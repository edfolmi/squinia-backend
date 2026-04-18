"""
Pydantic v2 schemas for email verification.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class EmailVerificationRequest(BaseModel):
    """Request a new verification email."""

    email: EmailStr


class EmailVerificationSubmit(BaseModel):
    """Confirm email using the token from the message."""

    token: str = Field(..., min_length=1, max_length=512)


class EmailVerificationResponse(BaseModel):
    """Verification record without token hash."""

    id: UUID
    user_id: UUID
    email: str
    expires_at: datetime
    verified_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
