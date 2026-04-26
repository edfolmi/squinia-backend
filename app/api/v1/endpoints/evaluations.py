"""Evaluation read API (by evaluation id)."""
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.response import ok
from app.schemas.simulation.evaluation import EvaluationResponse
from app.schemas.simulation.responses import EvaluationFullResponse, EvaluationScorePublic
from app.core.tenant_access import TenantMember
from app.services.simulation.evaluation import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


def _evaluation_full(ev: Any) -> dict:
    scores = []
    for s in getattr(ev, "scores", []) or []:
        ri = getattr(s, "rubric_item", None)
        criterion = ri.criterion if ri else "unknown"
        max_score = ri.max_score if ri else 0
        scores.append(
            EvaluationScorePublic(
                criterion=criterion,
                score=s.score,
                max_score=max_score,
                rationale=s.rationale,
                summary=s.summary,
                example_quote=s.example_quote,
                improvement=s.improvement,
            ).model_dump(mode="json"),
        )
    base = EvaluationResponse.model_validate(ev).model_dump(mode="json")
    return EvaluationFullResponse(**{**base, "scores": scores}).model_dump(mode="json")


@router.get("/{evaluation_id}")
async def get_evaluation(
    evaluation_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = EvaluationService(db)
    result = await svc.get_by_id(ctx.tenant_id, evaluation_id, ctx.user.id, ctx.org_role)
    ev = result["evaluation"]
    return ok({"evaluation": _evaluation_full(ev)})
