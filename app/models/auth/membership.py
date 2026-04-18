"""
Membership links users to tenants with an organization role.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auth.user import User
    from app.models.auth.tenant import Tenant


class OrgRole(str, Enum):
    """Organization-scoped role (org_role_enum)."""

    ORG_OWNER = "ORG_OWNER"
    ORG_ADMIN = "ORG_ADMIN"
    INSTRUCTOR = "INSTRUCTOR"
    STUDENT = "STUDENT"


class Membership(Base):
    """User membership in a tenant with a single org role."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_memberships_user_tenant"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[OrgRole] = mapped_column(
        SQLEnum(OrgRole, name="org_role_enum", native_enum=True),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="memberships")
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="memberships")

    def __repr__(self) -> str:
        return f"Membership(id={self.id!s}, user_id={self.user_id!s}, tenant_id={self.tenant_id!s}, role={self.role})"
