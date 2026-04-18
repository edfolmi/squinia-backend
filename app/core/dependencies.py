"""
FastAPI dependencies for authentication and platform authorization.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.auth.user import PlatformRole, User
from app.services.auth import AuthService

security = HTTPBearer()


def _platform_role_rank(role: PlatformRole) -> int:
    return {
        PlatformRole.USER: 0,
        PlatformRole.PLATFORM_ADMIN: 1,
        PlatformRole.PLATFORM_OWNER: 2,
    }[role]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    auth_service = AuthService(db)
    return await auth_service.get_current_user(credentials.credentials)


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_platform_role(minimum: PlatformRole):
    """
    Require ``current_user.platform_role`` at least as privileged as ``minimum``.

    Ordering: USER < PLATFORM_ADMIN < PLATFORM_OWNER.
    """

    async def check_role(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if _platform_role_rank(current_user.platform_role) < _platform_role_rank(minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient platform privileges",
            )
        return current_user

    return check_role


CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_platform_role(PlatformRole.PLATFORM_ADMIN))]
