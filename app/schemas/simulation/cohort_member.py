"""
Pydantic v2 schemas for CohortMember.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.simulation.cohort_member import CohortMemberRole


class CohortMemberBase(BaseModel):
    """Shared cohort member fields."""

    role: CohortMemberRole = CohortMemberRole.STUDENT


class CohortMemberCreate(CohortMemberBase):
    """Add a user to a cohort."""

    cohort_id: UUID
    user_id: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cohort_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "role": "STUDENT",
            }
        }
    )


class CohortMemberUpdate(BaseModel):
    """Change member role."""

    role: Optional[CohortMemberRole] = None


class CohortMemberResponse(CohortMemberBase):
    """Cohort member row."""

    id: UUID
    cohort_id: UUID
    user_id: UUID
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CohortMemberList(BaseModel):
    """Paginated cohort members."""

    items: list[CohortMemberResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
