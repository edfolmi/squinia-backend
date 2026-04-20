"""
Pydantic v2 schemas for SimulationSession.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.simulation.simulation_session import SessionMode, SessionStatus


class SimulationSessionBase(BaseModel):
    """Shared session fields."""

    mode: SessionMode = SessionMode.TEXT


class SimulationSessionCreate(SimulationSessionBase):
    """Start a new simulation session."""

    tenant_id: UUID
    scenario_id: UUID
    cohort_id: Optional[UUID] = None
    scenario_snapshot: dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "scenario_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "cohort_id": None,
                "mode": "TEXT",
                "scenario_snapshot": {"system_prompt": "..."},
            }
        }
    )


class SimulationSessionUpdate(BaseModel):
    """Update session progress or status."""

    status: Optional[SessionStatus] = None
    mode: Optional[SessionMode] = None
    turn_count: Optional[int] = Field(None, ge=0)
    duration_seconds: Optional[int] = Field(None, ge=0)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class SimulationSessionResponse(SimulationSessionBase):
    """Session returned to clients."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    scenario_id: UUID
    cohort_id: Optional[UUID] = None
    status: SessionStatus
    turn_count: int
    duration_seconds: int
    scenario_snapshot: dict[str, Any]
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimulationSessionList(BaseModel):
    """Paginated session list."""

    items: list[SimulationSessionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
