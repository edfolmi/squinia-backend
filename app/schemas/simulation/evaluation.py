"""
Pydantic v2 schemas for Evaluation.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.simulation.evaluation import EvalStatus


class EvaluationBase(BaseModel):
    """Shared evaluation fields."""

    status: EvalStatus = EvalStatus.PENDING


class EvaluationCreate(EvaluationBase):
    """Queue an evaluation for a session."""

    session_id: UUID
    tenant_id: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "status": "PENDING",
            }
        }
    )


class EvaluationUpdate(BaseModel):
    """Update evaluation results."""

    status: Optional[EvalStatus] = None
    overall_score: Optional[int] = Field(None, ge=0, le=100)
    feedback_summary: Optional[str] = None
    strengths: Optional[str] = None
    improvements: Optional[str] = None
    highlights: Optional[list[dict[str, Any]]] = None
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class EvaluationResponse(EvaluationBase):
    """Evaluation returned to clients."""

    id: UUID
    session_id: UUID
    tenant_id: UUID
    overall_score: Optional[int] = None
    feedback_summary: Optional[str] = None
    strengths: Optional[str] = None
    improvements: Optional[str] = None
    highlights: list[dict[str, Any]] = []
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
