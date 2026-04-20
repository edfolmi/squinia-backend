"""
CohortMember: links a user to a cohort with a cohort-level role.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auth.user import User
    from app.models.simulation.cohort import Cohort


class CohortMemberRole(str, Enum):
    """Role a user plays inside a cohort."""

    STUDENT = "STUDENT"
    INSTRUCTOR = "INSTRUCTOR"


class CohortMember(Base):
    """User enrolled in a cohort."""

    __tablename__ = "cohort_members"
    __table_args__ = (
        UniqueConstraint("cohort_id", "user_id", name="uq_cohort_members_cohort_user"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    cohort_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cohorts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[CohortMemberRole] = mapped_column(
        SQLEnum(CohortMemberRole, name="cohort_member_role_enum", native_enum=True),
        default=CohortMemberRole.STUDENT,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    cohort: Mapped["Cohort"] = relationship("Cohort", back_populates="members")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"CohortMember(id={self.id!s}, cohort_id={self.cohort_id!s}, user_id={self.user_id!s}, role={self.role})"
