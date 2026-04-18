"""
Pydantic v2 schemas for Membership (user ↔ tenant + org role).
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.auth.membership import OrgRole


class MembershipBase(BaseModel):
    """Shared membership fields."""

    role: OrgRole
    is_active: bool = True


class MembershipCreate(MembershipBase):
    """Invite or add a user to a tenant."""

    user_id: UUID
    tenant_id: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "role": "STUDENT",
                "is_active": True,
            }
        }
    )


class MembershipUpdate(BaseModel):
    """Change role or suspend membership."""

    role: Optional[OrgRole] = None
    is_active: Optional[bool] = None


class MembershipResponse(MembershipBase):
    """Membership row for APIs."""

    id: UUID
    user_id: UUID
    tenant_id: UUID
    deleted_at: Optional[datetime] = None
    joined_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "7ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "role": "INSTRUCTOR",
                "is_active": True,
                "deleted_at": None,
                "joined_at": "2026-01-01T00:00:00Z",
            }
        },
    )


class MembershipList(BaseModel):
    """Paginated memberships."""

    items: list[MembershipResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
