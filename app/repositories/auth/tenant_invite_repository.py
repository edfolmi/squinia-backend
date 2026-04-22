"""Tenant invite token persistence."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.membership import OrgRole
from app.models.auth.tenant_invite import TenantInvite


class TenantInviteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        tenant_id: UUID,
        email: str,
        role: OrgRole,
        token_hash: str,
        expires_at: datetime,
        invited_by_user_id: Optional[UUID] = None,
    ) -> TenantInvite:
        row = TenantInvite(
            tenant_id=tenant_id,
            email=email.strip().lower(),
            role=role,
            token_hash=token_hash,
            expires_at=expires_at,
            invited_by_user_id=invited_by_user_id,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get_open_by_token_hash(self, token_hash: str) -> Optional[TenantInvite]:
        stmt = (
            select(TenantInvite)
            .where(
                TenantInvite.token_hash == token_hash,
                TenantInvite.used_at.is_(None),
            )
            .order_by(TenantInvite.created_at.desc())
            .limit(1)
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def mark_used(self, invite_id: UUID, *, used_at: datetime) -> None:
        await self.db.execute(
            update(TenantInvite).where(TenantInvite.id == invite_id).values(used_at=used_at),
        )
        await self.db.flush()
