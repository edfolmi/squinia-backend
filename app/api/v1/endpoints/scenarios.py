"""Scenario service HTTP API."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.tenant_access import ScenarioWriter, TenantMember
from app.db.session import get_db
from app.models.auth.membership import OrgRole
from app.models.simulation.scenario import AgentRole, ScenarioDifficulty, ScenarioStatus
from app.schemas.response import ok, ok_paginated
from app.schemas.simulation.requests import RubricReorderRequest, ScenarioCreateRequest
from app.schemas.simulation.responses import ScenarioDetailResponse
from app.schemas.simulation.scenario import ScenarioResponse, ScenarioUpdate
from app.schemas.simulation.scenario_rubric_item import RubricItemBase, RubricItemResponse, RubricItemUpdate
from app.services.simulation.scenario import ScenarioService

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_scenario(
    body: ScenarioCreateRequest,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    result = await svc.create(ctx.tenant_id, ctx.user.id, body)
    return ok({"scenario": ScenarioResponse.model_validate(result["scenario"]).model_dump(mode="json")})


@router.get("")
async def list_scenarios(
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: ScenarioStatus | None = Query(None),
    agent_role: AgentRole | None = Query(None),
    difficulty: ScenarioDifficulty | None = Query(None),
):
    svc = ScenarioService(db)
    published_only = ctx.org_role == OrgRole.STUDENT
    result = await svc.list_paginated(
        ctx.tenant_id,
        page,
        limit,
        status=status,
        agent_role=agent_role,
        difficulty=difficulty,
        published_only=published_only,
    )
    items = [ScenarioResponse.model_validate(i).model_dump(mode="json") for i in result["items"]]
    return ok_paginated(items, total=result["total"], page=result["page"], page_size=result["limit"])


@router.get("/{scenario_id}")
async def get_scenario(
    scenario_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    result = await svc.get_detail(ctx.tenant_id, scenario_id)
    scenario = result["scenario"]
    if ctx.org_role == OrgRole.STUDENT and scenario.status != ScenarioStatus.PUBLISHED:
        raise AppError(status_code=403, code="FORBIDDEN", message="Scenario is not published")
    detail = ScenarioDetailResponse.model_validate(
        {
            **ScenarioResponse.model_validate(scenario).model_dump(),
            "rubric_items": [RubricItemResponse.model_validate(i).model_dump() for i in result["rubric_items"]],
        },
    )
    return ok({"scenario": detail.model_dump(mode="json")})


@router.patch("/{scenario_id}")
async def update_scenario(
    scenario_id: UUID,
    body: ScenarioUpdate,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    result = await svc.update(ctx.tenant_id, scenario_id, body)
    return ok({"scenario": ScenarioResponse.model_validate(result["scenario"]).model_dump(mode="json")})


@router.delete("/{scenario_id}", status_code=status.HTTP_200_OK)
async def delete_scenario(
    scenario_id: UUID,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    await svc.soft_delete(ctx.tenant_id, scenario_id)
    return ok({"message": "Scenario deleted"})


@router.post("/{scenario_id}/publish")
async def publish_scenario(
    scenario_id: UUID,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    result = await svc.publish(ctx.tenant_id, scenario_id)
    return ok({"scenario": ScenarioResponse.model_validate(result["scenario"]).model_dump(mode="json")})


@router.post("/{scenario_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_scenario(
    scenario_id: UUID,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    result = await svc.duplicate(ctx.tenant_id, ctx.user.id, scenario_id)
    scenario = result["scenario"]
    detail = ScenarioDetailResponse.model_validate(
        {
            **ScenarioResponse.model_validate(scenario).model_dump(),
            "rubric_items": [RubricItemResponse.model_validate(i).model_dump() for i in result["rubric_items"]],
        },
    )
    return ok({"scenario": detail.model_dump(mode="json")})


@router.post("/{scenario_id}/rubric-items", status_code=status.HTTP_201_CREATED)
async def add_rubric_item(
    scenario_id: UUID,
    body: RubricItemBase,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    result = await svc.add_rubric_item(ctx.tenant_id, scenario_id, body)
    return ok({"rubric_item": RubricItemResponse.model_validate(result["rubric_item"]).model_dump(mode="json")})


@router.get("/{scenario_id}/rubric-items")
async def list_rubric_items(
    scenario_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    result = await svc.list_rubric_items(ctx.tenant_id, scenario_id)
    items = [RubricItemResponse.model_validate(i).model_dump(mode="json") for i in result["items"]]
    return ok({"items": items})


@router.patch("/{scenario_id}/rubric-items/{rubric_id}")
async def update_rubric_item(
    scenario_id: UUID,
    rubric_id: UUID,
    body: RubricItemUpdate,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    result = await svc.update_rubric_item(ctx.tenant_id, scenario_id, rubric_id, body)
    return ok({"rubric_item": RubricItemResponse.model_validate(result["rubric_item"]).model_dump(mode="json")})


@router.delete("/{scenario_id}/rubric-items/{rubric_id}", status_code=status.HTTP_200_OK)
async def delete_rubric_item(
    scenario_id: UUID,
    rubric_id: UUID,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    await svc.delete_rubric_item(ctx.tenant_id, scenario_id, rubric_id)
    return ok({"message": "Rubric item deleted"})


@router.put("/{scenario_id}/rubric-items/order")
async def reorder_rubric_items(
    scenario_id: UUID,
    body: RubricReorderRequest,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ScenarioService(db)
    result = await svc.reorder_rubric(ctx.tenant_id, scenario_id, body.ordered_ids)
    items = [RubricItemResponse.model_validate(i).model_dump(mode="json") for i in result["items"]]
    return ok({"items": items})
