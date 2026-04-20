"""Cohort use-cases."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.auth.membership import OrgRole
from app.models.simulation.evaluation import EvalStatus, Evaluation
from app.models.simulation.simulation_session import SessionStatus, SimulationSession
from app.repositories.simulation import CohortRepository
from app.schemas.simulation.cohort import CohortUpdate
from app.schemas.simulation.requests import CohortCreateRequest, CohortMembersAddRequest

logger = get_logger(__name__)


class CohortService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cohorts = CohortRepository(db)

    async def create(self, tenant_id: UUID, body: CohortCreateRequest) -> dict:
        row = await self.cohorts.create(
            {
                "tenant_id": tenant_id,
                "name": body.name,
                "description": body.description,
                "status": body.status,
                "starts_at": body.starts_at,
                "ends_at": body.ends_at,
            },
        )
        await self.db.commit()
        logger.info("Cohort created", cohort_id=str(row.id), tenant_id=str(tenant_id))
        return {"cohort": row}

    async def list_paginated(self, tenant_id: UUID, page: int, limit: int) -> dict:
        offset = (page - 1) * limit
        items = await self.cohorts.list_for_tenant(tenant_id, offset=offset, limit=limit)
        total = await self.cohorts.count_for_tenant(tenant_id)
        return {"items": items, "total": total, "page": page, "limit": limit}

    async def get(self, tenant_id: UUID, cohort_id: UUID):
        row = await self.cohorts.get(cohort_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Cohort not found")
        return {"cohort": row}

    async def update(self, tenant_id: UUID, cohort_id: UUID, body: CohortUpdate) -> dict:
        data = body.model_dump(exclude_unset=True)
        row = await self.cohorts.update(cohort_id, tenant_id, data)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Cohort not found")
        await self.db.commit()
        return {"cohort": row}

    async def soft_delete(self, tenant_id: UUID, cohort_id: UUID) -> None:
        row = await self.cohorts.get(cohort_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Cohort not found")
        await self.cohorts.soft_delete(cohort_id, tenant_id)
        await self.db.commit()

    async def add_members(
        self,
        tenant_id: UUID,
        cohort_id: UUID,
        body: CohortMembersAddRequest,
        org_role: OrgRole,
    ) -> dict:
        if org_role not in (OrgRole.ORG_OWNER, OrgRole.ORG_ADMIN):
            raise AppError(status_code=403, code="FORBIDDEN", message="Only org admins can add cohort members")
        cohort = await self.cohorts.get(cohort_id, tenant_id)
        if not cohort:
            raise AppError(status_code=404, code="NOT_FOUND", message="Cohort not found")
        added = []
        for uid in body.user_ids:
            existing = await self.cohorts.get_member(cohort_id, uid)
            if existing:
                continue
            m = await self.cohorts.add_member(cohort_id, uid, body.role)
            added.append(m)
        await self.db.commit()
        return {"members": added}

    async def list_members(self, tenant_id: UUID, cohort_id: UUID, page: int, limit: int) -> dict:
        cohort = await self.cohorts.get(cohort_id, tenant_id)
        if not cohort:
            raise AppError(status_code=404, code="NOT_FOUND", message="Cohort not found")
        offset = (page - 1) * limit
        members = await self.cohorts.list_members(cohort_id, offset, limit)
        total = await self.cohorts.count_members(cohort_id)
        summaries = []
        for m in members:
            completed, avg_score = await self._member_session_stats(cohort_id, m.user_id)
            summaries.append(
                {
                    "member": m,
                    "sessions_completed": completed,
                    "avg_score": avg_score,
                },
            )
        return {"items": summaries, "total": total, "page": page, "limit": limit}

    async def _member_session_stats(self, cohort_id: UUID, user_id: UUID) -> tuple[int, float | None]:
        stmt = (
            select(
                func.count(SimulationSession.id).label("completed"),
                func.avg(Evaluation.overall_score).label("avg"),
            )
            .select_from(SimulationSession)
            .outerjoin(Evaluation, Evaluation.session_id == SimulationSession.id)
            .where(
                SimulationSession.cohort_id == cohort_id,
                SimulationSession.user_id == user_id,
                SimulationSession.status == SessionStatus.COMPLETED,
                Evaluation.status == EvalStatus.COMPLETED,
            )
        )
        r = await self.db.execute(stmt)
        row = r.one()
        completed = int(row.completed or 0)
        avg = row.avg
        return completed, float(avg) if avg is not None else None

    async def remove_member(self, tenant_id: UUID, cohort_id: UUID, user_id: UUID, org_role: OrgRole) -> None:
        if org_role not in (OrgRole.ORG_OWNER, OrgRole.ORG_ADMIN):
            raise AppError(status_code=403, code="FORBIDDEN", message="Only org admins can remove cohort members")
        cohort = await self.cohorts.get(cohort_id, tenant_id)
        if not cohort:
            raise AppError(status_code=404, code="NOT_FOUND", message="Cohort not found")
        ok = await self.cohorts.delete_member(cohort_id, user_id)
        if not ok:
            raise AppError(status_code=404, code="NOT_FOUND", message="Member not found in cohort")
        await self.db.commit()

    async def progress(self, tenant_id: UUID, cohort_id: UUID) -> dict:
        cohort = await self.cohorts.get(cohort_id, tenant_id)
        if not cohort:
            raise AppError(status_code=404, code="NOT_FOUND", message="Cohort not found")

        members = await self.cohorts.list_members(cohort_id, 0, 10_000)
        members_out: list[dict] = []
        for m in members:
            stmt_total = select(func.count()).select_from(SimulationSession).where(
                SimulationSession.cohort_id == cohort_id,
                SimulationSession.user_id == m.user_id,
            )
            stmt_done = select(func.count()).select_from(SimulationSession).where(
                SimulationSession.cohort_id == cohort_id,
                SimulationSession.user_id == m.user_id,
                SimulationSession.status == SessionStatus.COMPLETED,
            )
            stmt_avg = (
                select(func.avg(Evaluation.overall_score))
                .select_from(Evaluation)
                .join(SimulationSession, SimulationSession.id == Evaluation.session_id)
                .where(
                    SimulationSession.cohort_id == cohort_id,
                    SimulationSession.user_id == m.user_id,
                    Evaluation.status == EvalStatus.COMPLETED,
                )
            )
            total = int((await self.db.execute(stmt_total)).scalar_one() or 0)
            done = int((await self.db.execute(stmt_done)).scalar_one() or 0)
            avg_raw = (await self.db.execute(stmt_avg)).scalar_one_or_none()
            completion = float(done) / float(total) if total else 0.0
            scores: dict[str, float] = {}
            if avg_raw is not None:
                scores["overall"] = float(avg_raw)
            members_out.append(
                {
                    "user_id": m.user_id,
                    "scores": scores,
                    "completion_rate": completion,
                },
            )
        return {"progress": {"members": members_out}}
