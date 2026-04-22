"""
Auth session endpoints: register, login, refresh, current user.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.db.session import get_db
from app.models.auth.user import User
from app.schemas.auth.auth import LoginRequest, RefreshTokenRequest
from app.schemas.auth.user import UserCreate, UserResponse
from app.schemas.response import ok
from app.services.auth import AuthService
from app.services.auth_verification import AuthVerificationService
from app.services.me import MeService
from app.services.user import UserService

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a platform user account (password-based)."""
    user_service = UserService(db)
    user = await user_service.create_user(user_in)
    await AuthVerificationService(db).issue_and_send_for_user(user)
    return ok({"user": UserResponse.model_validate(user).model_dump(mode="json")})


@router.post("/login")
async def login(
    login_data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Exchange email and password for access and refresh tokens."""
    auth_service = AuthService(db)
    result = await auth_service.login(login_data.email, login_data.password)
    return ok({
        "user": UserResponse.model_validate(result["user"]).model_dump(mode="json"),
        "tokens": result["tokens"].model_dump(mode="json"),
    })


@router.post("/refresh")
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Rotate tokens using a valid refresh token."""
    auth_service = AuthService(db)
    tokens = await auth_service.refresh_access_token(token_data.refresh_token)
    return ok({"tokens": tokens.model_dump(mode="json")})


@router.get("/me")
async def get_current_user_info(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Current user plus org memberships for shell routing (learner vs org operator).

    ``data.user`` includes ``onboarding`` and ``onboarding_completed_at``.
    ``data.memberships`` lists active tenants with ``tenant_name`` / ``tenant_slug`` / ``org_role``.
    ``data.default_tenant_id`` matches the first membership (same ordering as JWT default tenant).
    """
    me = await MeService(db).get_me(current_user)
    return ok(me.model_dump(mode="json"))
