"""Agent persona persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation.agent_persona import AgentPersona


class AgentPersonaRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict[str, Any]) -> AgentPersona:
        row = AgentPersona(**data)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get(self, persona_id: UUID, tenant_id: UUID) -> Optional[AgentPersona]:
        stmt = select(AgentPersona).where(
            AgentPersona.id == persona_id,
            AgentPersona.tenant_id == tenant_id,
            AgentPersona.deleted_at.is_(None),
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def list_for_tenant(self, tenant_id: UUID) -> list[AgentPersona]:
        stmt = (
            select(AgentPersona)
            .where(AgentPersona.tenant_id == tenant_id, AgentPersona.deleted_at.is_(None))
            .order_by(AgentPersona.is_default.desc(), AgentPersona.updated_at.desc(), AgentPersona.name.asc())
        )
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def update(self, persona_id: UUID, tenant_id: UUID, data: dict[str, Any]) -> Optional[AgentPersona]:
        if not data:
            return await self.get(persona_id, tenant_id)
        await self.db.execute(
            update(AgentPersona)
            .where(AgentPersona.id == persona_id, AgentPersona.tenant_id == tenant_id, AgentPersona.deleted_at.is_(None))
            .values(**data),
        )
        await self.db.flush()
        return await self.get(persona_id, tenant_id)

    async def clear_default(self, tenant_id: UUID, *, except_id: UUID | None = None) -> None:
        stmt = update(AgentPersona).where(
            AgentPersona.tenant_id == tenant_id,
            AgentPersona.deleted_at.is_(None),
        )
        if except_id is not None:
            stmt = stmt.where(AgentPersona.id != except_id)
        await self.db.execute(stmt.values(is_default=False))
        await self.db.flush()

    async def soft_delete(self, persona_id: UUID, tenant_id: UUID) -> None:
        await self.db.execute(
            update(AgentPersona)
            .where(AgentPersona.id == persona_id, AgentPersona.tenant_id == tenant_id, AgentPersona.deleted_at.is_(None))
            .values(deleted_at=datetime.now(timezone.utc), is_default=False),
        )
        await self.db.flush()
