"""Cohort service HTTP API."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_access import CohortReader, CohortWriter
from app.db.session import get_db
from app.schemas.response import ok, ok_paginated
from app.schemas.simulation.cohort import CohortResponse, CohortUpdate
from app.schemas.simulation.cohort_member import CohortMemberResponse
from app.schemas.simulation.requests import CohortCreateRequest, CohortMembersAddRequest
from app.schemas.simulation.responses import CohortMemberListItem, CohortProgressResponse
from app.services.simulation.cohort import CohortService
from app.services.simulation.evaluation import EvaluationService
from app.schemas.simulation.evaluation import EvaluationResponse

router = APIRouter(prefix="/cohorts", tags=["Cohorts"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_cohort(
    body: CohortCreateRequest,
    ctx: CohortWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CohortService(db)
    result = await svc.create(ctx.tenant_id, body)
    return ok({"cohort": CohortResponse.model_validate(result["cohort"]).model_dump(mode="json")})


async def _list_cohorts_paginated(
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int,
    limit: int,
):
    svc = CohortService(db)
    result = await svc.list_paginated(ctx.tenant_id, page, limit)
    items = [CohortResponse.model_validate(i).model_dump(mode="json") for i in result["items"]]
    return ok_paginated(items, total=result["total"], page=result["page"], page_size=result["limit"])


@router.get("")
async def list_cohorts(
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    return await _list_cohorts_paginated(ctx, db, page, limit)


@router.get("/list")
async def list_cohorts_extra_segment(
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Same as ``GET /cohorts`` but with an extra path segment so a stray ``GET /{tenant_id}``
    at the API root cannot steal the request (``cohorts`` is no longer the first segment alone).
    Prefer this URL from clients when upgrading older deployments.
    """
    return await _list_cohorts_paginated(ctx, db, page, limit)


@router.get("/{cohort_id}")
async def get_cohort(
    cohort_id: UUID,
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CohortService(db)
    result = await svc.get(ctx.tenant_id, cohort_id)
    return ok({"cohort": CohortResponse.model_validate(result["cohort"]).model_dump(mode="json")})


@router.patch("/{cohort_id}")
async def update_cohort(
    cohort_id: UUID,
    body: CohortUpdate,
    ctx: CohortWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CohortService(db)
    result = await svc.update(ctx.tenant_id, cohort_id, body)
    return ok({"cohort": CohortResponse.model_validate(result["cohort"]).model_dump(mode="json")})


@router.delete("/{cohort_id}", status_code=status.HTTP_200_OK)
async def delete_cohort(
    cohort_id: UUID,
    ctx: CohortWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CohortService(db)
    await svc.soft_delete(ctx.tenant_id, cohort_id)
    return ok({"message": "Cohort deleted"})


@router.post("/{cohort_id}/members", status_code=status.HTTP_201_CREATED)
async def add_cohort_members(
    cohort_id: UUID,
    body: CohortMembersAddRequest,
    ctx: CohortWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CohortService(db)
    result = await svc.add_members(ctx.tenant_id, cohort_id, body, ctx.org_role)
    items = [CohortMemberResponse.model_validate(m).model_dump(mode="json") for m in result["members"]]
    return ok({"members": items})


@router.get("/{cohort_id}/members")
async def list_cohort_members(
    cohort_id: UUID,
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
):
    svc = CohortService(db)
    result = await svc.list_members(ctx.tenant_id, cohort_id, page, limit)
    items_out = []
    for row in result["items"]:
        m = row["member"]
        items_out.append(
            CohortMemberListItem(
                id=m.id,
                cohort_id=m.cohort_id,
                user_id=m.user_id,
                role=m.role.value,
                joined_at=m.joined_at,
                sessions_completed=row["sessions_completed"],
                avg_score=row["avg_score"],
            ).model_dump(mode="json"),
        )
    return ok_paginated(items_out, total=result["total"], page=result["page"], page_size=result["limit"])


@router.delete("/{cohort_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_cohort_member(
    cohort_id: UUID,
    user_id: UUID,
    ctx: CohortWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CohortService(db)
    await svc.remove_member(ctx.tenant_id, cohort_id, user_id, ctx.org_role)
    return ok({"message": "Member removed"})


@router.get("/{cohort_id}/evaluations")
async def list_cohort_evaluations(
    cohort_id: UUID,
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: UUID | None = Query(None),
    scenario_id: UUID | None = Query(None),
):
    ev_svc = EvaluationService(db)
    result = await ev_svc.list_for_cohort(
        ctx.tenant_id,
        cohort_id,
        ctx.user.id,
        ctx.org_role,
        page,
        limit,
        user_id=user_id,
        scenario_id=scenario_id,
    )
    items = [EvaluationResponse.model_validate(i).model_dump(mode="json") for i in result["items"]]
    return ok_paginated(items, total=result["total"], page=result["page"], page_size=result["limit"])


@router.get("/{cohort_id}/progress")
async def cohort_progress(
    cohort_id: UUID,
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CohortService(db)
    result = await svc.progress(ctx.tenant_id, cohort_id)
    payload = CohortProgressResponse.model_validate(result["progress"]).model_dump(mode="json")
    return ok({"progress": payload})
