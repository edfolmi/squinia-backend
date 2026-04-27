"""Scenario and rubric item persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.simulation.scenario import AgentRole, Scenario, ScenarioDifficulty, ScenarioStatus
from app.models.simulation.scenario_rubric_item import ScenarioRubricItem


class ScenarioRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict[str, Any]) -> Scenario:
        row = Scenario(**data)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get(self, scenario_id: UUID, tenant_id: UUID) -> Optional[Scenario]:
        stmt = select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.tenant_id == tenant_id,
            Scenario.deleted_at.is_(None),
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def get_with_rubric(self, scenario_id: UUID, tenant_id: UUID) -> Optional[Scenario]:
        stmt = (
            select(Scenario)
            .options(selectinload(Scenario.rubric_items), selectinload(Scenario.persona))
            .where(
                Scenario.id == scenario_id,
                Scenario.tenant_id == tenant_id,
                Scenario.deleted_at.is_(None),
            )
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        offset: int,
        limit: int,
        status: Optional[ScenarioStatus] = None,
        agent_role: Optional[AgentRole] = None,
        difficulty: Optional[ScenarioDifficulty] = None,
        published_only: bool = False,
    ) -> list[Scenario]:
        stmt = (
            select(Scenario)
            .options(selectinload(Scenario.persona))
            .where(Scenario.tenant_id == tenant_id, Scenario.deleted_at.is_(None))
        )
        if status is not None:
            stmt = stmt.where(Scenario.status == status)
        if agent_role is not None:
            stmt = stmt.where(Scenario.agent_role == agent_role)
        if difficulty is not None:
            stmt = stmt.where(Scenario.difficulty == difficulty)
        if published_only:
            stmt = stmt.where(Scenario.status == ScenarioStatus.PUBLISHED)
        stmt = stmt.order_by(Scenario.updated_at.desc()).offset(offset).limit(limit)
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def count_for_tenant(
        self,
        tenant_id: UUID,
        *,
        status: Optional[ScenarioStatus] = None,
        agent_role: Optional[AgentRole] = None,
        difficulty: Optional[ScenarioDifficulty] = None,
        published_only: bool = False,
    ) -> int:
        stmt = select(func.count()).select_from(Scenario).where(
            Scenario.tenant_id == tenant_id,
            Scenario.deleted_at.is_(None),
        )
        if status is not None:
            stmt = stmt.where(Scenario.status == status)
        if agent_role is not None:
            stmt = stmt.where(Scenario.agent_role == agent_role)
        if difficulty is not None:
            stmt = stmt.where(Scenario.difficulty == difficulty)
        if published_only:
            stmt = stmt.where(Scenario.status == ScenarioStatus.PUBLISHED)
        r = await self.db.execute(stmt)
        return int(r.scalar_one() or 0)

    async def update(self, scenario_id: UUID, tenant_id: UUID, data: dict[str, Any]) -> Optional[Scenario]:
        if not data:
            return await self.get_with_persona(scenario_id, tenant_id)
        await self.db.execute(
            update(Scenario)
            .where(Scenario.id == scenario_id, Scenario.tenant_id == tenant_id, Scenario.deleted_at.is_(None))
            .values(**data),
        )
        await self.db.flush()
        return await self.get_with_persona(scenario_id, tenant_id)

    async def get_with_persona(self, scenario_id: UUID, tenant_id: UUID) -> Optional[Scenario]:
        stmt = (
            select(Scenario)
            .options(selectinload(Scenario.persona))
            .where(
                Scenario.id == scenario_id,
                Scenario.tenant_id == tenant_id,
                Scenario.deleted_at.is_(None),
            )
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def soft_delete(self, scenario_id: UUID, tenant_id: UUID) -> None:
        await self.db.execute(
            update(Scenario)
            .where(Scenario.id == scenario_id, Scenario.tenant_id == tenant_id, Scenario.deleted_at.is_(None))
            .values(deleted_at=datetime.now(timezone.utc)),
        )
        await self.db.flush()

    async def list_rubric_items(self, scenario_id: UUID) -> list[ScenarioRubricItem]:
        stmt = (
            select(ScenarioRubricItem)
            .where(ScenarioRubricItem.scenario_id == scenario_id)
            .order_by(ScenarioRubricItem.sort_order.asc(), ScenarioRubricItem.id.asc())
        )
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def get_rubric_item(self, rubric_id: UUID, scenario_id: UUID) -> Optional[ScenarioRubricItem]:
        stmt = select(ScenarioRubricItem).where(
            ScenarioRubricItem.id == rubric_id,
            ScenarioRubricItem.scenario_id == scenario_id,
        )
        r = await self.db.execute(stmt)
        return r.scalar_one_or_none()

    async def create_rubric_item(self, data: dict[str, Any]) -> ScenarioRubricItem:
        row = ScenarioRubricItem(**data)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def update_rubric_item(self, rubric_id: UUID, scenario_id: UUID, data: dict[str, Any]) -> Optional[ScenarioRubricItem]:
        if not data:
            return await self.get_rubric_item(rubric_id, scenario_id)
        await self.db.execute(
            update(ScenarioRubricItem)
            .where(
                ScenarioRubricItem.id == rubric_id,
                ScenarioRubricItem.scenario_id == scenario_id,
            )
            .values(**data),
        )
        await self.db.flush()
        return await self.get_rubric_item(rubric_id, scenario_id)

    async def delete_rubric_item(self, rubric_id: UUID, scenario_id: UUID) -> bool:
        res = await self.db.execute(
            delete(ScenarioRubricItem).where(
                ScenarioRubricItem.id == rubric_id,
                ScenarioRubricItem.scenario_id == scenario_id,
            ),
        )
        await self.db.flush()
        return (res.rowcount or 0) > 0

    async def reorder_rubric_items(self, scenario_id: UUID, ordered_ids: list[UUID]) -> None:
        for order, rid in enumerate(ordered_ids):
            await self.db.execute(
                update(ScenarioRubricItem)
                .where(
                    ScenarioRubricItem.id == rid,
                    ScenarioRubricItem.scenario_id == scenario_id,
                )
                .values(sort_order=order),
            )
        await self.db.flush()
