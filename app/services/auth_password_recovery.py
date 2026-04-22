"""Forgot / reset password using one-time tokens."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.core.security import security_service
from app.integrations.email import get_email_provider
from app.repositories.auth.password_reset_repository import PasswordResetRepository
from app.repositories.auth.user_repository import UserRepository
from app.utils.tokens import hash_url_token, new_url_token

logger = get_logger(__name__)

RESET_TTL_HOURS = 2


class AuthPasswordRecoveryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.resets = PasswordResetRepository(db)
        self.users = UserRepository(db)

    async def forgot_password(self, email: str) -> None:
        user = await self.users.get_by_email_lower(email)
        if not user or user.deleted_at is not None or not user.password_hash:
            return
        raw, token_hash = new_url_token()
        expires = datetime.now(timezone.utc) + timedelta(hours=RESET_TTL_HOURS)
        await self.resets.delete_open_for_user(user.id)
        await self.resets.create(user_id=user.id, token_hash=token_hash, expires_at=expires)
        base = settings.PUBLIC_APP_URL.rstrip("/")
        link = f"{base}/reset-password?token={raw}"
        subject = "Reset your password"
        text = (
            f"Reset your password using this link:\n{link}\n\n"
            "If you did not request a reset, you can ignore this message."
        )
        try:
            await get_email_provider().send(
                to_address=user.email,
                subject=subject,
                text_body=text,
            )
        except Exception:
            logger.exception("password_reset_email_failed", user_id=str(user.id))

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        token_hash = hash_url_token(raw_token)
        row = await self.resets.get_open_by_token_hash(token_hash)
        if not row:
            raise AppError(
                status_code=400,
                code="INVALID_TOKEN",
                message="Invalid or unknown reset token",
            )
        now = datetime.now(timezone.utc)
        if row.expires_at <= now:
            raise AppError(
                status_code=400,
                code="TOKEN_EXPIRED",
                message="Reset link has expired",
            )

        user = await self.users.get(row.user_id)
        if not user or user.deleted_at is not None:
            raise AppError(
                status_code=400,
                code="INVALID_TOKEN",
                message="Invalid or unknown reset token",
            )

        await self.users.update(
            user.id,
            {"password_hash": security_service.get_password_hash(new_password)},
        )
        await self.resets.mark_used(row.id, used_at=now)
