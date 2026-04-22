"""Email verification issuance and confirmation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.integrations.email import get_email_provider
from app.models.auth.user import User
from app.repositories.auth.email_verification_repository import EmailVerificationRepository
from app.repositories.auth.user_repository import UserRepository
from app.utils.tokens import hash_url_token, new_url_token

logger = get_logger(__name__)

VERIFICATION_TTL_HOURS = 48


class AuthVerificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = EmailVerificationRepository(db)
        self.users = UserRepository(db)

    async def issue_and_send_for_user(self, user: User) -> None:
        raw, token_hash = new_url_token()
        expires = datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TTL_HOURS)
        await self.repo.delete_pending_for_user(user.id)
        await self.repo.create(
            user_id=user.id,
            email=user.email,
            token_hash=token_hash,
            expires_at=expires,
        )
        base = settings.PUBLIC_APP_URL.rstrip("/")
        link = f"{base}/verify-email?token={raw}"
        subject = "Verify your email"
        text = (
            f"Confirm your email by opening this link (or paste the token in the app):\n{link}\n\n"
            "If you did not create this account, you can ignore this message."
        )
        try:
            await get_email_provider().send(
                to_address=user.email,
                subject=subject,
                text_body=text,
            )
        except Exception:
            logger.exception("verification_email_send_failed", user_id=str(user.id))

    async def verify_email_token(self, raw_token: str) -> User:
        token_hash = hash_url_token(raw_token)
        row = await self.repo.get_unverified_by_token_hash(token_hash)
        if not row:
            raise AppError(
                status_code=400,
                code="INVALID_TOKEN",
                message="Invalid or unknown verification token",
            )

        now = datetime.now(timezone.utc)
        if row.expires_at <= now:
            raise AppError(
                status_code=400,
                code="TOKEN_EXPIRED",
                message="Verification link has expired",
            )

        user = await self.users.get(row.user_id)
        if not user or user.deleted_at is not None:
            raise AppError(
                status_code=400,
                code="INVALID_TOKEN",
                message="Invalid or unknown verification token",
            )

        if user.is_verified:
            await self.repo.mark_verified(row.id, verified_at=now)
            return user

        await self.users.update(user.id, {"is_verified": True})
        await self.repo.mark_verified(row.id, verified_at=now)
        user.is_verified = True
        return user
