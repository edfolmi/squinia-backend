"""Tenant read access."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.tenant import Tenant


class TenantRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self, tenant_id: UUID) -> Optional[Tenant]:
        stmt = select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()
