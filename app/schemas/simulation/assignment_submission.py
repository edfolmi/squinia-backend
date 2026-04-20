"""
Pydantic v2 schemas for AssignmentSubmission.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class SubmissionBase(BaseModel):
    """Shared submission fields."""

    content: Optional[str] = None
    files: list[dict[str, Any]] = Field(default_factory=list)


class SubmissionCreate(SubmissionBase):
    """Submit work for an assignment."""

    assignment_id: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "assignment_id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "My reflection on the session...",
                "files": [],
            }
        }
    )


class SubmissionGrade(BaseModel):
    """Grade a submission (instructor action)."""

    score: Optional[int] = Field(None, ge=0)
    feedback: Optional[str] = None


class SubmissionResponse(SubmissionBase):
    """Submission returned to clients."""

    id: UUID
    assignment_id: UUID
    user_id: UUID
    score: Optional[int] = None
    feedback: Optional[str] = None
    submitted_at: datetime
    graded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SubmissionList(BaseModel):
    """Paginated submissions."""

    items: list[SubmissionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
