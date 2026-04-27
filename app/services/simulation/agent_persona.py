"""Agent persona use-cases."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.repositories.simulation import AgentPersonaRepository
from app.schemas.simulation.agent_persona import AgentPersonaCreate, AgentPersonaUpdate


class AgentPersonaService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.personas = AgentPersonaRepository(db)

    async def create(self, tenant_id: UUID, user_id: UUID, body: AgentPersonaCreate) -> dict:
        data = body.model_dump()
        if data.get("is_default"):
            await self.personas.clear_default(tenant_id)
        row = await self.personas.create({"tenant_id": tenant_id, "created_by": user_id, **data})
        await self.db.commit()
        return {"persona": row}

    async def list(self, tenant_id: UUID) -> dict:
        return {"items": await self.personas.list_for_tenant(tenant_id)}

    async def get(self, tenant_id: UUID, persona_id: UUID) -> dict:
        row = await self.personas.get(persona_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Persona not found")
        return {"persona": row}

    async def update(self, tenant_id: UUID, persona_id: UUID, body: AgentPersonaUpdate) -> dict:
        data = body.model_dump(exclude_unset=True)
        if data.get("is_default"):
            await self.personas.clear_default(tenant_id, except_id=persona_id)
        row = await self.personas.update(persona_id, tenant_id, data)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Persona not found")
        await self.db.commit()
        return {"persona": row}

    async def delete(self, tenant_id: UUID, persona_id: UUID) -> None:
        row = await self.personas.get(persona_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Persona not found")
        await self.personas.soft_delete(persona_id, tenant_id)
        await self.db.commit()
