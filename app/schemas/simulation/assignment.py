"""
Pydantic v2 schemas for Assignment.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.simulation.assignment import AssignmentStatus, AssignmentType


class AssignmentBase(BaseModel):
    """Shared assignment fields."""

    type: AssignmentType
    title: str = Field(..., min_length=1, max_length=255)
    instructions: Optional[str] = None
    content: dict[str, Any] = Field(default_factory=dict)
    due_at: Optional[datetime] = None


class AssignmentCreate(AssignmentBase):
    """Issue an assignment."""

    tenant_id: UUID
    session_id: Optional[UUID] = None
    assigned_to: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": None,
                "assigned_to": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "type": "REFLECTION",
                "title": "Post-interview reflection",
                "instructions": "Write a 200-word reflection on your performance.",
                "content": {},
                "due_at": "2026-07-01T23:59:59Z",
            }
        }
    )


class AssignmentUpdate(BaseModel):
    """Partial assignment update."""

    status: Optional[AssignmentStatus] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    instructions: Optional[str] = None
    content: Optional[dict[str, Any]] = None
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AssignmentResponse(AssignmentBase):
    """Assignment returned to clients."""

    id: UUID
    tenant_id: UUID
    session_id: Optional[UUID] = None
    assigned_to: UUID
    assigned_by: UUID
    status: AssignmentStatus
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssignmentList(BaseModel):
    """Paginated assignment list."""

    items: list[AssignmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
