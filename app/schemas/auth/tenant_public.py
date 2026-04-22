"""Minimal tenant read model for shell / settings."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.auth.tenant import Plan


class TenantPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    plan: Plan
    is_active: bool
