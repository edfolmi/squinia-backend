"""
Pydantic v2 schemas for password reset flows (tokens are hashed at rest).
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.schemas.auth.password_policy import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH


class PasswordResetRequest(BaseModel):
    """Start reset from email (public)."""

    email: EmailStr


class PasswordResetSubmit(BaseModel):
    """Consume token and set a new password (public)."""

    token: str = Field(..., min_length=1, max_length=512)
    new_password: str = Field(
        ..., min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )


class PasswordResetResponse(BaseModel):
    """Audit row without raw token."""

    id: UUID
    user_id: UUID
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
