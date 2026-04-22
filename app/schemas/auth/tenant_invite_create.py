"""Org-admin minted tenant invite."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.auth.membership import OrgRole


class CreateTenantInviteRequest(BaseModel):
    """Invite someone to the current JWT tenant."""

    email: EmailStr
    role: OrgRole = Field(
        default=OrgRole.STUDENT,
        description="Organization role granted when the invite is accepted (typically STUDENT or INSTRUCTOR).",
    )
    expires_in_days: int = Field(default=14, ge=1, le=90)


class CreateTenantInviteResponse(BaseModel):
    invite_id: UUID
    email: str
    role: OrgRole
    expires_at: datetime
    token: str = Field(description="One-time secret; treat like a password. Deliver over HTTPS only.")
    invite_url: str = Field(description="Absolute URL for the accept-invite screen including token.")
