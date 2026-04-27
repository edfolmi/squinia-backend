"""Agent persona HTTP API."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_access import ScenarioWriter, TenantMember
from app.db.session import get_db
from app.schemas.response import ok
from app.schemas.simulation.agent_persona import AgentPersonaCreate, AgentPersonaResponse, AgentPersonaUpdate
from app.services.simulation.agent_persona import AgentPersonaService

router = APIRouter(prefix="/agent-personas", tags=["Agent personas"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent_persona(
    body: AgentPersonaCreate,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AgentPersonaService(db)
    result = await svc.create(ctx.tenant_id, ctx.user.id, body)
    return ok({"persona": AgentPersonaResponse.model_validate(result["persona"]).model_dump(mode="json")})


@router.get("")
async def list_agent_personas(
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AgentPersonaService(db)
    result = await svc.list(ctx.tenant_id)
    items = [AgentPersonaResponse.model_validate(i).model_dump(mode="json") for i in result["items"]]
    return ok({"items": items})


@router.get("/{persona_id}")
async def get_agent_persona(
    persona_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AgentPersonaService(db)
    result = await svc.get(ctx.tenant_id, persona_id)
    return ok({"persona": AgentPersonaResponse.model_validate(result["persona"]).model_dump(mode="json")})


@router.patch("/{persona_id}")
async def update_agent_persona(
    persona_id: UUID,
    body: AgentPersonaUpdate,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AgentPersonaService(db)
    result = await svc.update(ctx.tenant_id, persona_id, body)
    return ok({"persona": AgentPersonaResponse.model_validate(result["persona"]).model_dump(mode="json")})


@router.delete("/{persona_id}", status_code=status.HTTP_200_OK)
async def delete_agent_persona(
    persona_id: UUID,
    ctx: ScenarioWriter,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AgentPersonaService(db)
    await svc.delete(ctx.tenant_id, persona_id)
    return ok({"message": "Persona deleted"})
