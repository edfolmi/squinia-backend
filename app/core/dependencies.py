"""
FastAPI dependencies for authentication and platform authorization.
"""
from typing import Annotated, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.auth.user import PlatformRole, User
from app.services.auth import AuthService

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


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
        raise AppError(status_code=403, code="USER_INACTIVE", message="Inactive user")
    return current_user


async def get_current_user_optional(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(security_optional),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    if credentials is None or not credentials.credentials:
        return None
    auth_service = AuthService(db)
    try:
        return await auth_service.get_current_user(credentials.credentials)
    except AppError:
        return None


def require_platform_role(minimum: PlatformRole):
    """
    Require ``current_user.platform_role`` at least as privileged as ``minimum``.

    Ordering: USER < PLATFORM_ADMIN < PLATFORM_OWNER.
    """

    async def check_role(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if _platform_role_rank(current_user.platform_role) < _platform_role_rank(minimum):
            raise AppError(
                status_code=403,
                code="INSUFFICIENT_PRIVILEGES",
                message="Insufficient platform privileges",
            )
        return current_user

    return check_role


CurrentUser = Annotated[User, Depends(get_current_active_user)]
OptionalUser = Annotated[Optional[User], Depends(get_current_user_optional)]
AdminUser = Annotated[User, Depends(require_platform_role(PlatformRole.PLATFORM_ADMIN))]
