"""
Pydantic v2 schemas for ScenarioRubricItem.
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class RubricItemBase(BaseModel):
    """Shared rubric item fields."""

    criterion: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    max_score: int = Field(default=10, ge=1)
    weight: int = Field(default=1, ge=0)
    sort_order: int = Field(default=0, ge=0)


class RubricItemCreate(RubricItemBase):
    """Create a rubric item for a scenario."""

    scenario_id: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scenario_id": "550e8400-e29b-41d4-a716-446655440000",
                "criterion": "Communication Clarity",
                "description": "Articulates ideas clearly and concisely",
                "max_score": 10,
                "weight": 2,
                "sort_order": 0,
            }
        }
    )


class RubricItemUpdate(BaseModel):
    """Partial rubric item update."""

    criterion: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    max_score: Optional[int] = Field(None, ge=1)
    weight: Optional[int] = Field(None, ge=0)
    sort_order: Optional[int] = Field(None, ge=0)


class RubricItemResponse(RubricItemBase):
    """Rubric item returned to clients."""

    id: UUID
    scenario_id: UUID

    model_config = ConfigDict(from_attributes=True)
