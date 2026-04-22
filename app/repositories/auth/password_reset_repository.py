"""Password reset token persistence."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.password_reset import PasswordReset


class PasswordResetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def delete_open_for_user(self, user_id: UUID) -> None:
        await self.db.execute(
            delete(PasswordReset).where(
                PasswordReset.user_id == user_id,
                PasswordReset.used_at.is_(None),
            ),
        )
        await self.db.flush()

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordReset:
        row = PasswordReset(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get_open_by_token_hash(self, token_hash: str) -> Optional[PasswordReset]:
        stmt = (
            select(PasswordReset)
            .where(
                PasswordReset.token_hash == token_hash,
                PasswordReset.used_at.is_(None),
            )
            .order_by(PasswordReset.created_at.desc())
            .limit(1)
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def mark_used(self, reset_id: UUID, *, used_at: datetime) -> None:
        await self.db.execute(
            update(PasswordReset).where(PasswordReset.id == reset_id).values(used_at=used_at),
        )
        await self.db.flush()
