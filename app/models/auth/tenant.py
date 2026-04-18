"""
Tenant (organization) model: billing, plan limits, and per-tenant settings.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.auth.membership import Membership
    from app.models.auth.auth_session import AuthSession


class Plan(str, Enum):
    """Subscription plan tier stored as plan_enum in PostgreSQL."""

    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class Tenant(BaseModel):
    """
    Top-level tenant (organization) record.

    Attributes:
        id: Primary key UUID
        name: Display name
        slug: URL-safe unique identifier
        plan: Billing plan
        is_active: Whether the tenant can be used
        max_seats: Seat cap for the plan
        trial_ends_at: Optional trial end timestamp
        billing_email: Billing contact email
        settings: JSON document (SSO, branding, feature flags)
        deleted_at: Soft-delete timestamp
    """

    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    plan: Mapped[Plan] = mapped_column(
        SQLEnum(Plan, name="plan_enum", native_enum=True),
        default=Plan.starter,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_seats: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    memberships: Mapped[list["Membership"]] = relationship(
        "Membership",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        "AuthSession",
        back_populates="tenant",
    )

    def __repr__(self) -> str:
        return f"Tenant(id={self.id!s}, slug={self.slug!r}, plan={self.plan})"
