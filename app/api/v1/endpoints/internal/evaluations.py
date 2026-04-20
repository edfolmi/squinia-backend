"""Internal evaluation worker hooks."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.internal_auth import verify_internal_api_key
from app.db.session import get_db
from app.schemas.response import ok
from app.schemas.simulation.evaluation import EvaluationResponse
from app.schemas.simulation.requests import InternalEvalCompleteRequest, InternalEvalTriggerRequest
from app.services.simulation.evaluation import EvaluationService

router = APIRouter(
    prefix="/internal/evaluations",
    tags=["Internal — Evaluations"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.post("/trigger", status_code=status.HTTP_201_CREATED)
async def trigger_evaluation(
    body: InternalEvalTriggerRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = EvaluationService(db)
    result = await svc.internal_trigger(body)
    return ok(
        {
            "evaluation": EvaluationResponse.model_validate(result["evaluation"]).model_dump(mode="json"),
            "created": result["created"],
        },
    )


@router.patch("/{evaluation_id}/complete")
async def complete_evaluation(
    evaluation_id: UUID,
    body: InternalEvalCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = EvaluationService(db)
    result = await svc.internal_complete(evaluation_id, body)
    return ok(
        {
            "evaluation": EvaluationResponse.model_validate(result["evaluation"]).model_dump(mode="json"),
        },
    )
