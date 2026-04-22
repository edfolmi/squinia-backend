"""Email verification token persistence."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.email_verification import EmailVerification


class EmailVerificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def delete_pending_for_user(self, user_id: UUID) -> None:
        await self.db.execute(
            delete(EmailVerification).where(
                EmailVerification.user_id == user_id,
                EmailVerification.verified_at.is_(None),
            ),
        )
        await self.db.flush()

    async def create(
        self,
        *,
        user_id: UUID,
        email: str,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerification:
        row = EmailVerification(
            user_id=user_id,
            email=email,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get_unverified_by_token_hash(self, token_hash: str) -> Optional[EmailVerification]:
        stmt = (
            select(EmailVerification)
            .where(
                EmailVerification.token_hash == token_hash,
                EmailVerification.verified_at.is_(None),
            )
            .order_by(EmailVerification.created_at.desc())
            .limit(1)
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def mark_verified(self, verification_id: UUID, *, verified_at: datetime) -> None:
        await self.db.execute(
            update(EmailVerification)
            .where(EmailVerification.id == verification_id)
            .values(verified_at=verified_at),
        )
        await self.db.flush()
