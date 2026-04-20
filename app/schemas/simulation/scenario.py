"""
Pydantic v2 schemas for Scenario.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.simulation.scenario import AgentRole, ScenarioDifficulty, ScenarioStatus


class ScenarioBase(BaseModel):
    """Shared scenario fields."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    agent_role: AgentRole
    difficulty: ScenarioDifficulty = ScenarioDifficulty.INTERMEDIATE
    status: ScenarioStatus = ScenarioStatus.DRAFT
    config: dict[str, Any] = Field(default_factory=dict)
    estimated_minutes: int = Field(default=30, ge=1)
    is_template: bool = False


class ScenarioCreate(ScenarioBase):
    """Create a scenario within a tenant."""

    tenant_id: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Technical Interview: Python",
                "description": "A mock technical interview focusing on Python fundamentals",
                "agent_role": "TECHNICAL_INTERVIEWER",
                "difficulty": "INTERMEDIATE",
                "status": "DRAFT",
                "config": {
                    "system_prompt": "You are a senior software engineer...",
                    "persona_name": "Alex",
                    "opening_message": "Hi, thanks for joining today.",
                },
                "estimated_minutes": 30,
                "is_template": False,
            }
        }
    )


class ScenarioUpdate(BaseModel):
    """Partial scenario update."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    difficulty: Optional[ScenarioDifficulty] = None
    status: Optional[ScenarioStatus] = None
    config: Optional[dict[str, Any]] = None
    estimated_minutes: Optional[int] = Field(None, ge=1)
    is_template: Optional[bool] = None


class ScenarioResponse(ScenarioBase):
    """Scenario returned to clients."""

    id: UUID
    tenant_id: UUID
    created_by: UUID
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScenarioList(BaseModel):
    """Paginated scenario list."""

    items: list[ScenarioResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
