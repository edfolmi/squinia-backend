"""
Membership repository: tenant membership lookups.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.membership import Membership, OrgRole


class MembershipRepository:
    """Data access for ``memberships`` table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self, user_id: UUID, tenant_id: UUID) -> Optional[Membership]:
        stmt = (
            select(Membership)
            .where(
                Membership.user_id == user_id,
                Membership.tenant_id == tenant_id,
                Membership.deleted_at.is_(None),
                Membership.is_active.is_(True),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_for_user(self, user_id: UUID) -> Optional[Membership]:
        """First active membership by ``joined_at`` (stable default tenant for JWT)."""
        stmt = (
            select(Membership)
            .where(
                Membership.user_id == user_id,
                Membership.deleted_at.is_(None),
                Membership.is_active.is_(True),
            )
            .order_by(Membership.joined_at.asc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_any_for_user_tenant(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> Optional[Membership]:
        stmt = select(Membership).where(
            Membership.user_id == user_id,
            Membership.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
        role: OrgRole,
    ) -> Membership:
        m = Membership(user_id=user_id, tenant_id=tenant_id, role=role, is_active=True)
        self.db.add(m)
        await self.db.flush()
        await self.db.refresh(m)
        return m

    async def reactivate(self, membership_id: UUID) -> None:
        await self.db.execute(
            update(Membership)
            .where(Membership.id == membership_id)
            .values(is_active=True, deleted_at=None),
        )
        await self.db.flush()
