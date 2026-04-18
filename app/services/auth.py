"""
Authentication service: credentials, JWT issuance, token refresh.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import security_service
from app.models.auth.user import User
from app.repositories.auth import UserRepository
from app.schemas.auth.auth import Token

logger = get_logger(__name__)


class AuthService:
    """Login, refresh, and token-backed user resolution."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = await self.user_repo.get_by_email(email)
        if not user:
            logger.warning("Authentication failed: user not found", email=email)
            return None
        if user.deleted_at is not None:
            logger.warning("Authentication failed: deleted user", email=email)
            return None
        if not user.password_hash:
            logger.warning("Authentication failed: SSO-only user", email=email)
            return None
        if not security_service.verify_password(password, user.password_hash):
            logger.warning("Authentication failed: invalid password", email=email)
            return None
        if not user.is_active:
            logger.warning("Authentication failed: inactive user", email=email)
            return None

        logger.info("User authenticated", user_id=str(user.id), email=email)
        return user

    async def login(self, email: str, password: str) -> Token:
        user = await self.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = security_service.create_access_token(
            subject=str(user.id),
            additional_claims={"platform_role": user.platform_role.value},
        )
        refresh_token = security_service.create_refresh_token(subject=str(user.id))
        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token: str) -> Token:
        payload = security_service.decode_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        if not security_service.verify_token_type(payload, "refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is not a refresh token",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        try:
            uid = UUID(str(user_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )

        user = await self.user_repo.get(uid)
        if not user or not user.is_active or user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        access_token = security_service.create_access_token(
            subject=str(user.id),
            additional_claims={"platform_role": user.platform_role.value},
        )
        new_refresh = security_service.create_refresh_token(subject=str(user.id))
        logger.info("Access token refreshed", user_id=str(user.id))
        return Token(access_token=access_token, refresh_token=new_refresh)

    async def get_current_user(self, token: str) -> User:
        payload = security_service.decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not security_service.verify_token_type(payload, "access"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        try:
            uid = UUID(str(user_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )

        user = await self.user_repo.get(uid)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is no longer available",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )
        return user
