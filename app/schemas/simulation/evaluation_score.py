"""
Pydantic v2 schemas for EvaluationScore (per-rubric-item score).
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class EvaluationScoreBase(BaseModel):
    """Shared evaluation score fields."""

    score: int = Field(..., ge=0)
    rationale: Optional[str] = None


class EvaluationScoreCreate(EvaluationScoreBase):
    """Record a score for a rubric item."""

    evaluation_id: UUID
    rubric_item_id: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "evaluation_id": "550e8400-e29b-41d4-a716-446655440000",
                "rubric_item_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "score": 8,
                "rationale": "Clear communication with minor hesitations",
            }
        }
    )


class EvaluationScoreUpdate(BaseModel):
    """Update a rubric score."""

    score: Optional[int] = Field(None, ge=0)
    rationale: Optional[str] = None


class EvaluationScoreResponse(EvaluationScoreBase):
    """Evaluation score returned to clients."""

    id: UUID
    evaluation_id: UUID
    rubric_item_id: UUID

    model_config = ConfigDict(from_attributes=True)
