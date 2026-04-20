"""
Assignment: follow-up task issued after (or independent of) a simulation.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.auth.tenant import Tenant
    from app.models.auth.user import User
    from app.models.simulation.simulation_session import SimulationSession
    from app.models.simulation.assignment_submission import AssignmentSubmission


class AssignmentType(str, Enum):
    """Kind of follow-up work."""

    REFLECTION = "REFLECTION"
    QUIZ = "QUIZ"
    CODE_SUBMISSION = "CODE_SUBMISSION"
    RETRY_SIMULATION = "RETRY_SIMULATION"
    EXTERNAL_LINK = "EXTERNAL_LINK"


class AssignmentStatus(str, Enum):
    """Lifecycle of an assignment."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    GRADED = "GRADED"
    OVERDUE = "OVERDUE"


class Assignment(BaseModel):
    """
    Follow-up task for a user, optionally linked to a simulation session.

    Attributes:
        id: Primary key UUID
        tenant_id: Owning tenant
        session_id: Optional originating simulation session
        assigned_to: Target user
        assigned_by: Issuing user (instructor / admin)
        type: Assignment kind
        status: Lifecycle status
        title: Short name
        instructions: Long-form description
        content: JSONB payload (quiz questions, code starters, etc.)
        due_at: Optional deadline
        completed_at: When the assignment was fulfilled
    """

    __tablename__ = "assignments"

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
    session_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("simulation_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_to: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[AssignmentType] = mapped_column(
        SQLEnum(AssignmentType, name="assignment_type_enum", native_enum=True),
        nullable=False,
    )
    status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus, name="assignment_status_enum", native_enum=True),
        default=AssignmentStatus.PENDING,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant")
    session: Mapped[Optional["SimulationSession"]] = relationship("SimulationSession", back_populates="assignments")
    assignee: Mapped["User"] = relationship("User", foreign_keys=[assigned_to])
    assigner: Mapped["User"] = relationship("User", foreign_keys=[assigned_by])
    submissions: Mapped[list["AssignmentSubmission"]] = relationship(
        "AssignmentSubmission",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Assignment(id={self.id!s}, type={self.type}, status={self.status})"
