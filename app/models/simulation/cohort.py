"""
Cohort: a time-bound group of users within a tenant.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.auth.tenant import Tenant
    from app.models.simulation.cohort_member import CohortMember
    from app.models.simulation.simulation_session import SimulationSession


class CohortStatus(str, Enum):
    """Lifecycle status of a cohort."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class Cohort(BaseModel):
    """
    Cohort within a tenant.

    Attributes:
        id: Primary key UUID
        tenant_id: Owning tenant
        name: Display name
        description: Optional long-form description
        status: Lifecycle status
        starts_at: Scheduled start
        ends_at: Scheduled end
        deleted_at: Soft-delete timestamp
    """

    __tablename__ = "cohorts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[CohortStatus] = mapped_column(
        SQLEnum(CohortStatus, name="cohort_status_enum", native_enum=True),
        default=CohortStatus.DRAFT,
        nullable=False,
        index=True,
    )
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant")
    members: Mapped[list["CohortMember"]] = relationship(
        "CohortMember",
        back_populates="cohort",
        cascade="all, delete-orphan",
    )
    simulation_sessions: Mapped[list["SimulationSession"]] = relationship(
        "SimulationSession",
        back_populates="cohort",
    )

    def __repr__(self) -> str:
        return f"Cohort(id={self.id!s}, name={self.name!r}, status={self.status})"
