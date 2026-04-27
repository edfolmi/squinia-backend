"""Scenario and rubric use-cases."""
from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.simulation.scenario import ScenarioStatus
from app.repositories.simulation import AgentPersonaRepository, ScenarioRepository
from app.schemas.simulation.requests import ScenarioCreateRequest
from app.schemas.simulation.scenario import ScenarioUpdate
from app.schemas.simulation.scenario_rubric_item import RubricItemBase, RubricItemUpdate

logger = get_logger(__name__)


class ScenarioService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.scenarios = ScenarioRepository(db)
        self.personas = AgentPersonaRepository(db)

    async def _validate_persona(self, tenant_id: UUID, persona_id: UUID | None) -> None:
        if persona_id is None:
            return
        persona = await self.personas.get(persona_id, tenant_id)
        if not persona:
            raise AppError(status_code=400, code="INVALID_PERSONA", message="Persona does not belong to this organization")

    async def create(self, tenant_id: UUID, user_id: UUID, body: ScenarioCreateRequest) -> dict:
        await self._validate_persona(tenant_id, body.persona_id)
        row = await self.scenarios.create(
            {
                "tenant_id": tenant_id,
                "created_by": user_id,
                "persona_id": body.persona_id,
                "title": body.title,
                "description": body.description,
                "agent_role": body.agent_role,
                "difficulty": body.difficulty,
                "status": body.status,
                "config": body.config,
                "estimated_minutes": body.estimated_minutes,
                "is_template": body.is_template,
            },
        )
        await self.db.commit()
        fresh = await self.scenarios.get_with_persona(row.id, tenant_id)
        return {"scenario": fresh or row}

    async def list_paginated(
        self,
        tenant_id: UUID,
        page: int,
        limit: int,
        *,
        status=None,
        agent_role=None,
        difficulty=None,
        published_only: bool = False,
    ) -> dict:
        offset = (page - 1) * limit
        effective_status = ScenarioStatus.PUBLISHED if published_only else status
        items = await self.scenarios.list_for_tenant(
            tenant_id,
            offset=offset,
            limit=limit,
            status=effective_status,
            agent_role=agent_role,
            difficulty=difficulty,
            published_only=published_only,
        )
        total = await self.scenarios.count_for_tenant(
            tenant_id,
            status=effective_status,
            agent_role=agent_role,
            difficulty=difficulty,
            published_only=published_only,
        )
        return {"items": items, "total": total, "page": page, "limit": limit}

    async def get_detail(self, tenant_id: UUID, scenario_id: UUID) -> dict:
        row = await self.scenarios.get_with_rubric(scenario_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        return {"scenario": row, "rubric_items": list(row.rubric_items)}

    async def update(self, tenant_id: UUID, scenario_id: UUID, body: ScenarioUpdate) -> dict:
        data = body.model_dump(exclude_unset=True)
        if "persona_id" in data:
            await self._validate_persona(tenant_id, data["persona_id"])
        row = await self.scenarios.update(scenario_id, tenant_id, data)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        await self.db.commit()
        return {"scenario": row}

    async def soft_delete(self, tenant_id: UUID, scenario_id: UUID) -> None:
        row = await self.scenarios.get(scenario_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        await self.scenarios.soft_delete(scenario_id, tenant_id)
        await self.db.commit()

    async def publish(self, tenant_id: UUID, scenario_id: UUID) -> dict:
        row = await self.scenarios.update(scenario_id, tenant_id, {"status": ScenarioStatus.PUBLISHED})
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        await self.db.commit()
        return {"scenario": row}

    async def duplicate(self, tenant_id: UUID, user_id: UUID, scenario_id: UUID) -> dict:
        src = await self.scenarios.get_with_rubric(scenario_id, tenant_id)
        if not src:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        new_data = {
            "tenant_id": tenant_id,
            "created_by": user_id,
            "persona_id": src.persona_id,
            "title": f"{src.title} (copy)",
            "description": src.description,
            "agent_role": src.agent_role,
            "difficulty": src.difficulty,
            "status": ScenarioStatus.DRAFT,
            "config": deepcopy(src.config or {}),
            "estimated_minutes": src.estimated_minutes,
            "is_template": False,
        }
        new_scenario = await self.scenarios.create(new_data)
        for item in sorted(src.rubric_items, key=lambda x: (x.sort_order, str(x.id))):
            await self.scenarios.create_rubric_item(
                {
                    "scenario_id": new_scenario.id,
                    "criterion": item.criterion,
                    "description": item.description,
                    "max_score": item.max_score,
                    "weight": item.weight,
                    "sort_order": item.sort_order,
                },
            )
        await self.db.commit()
        fresh = await self.scenarios.get_with_rubric(new_scenario.id, tenant_id)
        if not fresh:
            raise AppError(status_code=500, code="INTERNAL_ERROR", message="Failed to load duplicated scenario")
        logger.info("Scenario duplicated", source=str(scenario_id), new=str(new_scenario.id))
        return {"scenario": fresh, "rubric_items": list(fresh.rubric_items)}

    async def add_rubric_item(self, tenant_id: UUID, scenario_id: UUID, body: RubricItemBase) -> dict:
        scenario = await self.scenarios.get(scenario_id, tenant_id)
        if not scenario:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        row = await self.scenarios.create_rubric_item(
            {
                "scenario_id": scenario_id,
                "criterion": body.criterion,
                "description": body.description,
                "max_score": body.max_score,
                "weight": body.weight,
                "sort_order": body.sort_order,
            },
        )
        await self.db.commit()
        return {"rubric_item": row}

    async def list_rubric_items(self, tenant_id: UUID, scenario_id: UUID) -> dict:
        scenario = await self.scenarios.get(scenario_id, tenant_id)
        if not scenario:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        items = await self.scenarios.list_rubric_items(scenario_id)
        return {"items": items}

    async def update_rubric_item(
        self,
        tenant_id: UUID,
        scenario_id: UUID,
        rubric_id: UUID,
        body: RubricItemUpdate,
    ) -> dict:
        scenario = await self.scenarios.get(scenario_id, tenant_id)
        if not scenario:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        data = body.model_dump(exclude_unset=True)
        row = await self.scenarios.update_rubric_item(rubric_id, scenario_id, data)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Rubric item not found")
        await self.db.commit()
        return {"rubric_item": row}

    async def delete_rubric_item(self, tenant_id: UUID, scenario_id: UUID, rubric_id: UUID) -> None:
        scenario = await self.scenarios.get(scenario_id, tenant_id)
        if not scenario:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        ok = await self.scenarios.delete_rubric_item(rubric_id, scenario_id)
        if not ok:
            raise AppError(status_code=404, code="NOT_FOUND", message="Rubric item not found")
        await self.db.commit()

    async def reorder_rubric(self, tenant_id: UUID, scenario_id: UUID, ordered_ids: list[UUID]) -> dict:
        scenario = await self.scenarios.get(scenario_id, tenant_id)
        if not scenario:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        existing = {str(i.id) for i in await self.scenarios.list_rubric_items(scenario_id)}
        if set(str(i) for i in ordered_ids) != existing:
            raise AppError(
                status_code=400,
                code="VALIDATION_ERROR",
                message="ordered_ids must match all rubric item ids for this scenario",
            )
        await self.scenarios.reorder_rubric_items(scenario_id, ordered_ids)
        await self.db.commit()
        items = await self.scenarios.list_rubric_items(scenario_id)
        return {"items": items}
