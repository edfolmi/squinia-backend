"""
SimulationSession: a single user run through a scenario.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.auth.tenant import Tenant
    from app.models.auth.user import User
    from app.models.simulation.scenario import Scenario
    from app.models.simulation.cohort import Cohort
    from app.models.simulation.message import Message
    from app.models.simulation.evaluation import Evaluation
    from app.models.simulation.assignment import Assignment


class SessionStatus(str, Enum):
    """Runtime status of a simulation session."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    ERRORED = "ERRORED"


class SessionMode(str, Enum):
    """Interaction modality."""

    TEXT = "TEXT"
    VOICE = "VOICE"
    VIDEO = "VIDEO"


class SimulationSession(BaseModel):
    """
    A user's run through a scenario.

    Attributes:
        id: Primary key UUID
        tenant_id: Owning tenant
        user_id: The learner
        scenario_id: Which scenario was run
        cohort_id: Optional cohort context (standalone sessions are null)
        status: Runtime status
        mode: Interaction mode
        turn_count: Number of conversational turns
        duration_seconds: Wall-clock duration
        scenario_snapshot: Frozen copy of scenario config at session start
        started_at / ended_at: Timing markers
    """

    __tablename__ = "simulation_sessions"

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
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cohort_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cohorts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus, name="session_status_enum", native_enum=True),
        default=SessionStatus.PENDING,
        nullable=False,
        index=True,
    )
    mode: Mapped[SessionMode] = mapped_column(
        SQLEnum(SessionMode, name="session_mode_enum", native_enum=True),
        default=SessionMode.TEXT,
        nullable=False,
    )
    turn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scenario_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant")
    user: Mapped["User"] = relationship("User")
    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="simulation_sessions")
    cohort: Mapped[Optional["Cohort"]] = relationship("Cohort", back_populates="simulation_sessions")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    evaluation: Mapped[Optional["Evaluation"]] = relationship(
        "Evaluation",
        back_populates="session",
        uselist=False,
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment",
        back_populates="session",
    )

    def __repr__(self) -> str:
        return f"SimulationSession(id={self.id!s}, status={self.status}, mode={self.mode})"
