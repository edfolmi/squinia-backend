"""Evaluation read APIs and internal worker hooks."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.auth.membership import OrgRole
from app.models.simulation.evaluation import EvalStatus
from app.models.simulation.evaluation_score import EvaluationScore
from app.repositories.simulation import EvaluationRepository, SessionRepository
from app.schemas.simulation.requests import InternalEvalCompleteRequest, InternalEvalTriggerRequest

logger = get_logger(__name__)


class EvaluationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.evaluations = EvaluationRepository(db)
        self.sessions = SessionRepository(db)

    def _can_view_evaluation(
        self,
        *,
        subject_user_id: UUID,
        viewer_id: UUID,
        org_role: OrgRole,
    ) -> bool:
        if subject_user_id == viewer_id:
            return True
        return org_role in (OrgRole.INSTRUCTOR, OrgRole.ORG_ADMIN, OrgRole.ORG_OWNER)

    async def get_by_id(
        self,
        tenant_id: UUID,
        evaluation_id: UUID,
        viewer_id: UUID,
        org_role: OrgRole,
    ) -> dict:
        ev = await self.evaluations.get_detail(evaluation_id, tenant_id)
        if not ev:
            raise AppError(status_code=404, code="NOT_FOUND", message="Evaluation not found")
        session = await self.sessions.get(ev.session_id, tenant_id)
        if not session:
            raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")
        if not self._can_view_evaluation(
            subject_user_id=session.user_id,
            viewer_id=viewer_id,
            org_role=org_role,
        ):
            raise AppError(status_code=403, code="FORBIDDEN", message="Cannot view this evaluation")
        return {"evaluation": ev}

    async def list_for_cohort(
        self,
        tenant_id: UUID,
        cohort_id: UUID,
        viewer_id: UUID,
        org_role: OrgRole,
        page: int,
        limit: int,
        *,
        user_id: UUID | None = None,
        scenario_id: UUID | None = None,
    ) -> dict:
        if org_role == OrgRole.STUDENT:
            raise AppError(status_code=403, code="FORBIDDEN", message="Cannot list cohort evaluations")
        offset = (page - 1) * limit
        items = await self.evaluations.list_for_cohort(
            tenant_id,
            cohort_id,
            offset=offset,
            limit=limit,
            user_id=user_id,
            scenario_id=scenario_id,
        )
        total = await self.evaluations.count_for_cohort(
            tenant_id,
            cohort_id,
            user_id=user_id,
            scenario_id=scenario_id,
        )
        return {"items": items, "total": total, "page": page, "limit": limit}

    async def list_for_user(
        self,
        tenant_id: UUID,
        target_user_id: UUID,
        viewer_id: UUID,
        org_role: OrgRole,
        page: int,
        limit: int,
    ) -> dict:
        if not self._can_view_evaluation(subject_user_id=target_user_id, viewer_id=viewer_id, org_role=org_role):
            raise AppError(status_code=403, code="FORBIDDEN", message="Cannot view this user's evaluations")
        offset = (page - 1) * limit
        items = await self.evaluations.list_for_user(tenant_id, target_user_id, offset=offset, limit=limit)
        total = await self.evaluations.count_for_user(tenant_id, target_user_id)
        return {"items": items, "total": total, "page": page, "limit": limit}

    async def internal_trigger(self, body: InternalEvalTriggerRequest) -> dict:
        session = await self.sessions.get_by_id(body.session_id)
        if not session:
            raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")
        tenant_id = session.tenant_id
        existing = await self.evaluations.get_by_session(body.session_id, tenant_id)
        if existing:
            return {"evaluation": existing, "created": False}
        ev = await self.evaluations.create(
            {
                "session_id": body.session_id,
                "tenant_id": tenant_id,
                "status": EvalStatus.PROCESSING,
                "processing_started_at": datetime.now(timezone.utc),
            },
        )
        await self.db.commit()
        logger.info("Evaluation triggered", evaluation_id=str(ev.id), session_id=str(body.session_id))
        return {"evaluation": ev, "created": True}

    async def internal_complete(
        self,
        evaluation_id: UUID,
        body: InternalEvalCompleteRequest,
    ) -> dict:
        ev = await self.evaluations.get_by_id(evaluation_id)
        if not ev:
            raise AppError(status_code=404, code="NOT_FOUND", message="Evaluation not found")
        tenant_id = ev.tenant_id
        await self.db.execute(delete(EvaluationScore).where(EvaluationScore.evaluation_id == ev.id))
        for item in body.scores:
            await self.evaluations.add_score(
                {
                    "evaluation_id": ev.id,
                    "rubric_item_id": item.rubric_item_id,
                    "score": item.score,
                    "rationale": item.rationale,
                    "summary": item.summary,
                    "example_quote": item.example_quote,
                    "improvement": item.improvement,
                },
            )
        await self.evaluations.update(
            ev.id,
            tenant_id,
            {
                "status": EvalStatus.COMPLETED,
                "overall_score": body.overall_score,
                "feedback_summary": body.feedback_summary,
                "strengths": body.strengths,
                "improvements": body.improvements,
                "highlights": body.highlights,
                "completed_at": datetime.now(timezone.utc),
            },
        )
        await self.db.commit()
        fresh = await self.evaluations.get_detail(ev.id, tenant_id)
        return {"evaluation": fresh}
