"""
Pydantic v2 schemas for Message (simulation conversation turn).
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.simulation.message import MessageRole


class MessageBase(BaseModel):
    """Shared message fields."""

    role: MessageRole
    content: str = Field(..., min_length=1)
    content_type: str = Field(default="text", max_length=50)
    meta: dict[str, Any] = Field(default_factory=dict)


class MessageCreate(MessageBase):
    """Append a message to a session."""

    session_id: UUID
    turn_number: int = Field(..., ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "role": "USER",
                "content": "I would approach this problem using a hash map...",
                "content_type": "text",
                "meta": {},
                "turn_number": 1,
            }
        }
    )


class MessageResponse(MessageBase):
    """Message returned to clients."""

    id: UUID
    session_id: UUID
    turn_number: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageList(BaseModel):
    """All messages for a session (not paginated; sessions are bounded)."""

    items: list[MessageResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
