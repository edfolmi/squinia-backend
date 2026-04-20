"""Simulation session HTTP API."""
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.response import ok, ok_paginated
from app.schemas.simulation.evaluation import EvaluationResponse
from app.schemas.simulation.message import MessageResponse
from app.schemas.simulation.requests import SimulationSessionStartRequest
from app.schemas.simulation.responses import EvaluationFullResponse, EvaluationScorePublic, SessionDetailResponse, SessionStartResponse
from app.schemas.simulation.simulation_session import SimulationSessionResponse
from app.core.tenant_access import TenantMember
from app.core.exceptions import AppError
from app.models.simulation.evaluation import EvalStatus
from app.models.simulation.simulation_session import SessionStatus
from app.services.simulation.session import SessionService

router = APIRouter(prefix="/sessions", tags=["Simulation Sessions"])


def _evaluation_full(ev: Any) -> dict:
    scores = []
    for s in getattr(ev, "scores", []) or []:
        ri = getattr(s, "rubric_item", None)
        criterion = ri.criterion if ri else "unknown"
        max_score = ri.max_score if ri else 0
        scores.append(
            EvaluationScorePublic(criterion=criterion, score=s.score, max_score=max_score, rationale=s.rationale).model_dump(
                mode="json",
            ),
        )
    base = EvaluationResponse.model_validate(ev).model_dump(mode="json")
    return EvaluationFullResponse(**{**base, "scores": scores}).model_dump(mode="json")


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_session(
    body: SimulationSessionStartRequest,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SessionService(db)
    result = await svc.start_session(ctx.tenant_id, ctx.user.id, ctx.org_role, body)
    payload = SessionStartResponse(
        session_id=result["session_id"],
        ws_token=result["ws_token"],
        scenario_snapshot=result["scenario_snapshot"],
    ).model_dump(mode="json")
    return ok(payload)


@router.get("")
async def list_sessions(
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="SessionStatus enum value"),
    cohort_id: UUID | None = Query(None),
):
    st = None
    if status:
        try:
            st = SessionStatus(status)
        except ValueError:
            raise AppError(status_code=422, code="VALIDATION_ERROR", message="Invalid session status filter")
    svc = SessionService(db)
    result = await svc.list_sessions(ctx.tenant_id, ctx.user.id, ctx.org_role, page, limit, status=st, cohort_id=cohort_id)
    items = [SimulationSessionResponse.model_validate(i).model_dump(mode="json") for i in result["items"]]
    return ok_paginated(items, total=result["total"], page=result["page"], page_size=result["limit"])


@router.get("/{session_id}")
async def get_session(
    session_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SessionService(db)
    result = await svc.get_detail(ctx.tenant_id, session_id, ctx.user.id, ctx.org_role)
    session = result["session"]
    messages = [MessageResponse.model_validate(m).model_dump(mode="json") for m in result["messages"]]
    ev = result["evaluation"]
    ev_full = (
        EvaluationFullResponse.model_validate(_evaluation_full(ev))
        if ev and ev.status == EvalStatus.COMPLETED
        else None
    )
    sd = SimulationSessionResponse.model_validate(session).model_dump()
    detail = SessionDetailResponse(**sd, messages=messages, evaluation=ev_full)
    return ok({"session": detail.model_dump(mode="json")})


@router.post("/{session_id}/end")
async def end_session(
    session_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SessionService(db)
    result = await svc.end_session(ctx.tenant_id, session_id, ctx.user.id, ctx.org_role)
    return ok({"session": SimulationSessionResponse.model_validate(result["session"]).model_dump(mode="json")})


@router.post("/{session_id}/abandon")
async def abandon_session(
    session_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SessionService(db)
    result = await svc.abandon_session(ctx.tenant_id, session_id, ctx.user.id, ctx.org_role)
    return ok({"session": SimulationSessionResponse.model_validate(result["session"]).model_dump(mode="json")})


@router.get("/{session_id}/messages")
async def list_session_messages(
    session_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SessionService(db)
    result = await svc.list_messages(ctx.tenant_id, session_id, ctx.user.id, ctx.org_role)
    items = [MessageResponse.model_validate(i).model_dump(mode="json") for i in result["items"]]
    return ok({"items": items, "total": result["total"]})


@router.get("/{session_id}/evaluation")
async def get_session_evaluation(
    session_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SessionService(db)
    code, payload = await svc.evaluation_status(ctx.tenant_id, session_id, ctx.user.id, ctx.org_role)
    ev = payload.get("evaluation")
    if ev is not None:
        payload = {**payload, "evaluation": _evaluation_full(ev)}
    body = ok(payload)
    if code == 202:
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=body)
    return body
