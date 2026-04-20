"""Evaluation persistence."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.simulation.evaluation import EvalStatus, Evaluation
from app.models.simulation.evaluation_score import EvaluationScore
from app.models.simulation.simulation_session import SimulationSession


class EvaluationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict[str, Any]) -> Evaluation:
        row = Evaluation(**data)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get(self, evaluation_id: UUID, tenant_id: UUID) -> Optional[Evaluation]:
        stmt = select(Evaluation).where(Evaluation.id == evaluation_id, Evaluation.tenant_id == tenant_id)
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def get_by_id(self, evaluation_id: UUID) -> Optional[Evaluation]:
        stmt = select(Evaluation).where(Evaluation.id == evaluation_id)
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def get_by_session(self, session_id: UUID, tenant_id: UUID) -> Optional[Evaluation]:
        stmt = select(Evaluation).where(Evaluation.session_id == session_id, Evaluation.tenant_id == tenant_id)
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def get_detail(self, evaluation_id: UUID, tenant_id: UUID) -> Optional[Evaluation]:
        stmt = (
            select(Evaluation)
            .options(
                selectinload(Evaluation.scores).selectinload(EvaluationScore.rubric_item),
            )
            .where(Evaluation.id == evaluation_id, Evaluation.tenant_id == tenant_id)
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def get_by_session_detail(self, session_id: UUID, tenant_id: UUID) -> Optional[Evaluation]:
        stmt = (
            select(Evaluation)
            .options(
                selectinload(Evaluation.scores).selectinload(EvaluationScore.rubric_item),
            )
            .where(Evaluation.session_id == session_id, Evaluation.tenant_id == tenant_id)
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def update(self, evaluation_id: UUID, tenant_id: UUID, data: dict[str, Any]) -> Optional[Evaluation]:
        if not data:
            return await self.get(evaluation_id, tenant_id)
        await self.db.execute(
            update(Evaluation)
            .where(Evaluation.id == evaluation_id, Evaluation.tenant_id == tenant_id)
            .values(**data),
        )
        await self.db.flush()
        return await self.get(evaluation_id, tenant_id)

    async def list_for_cohort(
        self,
        tenant_id: UUID,
        cohort_id: UUID,
        *,
        offset: int,
        limit: int,
        user_id: Optional[UUID] = None,
        scenario_id: Optional[UUID] = None,
    ) -> list[Evaluation]:
        stmt = (
            select(Evaluation)
            .join(SimulationSession, SimulationSession.id == Evaluation.session_id)
            .where(
                Evaluation.tenant_id == tenant_id,
                SimulationSession.cohort_id == cohort_id,
            )
        )
        if user_id is not None:
            stmt = stmt.where(SimulationSession.user_id == user_id)
        if scenario_id is not None:
            stmt = stmt.where(SimulationSession.scenario_id == scenario_id)
        stmt = stmt.order_by(Evaluation.created_at.desc()).offset(offset).limit(limit)
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def count_for_cohort(
        self,
        tenant_id: UUID,
        cohort_id: UUID,
        *,
        user_id: Optional[UUID] = None,
        scenario_id: Optional[UUID] = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Evaluation)
            .join(SimulationSession, SimulationSession.id == Evaluation.session_id)
            .where(
                Evaluation.tenant_id == tenant_id,
                SimulationSession.cohort_id == cohort_id,
            )
        )
        if user_id is not None:
            stmt = stmt.where(SimulationSession.user_id == user_id)
        if scenario_id is not None:
            stmt = stmt.where(SimulationSession.scenario_id == scenario_id)
        r = await self.db.execute(stmt)
        return int(r.scalar_one() or 0)

    async def list_for_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> list[Evaluation]:
        stmt = (
            select(Evaluation)
            .join(SimulationSession, SimulationSession.id == Evaluation.session_id)
            .where(
                Evaluation.tenant_id == tenant_id,
                SimulationSession.user_id == user_id,
            )
            .order_by(Evaluation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def count_for_user(self, tenant_id: UUID, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Evaluation)
            .join(SimulationSession, SimulationSession.id == Evaluation.session_id)
            .where(
                Evaluation.tenant_id == tenant_id,
                SimulationSession.user_id == user_id,
            )
        )
        r = await self.db.execute(stmt)
        return int(r.scalar_one() or 0)

    async def add_score(self, data: dict[str, Any]) -> EvaluationScore:
        row = EvaluationScore(**data)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row
