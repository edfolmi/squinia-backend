"""
Pydantic v2 schemas for auth sessions (refresh rotation, device list).
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AuthSessionCreate(BaseModel):
    """Internal use when persisting a new refresh session."""

    user_id: UUID
    tenant_id: Optional[UUID] = None
    refresh_token_hash: str = Field(..., min_length=1, max_length=255)
    user_agent: Optional[str] = Field(None, max_length=8000)
    ip_address: Optional[str] = Field(None, max_length=45)
    expires_at: datetime


class AuthSessionResponse(BaseModel):
    """Session metadata exposed to the user (no token hash)."""

    id: UUID
    user_id: UUID
    tenant_id: Optional[UUID] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "tenant_id": "7ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "user_agent": "Mozilla/5.0",
                "ip_address": "192.0.2.1",
                "expires_at": "2026-02-01T00:00:00Z",
                "created_at": "2026-01-01T00:00:00Z",
            }
        },
    )
