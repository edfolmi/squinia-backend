"""
Auth session endpoints: register, login, refresh, current user.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.models.auth.user import User
from app.db.session import get_db
from app.schemas.auth.auth import LoginRequest, RefreshTokenRequest, Token
from app.schemas.auth.user import UserCreate, UserResponse
from app.services.auth import AuthService
from app.services.user import UserService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Create a platform user account (password-based)."""
    user_service = UserService(db)
    user = await user_service.create_user(user_in)
    return user


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Exchange email and password for access and refresh tokens."""
    auth_service = AuthService(db)
    return await auth_service.login(login_data.email, login_data.password)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Rotate tokens using a valid refresh token."""
    auth_service = AuthService(db)
    return await auth_service.refresh_access_token(token_data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> User:
    """Return the authenticated user."""
    return current_user
