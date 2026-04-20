"""Assignment and submission persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation.assignment import Assignment, AssignmentStatus
from app.models.simulation.assignment_submission import AssignmentSubmission


class AssignmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict[str, Any]) -> Assignment:
        row = Assignment(**data)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get(self, assignment_id: UUID, tenant_id: UUID) -> Optional[Assignment]:
        stmt = select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.tenant_id == tenant_id,
            Assignment.deleted_at.is_(None),
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        offset: int,
        limit: int,
        assigned_to: Optional[UUID] = None,
        status: Optional[AssignmentStatus] = None,
    ) -> list[Assignment]:
        stmt = select(Assignment).where(Assignment.tenant_id == tenant_id, Assignment.deleted_at.is_(None))
        if assigned_to is not None:
            stmt = stmt.where(Assignment.assigned_to == assigned_to)
        if status is not None:
            stmt = stmt.where(Assignment.status == status)
        stmt = stmt.order_by(Assignment.created_at.desc()).offset(offset).limit(limit)
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def count_for_tenant(
        self,
        tenant_id: UUID,
        *,
        assigned_to: Optional[UUID] = None,
        status: Optional[AssignmentStatus] = None,
    ) -> int:
        stmt = select(func.count()).select_from(Assignment).where(
            Assignment.tenant_id == tenant_id,
            Assignment.deleted_at.is_(None),
        )
        if assigned_to is not None:
            stmt = stmt.where(Assignment.assigned_to == assigned_to)
        if status is not None:
            stmt = stmt.where(Assignment.status == status)
        r = await self.db.execute(stmt)
        return int(r.scalar_one() or 0)

    async def update(self, assignment_id: UUID, tenant_id: UUID, data: dict[str, Any]) -> Optional[Assignment]:
        if not data:
            return await self.get(assignment_id, tenant_id)
        await self.db.execute(
            update(Assignment)
            .where(
                Assignment.id == assignment_id,
                Assignment.tenant_id == tenant_id,
                Assignment.deleted_at.is_(None),
            )
            .values(**data),
        )
        await self.db.flush()
        return await self.get(assignment_id, tenant_id)

    async def soft_delete(self, assignment_id: UUID, tenant_id: UUID) -> None:
        await self.db.execute(
            update(Assignment)
            .where(
                Assignment.id == assignment_id,
                Assignment.tenant_id == tenant_id,
                Assignment.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(timezone.utc)),
        )
        await self.db.flush()

    async def get_submission(self, assignment_id: UUID, user_id: UUID) -> Optional[AssignmentSubmission]:
        stmt = select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.user_id == user_id,
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def upsert_submission(self, assignment_id: UUID, user_id: UUID, data: dict[str, Any]) -> AssignmentSubmission:
        existing = await self.get_submission(assignment_id, user_id)
        if existing:
            await self.db.execute(
                update(AssignmentSubmission)
                .where(AssignmentSubmission.id == existing.id)
                .values(**data),
            )
            await self.db.flush()
            return (await self.get_submission(assignment_id, user_id)) or existing
        row = AssignmentSubmission(assignment_id=assignment_id, user_id=user_id, **data)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row
