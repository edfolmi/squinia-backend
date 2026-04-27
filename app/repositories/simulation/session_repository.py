"""Simulation session persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.simulation.evaluation import Evaluation
from app.models.simulation.evaluation_score import EvaluationScore
from app.models.simulation.simulation_session import SessionStatus, SimulationSession


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict[str, Any]) -> SimulationSession:
        row = SimulationSession(**data)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get(self, session_id: UUID, tenant_id: UUID) -> Optional[SimulationSession]:
        stmt = select(SimulationSession).where(
            SimulationSession.id == session_id,
            SimulationSession.tenant_id == tenant_id,
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def get_by_id(self, session_id: UUID) -> Optional[SimulationSession]:
        stmt = select(SimulationSession).where(SimulationSession.id == session_id)
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def get_with_relations(self, session_id: UUID, tenant_id: UUID) -> Optional[SimulationSession]:
        stmt = (
            select(SimulationSession)
            .options(
                selectinload(SimulationSession.messages),
                selectinload(SimulationSession.evaluation)
                .selectinload(Evaluation.scores)
                .selectinload(EvaluationScore.rubric_item),
            )
            .where(SimulationSession.id == session_id, SimulationSession.tenant_id == tenant_id)
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def list_for_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        offset: int,
        limit: int,
        status: Optional[SessionStatus] = None,
        cohort_id: Optional[UUID] = None,
    ) -> list[SimulationSession]:
        stmt = select(SimulationSession).where(
            SimulationSession.tenant_id == tenant_id,
            SimulationSession.user_id == user_id,
        )
        if status is not None:
            stmt = stmt.where(SimulationSession.status == status)
        if cohort_id is not None:
            stmt = stmt.where(SimulationSession.cohort_id == cohort_id)
        stmt = stmt.order_by(SimulationSession.created_at.desc()).offset(offset).limit(limit)
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def count_for_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        status: Optional[SessionStatus] = None,
        cohort_id: Optional[UUID] = None,
    ) -> int:
        stmt = select(func.count()).select_from(SimulationSession).where(
            SimulationSession.tenant_id == tenant_id,
            SimulationSession.user_id == user_id,
        )
        if status is not None:
            stmt = stmt.where(SimulationSession.status == status)
        if cohort_id is not None:
            stmt = stmt.where(SimulationSession.cohort_id == cohort_id)
        r = await self.db.execute(stmt)
        return int(r.scalar_one() or 0)

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        offset: int,
        limit: int,
        status: Optional[SessionStatus] = None,
        cohort_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> list[SimulationSession]:
        stmt = select(SimulationSession).where(SimulationSession.tenant_id == tenant_id)
        if status is not None:
            stmt = stmt.where(SimulationSession.status == status)
        if cohort_id is not None:
            stmt = stmt.where(SimulationSession.cohort_id == cohort_id)
        if user_id is not None:
            stmt = stmt.where(SimulationSession.user_id == user_id)
        stmt = stmt.order_by(SimulationSession.created_at.desc()).offset(offset).limit(limit)
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def count_for_tenant(
        self,
        tenant_id: UUID,
        *,
        status: Optional[SessionStatus] = None,
        cohort_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> int:
        stmt = select(func.count()).select_from(SimulationSession).where(
            SimulationSession.tenant_id == tenant_id,
        )
        if status is not None:
            stmt = stmt.where(SimulationSession.status == status)
        if cohort_id is not None:
            stmt = stmt.where(SimulationSession.cohort_id == cohort_id)
        if user_id is not None:
            stmt = stmt.where(SimulationSession.user_id == user_id)
        r = await self.db.execute(stmt)
        return int(r.scalar_one() or 0)

    async def update(self, session_id: UUID, tenant_id: UUID, data: dict[str, Any]) -> Optional[SimulationSession]:
        if not data:
            return await self.get(session_id, tenant_id)
        await self.db.execute(
            update(SimulationSession)
            .where(SimulationSession.id == session_id, SimulationSession.tenant_id == tenant_id)
            .values(**data),
        )
        await self.db.flush()
        return await self.get(session_id, tenant_id)
