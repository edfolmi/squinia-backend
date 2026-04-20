"""Student evaluation history."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.response import ok_paginated
from app.schemas.simulation.evaluation import EvaluationResponse
from app.core.tenant_access import TenantMember
from app.services.simulation.evaluation import EvaluationService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}/evaluations")
async def list_user_evaluations(
    user_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    svc = EvaluationService(db)
    result = await svc.list_for_user(ctx.tenant_id, user_id, ctx.user.id, ctx.org_role, page, limit)
    items = [EvaluationResponse.model_validate(i).model_dump(mode="json") for i in result["items"]]
    return ok_paginated(items, total=result["total"], page=result["page"], page_size=result["limit"])
