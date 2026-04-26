"""Composite API response models for OpenAPI."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.simulation.evaluation import EvaluationResponse
from app.schemas.simulation.message import MessageResponse
from app.schemas.simulation.scenario import ScenarioResponse
from app.schemas.simulation.scenario_rubric_item import RubricItemResponse
from app.schemas.simulation.simulation_session import SimulationSessionResponse


class ScenarioDetailResponse(ScenarioResponse):
    rubric_items: list[RubricItemResponse] = Field(default_factory=list)


class EvaluationScorePublic(BaseModel):
    criterion: str
    score: int
    max_score: int
    rationale: Optional[str] = None
    summary: Optional[str] = None
    example_quote: Optional[str] = None
    improvement: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EvaluationFullResponse(EvaluationResponse):
    scores: list[EvaluationScorePublic] = Field(default_factory=list)


class SessionDetailResponse(SimulationSessionResponse):
    messages: list[MessageResponse] = Field(default_factory=list)
    evaluation: Optional[EvaluationFullResponse] = None


class SessionStartResponse(BaseModel):
    session_id: UUID
    scenario_snapshot: dict[str, Any]


class SessionChatResponse(BaseModel):
    assistant_content: str
    user_turn: int
    assistant_turn: int


class SessionOpeningResponse(BaseModel):
    assistant_content: str
    assistant_turn: int


class LiveKitConnectionResponse(BaseModel):
    """Credentials for `@livekit/components-react` / `livekit-client` in the browser."""

    server_url: str
    room_name: str
    participant_token: str


class SessionTranscriptIngestResponse(BaseModel):
    accepted: int
    skipped: int
    turn_count: int


class CohortMemberProgressRow(BaseModel):
    user_id: UUID
    scores: dict[str, float] = Field(default_factory=dict)
    completion_rate: float = 0.0


class CohortProgressResponse(BaseModel):
    members: list[CohortMemberProgressRow]


class CohortMemberListItem(BaseModel):
    """Member row with lightweight progress summary."""

    id: UUID
    cohort_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    sessions_completed: int = 0
    avg_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class AnalyticsCohortOverview(BaseModel):
    total_members: int = 0
    avg_score: Optional[float] = None
    completion_rate: float = 0.0
    sessions_this_week: int = 0
    top_skill_gaps: list[str] = Field(default_factory=list)


class AnalyticsSkillMap(BaseModel):
    criteria: list[str] = Field(default_factory=list)
    members: list[dict[str, Any]] = Field(default_factory=list)


class AnalyticsProgressOverTime(BaseModel):
    dates: list[str] = Field(default_factory=list)
    series: list[dict[str, Any]] = Field(default_factory=list)


class AnalyticsUserSummary(BaseModel):
    total_sessions: int = 0
    avg_score: Optional[float] = None
    trend: str = "stable"
    weakest_criteria: list[str] = Field(default_factory=list)
    strongest_criteria: list[str] = Field(default_factory=list)


class AnalyticsScenarioStats(BaseModel):
    total_attempts: int = 0
    avg_score: Optional[float] = None
    pass_rate: Optional[float] = None
    avg_duration_seconds: Optional[float] = None
    score_distribution: dict[str, int] = Field(default_factory=dict)


class AnalyticsTenantOverview(BaseModel):
    total_tenants: int = 0
    total_sessions_today: int = 0
    active_users_30d: int = 0
