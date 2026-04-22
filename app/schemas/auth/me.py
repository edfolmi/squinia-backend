"""Response shapes for ``GET /auth/me`` (shell + routing)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.auth.membership import OrgRole


class MeMembershipItem(BaseModel):
    """One active org membership with tenant display fields."""

    model_config = ConfigDict(from_attributes=False)

    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    org_role: OrgRole
    joined_at: datetime


class MeResponse(BaseModel):
    """Envelope ``data`` for current session (extends flat ``user`` for clients)."""

    user: dict[str, Any]
    memberships: list[MeMembershipItem]
    default_tenant_id: Optional[UUID] = None
    default_org_role: Optional[OrgRole] = None
