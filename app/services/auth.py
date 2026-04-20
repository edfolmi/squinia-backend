"""
Authentication service: credentials, JWT issuance, token refresh.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
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

    async def login(self, email: str, password: str) -> dict:
        user = await self.authenticate_user(email, password)
        if not user:
            raise AppError(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = security_service.create_access_token(
            subject=str(user.id),
            additional_claims={"platform_role": user.platform_role.value},
        )
        refresh_token = security_service.create_refresh_token(subject=str(user.id))
        return {
            "user": user,
            "tokens": Token(access_token=access_token, refresh_token=refresh_token),
        }

    async def refresh_access_token(self, refresh_token: str) -> Token:
        payload = security_service.decode_token(refresh_token)
        if not payload:
            raise AppError(status_code=401, code="INVALID_TOKEN", message="Invalid refresh token")
        if not security_service.verify_token_type(payload, "refresh"):
            raise AppError(status_code=401, code="INVALID_TOKEN_TYPE", message="Token is not a refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise AppError(status_code=401, code="INVALID_TOKEN_PAYLOAD", message="Invalid token payload")

        try:
            uid = UUID(str(user_id))
        except ValueError:
            raise AppError(status_code=401, code="INVALID_TOKEN_SUBJECT", message="Invalid token subject")

        user = await self.user_repo.get(uid)
        if not user or not user.is_active or user.deleted_at is not None:
            raise AppError(status_code=401, code="USER_UNAVAILABLE", message="User not found or inactive")

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
            raise AppError(
                status_code=401,
                code="UNAUTHORIZED",
                message="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not security_service.verify_token_type(payload, "access"):
            raise AppError(status_code=401, code="INVALID_TOKEN_TYPE", message="Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise AppError(status_code=401, code="INVALID_TOKEN_PAYLOAD", message="Invalid token payload")

        try:
            uid = UUID(str(user_id))
        except ValueError:
            raise AppError(status_code=401, code="INVALID_TOKEN_SUBJECT", message="Invalid token subject")

        user = await self.user_repo.get(uid)
        if not user:
            raise AppError(status_code=404, code="USER_NOT_FOUND", message="User not found")
        if user.deleted_at is not None:
            raise AppError(status_code=403, code="USER_DELETED", message="User account is no longer available")
        if not user.is_active:
            raise AppError(status_code=403, code="USER_INACTIVE", message="Inactive user")
        return user
