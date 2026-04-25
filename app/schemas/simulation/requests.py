"""HTTP request bodies for simulation APIs (tenant_id never accepted from client)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.simulation.assignment import AssignmentType
from app.models.simulation.cohort import CohortStatus
from app.models.simulation.cohort_member import CohortMemberRole
from app.models.simulation.scenario import AgentRole, ScenarioDifficulty, ScenarioStatus
from app.models.simulation.simulation_session import SessionMode


class CohortCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: CohortStatus = CohortStatus.DRAFT
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class CohortMembersAddRequest(BaseModel):
    user_ids: list[UUID] = Field(..., min_length=1)
    role: CohortMemberRole = CohortMemberRole.STUDENT


class ScenarioCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    agent_role: AgentRole
    difficulty: ScenarioDifficulty = ScenarioDifficulty.INTERMEDIATE
    status: ScenarioStatus = ScenarioStatus.DRAFT
    config: dict[str, Any] = Field(default_factory=dict)
    estimated_minutes: int = Field(default=30, ge=1)
    is_template: bool = False


class RubricReorderRequest(BaseModel):
    ordered_ids: list[UUID] = Field(..., min_length=1)


class SimulationSessionChatRequest(BaseModel):
    text: str = Field(..., min_length=1, description="User message for the facilitator.")


class SimulationSessionTranscriptItem(BaseModel):
    role: Literal["USER", "ASSISTANT"] = Field(description="Speaker role inferred from LiveKit participant.")
    text: str = Field(..., min_length=1, description="Final transcript text.")
    segment_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Stable id from LiveKit transcript segment for de-duplication.",
    )
    participant_identity: Optional[str] = Field(default=None, max_length=255)
    participant_name: Optional[str] = Field(default=None, max_length=255)
    offset_ms: Optional[int] = Field(default=None, ge=0)
    is_final: bool = Field(
        default=True,
        description="Only final transcript segments should be persisted.",
    )


class SimulationSessionTranscriptIngestRequest(BaseModel):
    items: list[SimulationSessionTranscriptItem] = Field(..., min_length=1, max_length=100)


class SimulationSessionStartRequest(BaseModel):
    """
    Start a persisted simulation session (call ``POST /api/v1/sessions`` before opening the sim UI).

    ``tenant_id`` is taken from the access token, not the body.
    """

    scenario_id: UUID = Field(description="Published scenario to run.")
    cohort_id: Optional[UUID] = Field(
        default=None,
        description="Cohort context; optional if the product allows free practice in-tenant.",
    )
    mode: SessionMode = Field(
        default=SessionMode.TEXT,
        description="Interaction mode for the session (e.g. TEXT).",
    )


class InternalEvalTriggerRequest(BaseModel):
    session_id: UUID


class EvalScoreCompleteItem(BaseModel):
    rubric_item_id: UUID
    score: int = Field(..., ge=0)
    rationale: Optional[str] = None


class InternalEvalCompleteRequest(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    feedback_summary: str
    strengths: Optional[str] = None
    improvements: Optional[str] = None
    highlights: list[dict[str, Any]] = Field(default_factory=list)
    scores: list[EvalScoreCompleteItem] = Field(default_factory=list)


class AssignmentCreateRequest(BaseModel):
    assigned_to: UUID
    type: AssignmentType
    title: str = Field(..., min_length=1, max_length=255)
    instructions: Optional[str] = None
    content: dict[str, Any] = Field(default_factory=dict)
    due_at: Optional[datetime] = None
    session_id: Optional[UUID] = None


class AssignmentSubmitRequest(BaseModel):
    content: Optional[str] = None
    files: list[dict[str, Any]] = Field(default_factory=list)


class AssignmentGradeRequest(BaseModel):
    score: int = Field(..., ge=0)
    feedback: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={"example": {"score": 85, "feedback": "Good structure"}},
    )
