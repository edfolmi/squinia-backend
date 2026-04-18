"""
Pydantic v2 schemas for Tenant model.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.auth.tenant import Plan


class TenantBase(BaseModel):
    """Shared tenant fields."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    plan: Plan = Plan.starter
    is_active: bool = True
    max_seats: int = Field(default=50, ge=1)
    trial_ends_at: Optional[datetime] = None
    billing_email: Optional[EmailStr] = None
    settings: dict[str, Any] = Field(default_factory=dict)


class TenantCreate(TenantBase):
    """Create tenant (admin or self-serve signup)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Learning",
                "slug": "acme-learning",
                "plan": "starter",
                "max_seats": 50,
                "billing_email": "billing@acme.example",
                "settings": {},
            }
        }
    )


class TenantUpdate(BaseModel):
    """Partial tenant update."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    plan: Optional[Plan] = None
    is_active: Optional[bool] = None
    max_seats: Optional[int] = Field(None, ge=1)
    trial_ends_at: Optional[datetime] = None
    billing_email: Optional[EmailStr] = None
    settings: Optional[dict[str, Any]] = None


class TenantResponse(TenantBase):
    """Tenant returned to clients."""

    id: UUID
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Acme Learning",
                "slug": "acme-learning",
                "plan": "starter",
                "is_active": True,
                "max_seats": 50,
                "trial_ends_at": None,
                "billing_email": "billing@acme.example",
                "settings": {},
                "deleted_at": None,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        },
    )


class TenantList(BaseModel):
    """Paginated tenant list."""

    items: list[TenantResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
