"""Cohort and cohort member persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.simulation.cohort import Cohort
from app.models.simulation.cohort_member import CohortMember, CohortMemberRole


class CohortRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict[str, Any]) -> Cohort:
        row = Cohort(**data)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get(self, cohort_id: UUID, tenant_id: UUID) -> Optional[Cohort]:
        stmt = select(Cohort).where(
            Cohort.id == cohort_id,
            Cohort.tenant_id == tenant_id,
            Cohort.deleted_at.is_(None),
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> list[Cohort]:
        stmt = (
            select(Cohort)
            .where(Cohort.tenant_id == tenant_id, Cohort.deleted_at.is_(None))
            .order_by(Cohort.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(Cohort).where(
            Cohort.tenant_id == tenant_id,
            Cohort.deleted_at.is_(None),
        )
        r = await self.db.execute(stmt)
        return int(r.scalar_one() or 0)

    async def update(self, cohort_id: UUID, tenant_id: UUID, data: dict[str, Any]) -> Optional[Cohort]:
        if not data:
            return await self.get(cohort_id, tenant_id)
        await self.db.execute(
            update(Cohort)
            .where(Cohort.id == cohort_id, Cohort.tenant_id == tenant_id, Cohort.deleted_at.is_(None))
            .values(**data),
        )
        await self.db.flush()
        return await self.get(cohort_id, tenant_id)

    async def soft_delete(self, cohort_id: UUID, tenant_id: UUID) -> None:
        await self.db.execute(
            update(Cohort)
            .where(Cohort.id == cohort_id, Cohort.tenant_id == tenant_id, Cohort.deleted_at.is_(None))
            .values(deleted_at=datetime.now(timezone.utc)),
        )
        await self.db.flush()

    async def add_member(self, cohort_id: UUID, user_id: UUID, role: CohortMemberRole) -> CohortMember:
        m = CohortMember(cohort_id=cohort_id, user_id=user_id, role=role)
        self.db.add(m)
        await self.db.flush()
        await self.db.refresh(m)
        return m

    async def get_member(self, cohort_id: UUID, user_id: UUID) -> Optional[CohortMember]:
        stmt = select(CohortMember).where(
            CohortMember.cohort_id == cohort_id,
            CohortMember.user_id == user_id,
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def list_members(self, cohort_id: UUID, offset: int, limit: int) -> list[CohortMember]:
        stmt = (
            select(CohortMember)
            .where(CohortMember.cohort_id == cohort_id)
            .order_by(CohortMember.joined_at.asc())
            .offset(offset)
            .limit(limit)
        )
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def count_members(self, cohort_id: UUID) -> int:
        stmt = select(func.count()).select_from(CohortMember).where(CohortMember.cohort_id == cohort_id)
        r = await self.db.execute(stmt)
        return int(r.scalar_one() or 0)

    async def delete_member(self, cohort_id: UUID, user_id: UUID) -> bool:
        res = await self.db.execute(
            delete(CohortMember).where(
                CohortMember.cohort_id == cohort_id,
                CohortMember.user_id == user_id,
            ),
        )
        await self.db.flush()
        return (res.rowcount or 0) > 0

    async def get_with_members(self, cohort_id: UUID, tenant_id: UUID) -> Optional[Cohort]:
        stmt = (
            select(Cohort)
            .options(selectinload(Cohort.members))
            .where(
                Cohort.id == cohort_id,
                Cohort.tenant_id == tenant_id,
                Cohort.deleted_at.is_(None),
            )
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()
