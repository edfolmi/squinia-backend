"""Assignment service HTTP API."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.tenant_access import TenantMember
from app.db.session import get_db
from app.models.simulation.assignment import AssignmentStatus
from app.schemas.response import ok, ok_paginated
from app.schemas.simulation.assignment import AssignmentResponse, AssignmentUpdate
from app.schemas.simulation.assignment_submission import SubmissionResponse
from app.schemas.simulation.requests import (
    AssignmentCreateRequest,
    AssignmentGradeRequest,
    AssignmentSubmitRequest,
)
from app.services.simulation.assignment import AssignmentService

router = APIRouter(prefix="/assignments", tags=["Assignments"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_assignment(
    body: AssignmentCreateRequest,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.models.auth.membership import OrgRole

    if ctx.org_role not in (OrgRole.INSTRUCTOR, OrgRole.ORG_ADMIN, OrgRole.ORG_OWNER):
        raise AppError(status_code=403, code="FORBIDDEN", message="Only instructors or admins can create assignments")
    svc = AssignmentService(db)
    result = await svc.create(ctx.tenant_id, ctx.user.id, body)
    return ok({"assignment": AssignmentResponse.model_validate(result["assignment"]).model_dump(mode="json")})


@router.get("")
async def list_assignments(
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    assigned_to: UUID | None = Query(None),
    assigned_to_me: bool = Query(False),
    status: AssignmentStatus | None = Query(None),
):
    svc = AssignmentService(db)
    result = await svc.list(
        ctx.tenant_id,
        ctx.user.id,
        ctx.org_role,
        page,
        limit,
        assigned_to=assigned_to,
        assigned_to_me=assigned_to_me,
        status=status,
    )
    items = [AssignmentResponse.model_validate(i).model_dump(mode="json") for i in result["items"]]
    return ok_paginated(items, total=result["total"], page=result["page"], page_size=result["limit"])


@router.get("/{assignment_id}")
async def get_assignment(
    assignment_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssignmentService(db)
    result = await svc.get_detail(ctx.tenant_id, assignment_id, ctx.user.id, ctx.org_role)
    sub = result["submission"]
    payload = {
        "assignment": AssignmentResponse.model_validate(result["assignment"]).model_dump(mode="json"),
        "submission": SubmissionResponse.model_validate(sub).model_dump(mode="json") if sub else None,
    }
    return ok(payload)


@router.patch("/{assignment_id}")
async def update_assignment(
    assignment_id: UUID,
    body: AssignmentUpdate,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssignmentService(db)
    result = await svc.update(ctx.tenant_id, assignment_id, ctx.user.id, ctx.org_role, body)
    return ok({"assignment": AssignmentResponse.model_validate(result["assignment"]).model_dump(mode="json")})


@router.delete("/{assignment_id}", status_code=status.HTTP_200_OK)
async def delete_assignment(
    assignment_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssignmentService(db)
    await svc.soft_delete(ctx.tenant_id, assignment_id, ctx.org_role)
    return ok({"message": "Assignment deleted"})


@router.post("/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: UUID,
    body: AssignmentSubmitRequest,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssignmentService(db)
    result = await svc.submit(ctx.tenant_id, assignment_id, ctx.user.id, body)
    sub = result["submission"]
    return ok(
        {
            "submission": SubmissionResponse.model_validate(sub).model_dump(mode="json"),
            "assignment": AssignmentResponse.model_validate(result["assignment"]).model_dump(mode="json"),
        },
    )


@router.get("/{assignment_id}/submission")
async def get_submission(
    assignment_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssignmentService(db)
    result = await svc.get_submission(ctx.tenant_id, assignment_id, ctx.user.id, ctx.org_role)
    sub = result["submission"]
    return ok(
        {
            "submission": SubmissionResponse.model_validate(sub).model_dump(mode="json") if sub else None,
            "assignment": AssignmentResponse.model_validate(result["assignment"]).model_dump(mode="json"),
        },
    )


@router.patch("/{assignment_id}/submission/grade")
async def grade_submission(
    assignment_id: UUID,
    body: AssignmentGradeRequest,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssignmentService(db)
    result = await svc.grade(ctx.tenant_id, assignment_id, ctx.org_role, body)
    sub = result["submission"]
    return ok(
        {
            "submission": SubmissionResponse.model_validate(sub).model_dump(mode="json"),
            "assignment": AssignmentResponse.model_validate(result["assignment"]).model_dump(mode="json"),
        },
    )
