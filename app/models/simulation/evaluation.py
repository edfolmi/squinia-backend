"""
Evaluation: AI-generated assessment of a completed simulation session.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.auth.tenant import Tenant
    from app.models.simulation.simulation_session import SimulationSession
    from app.models.simulation.evaluation_score import EvaluationScore


class EvalStatus(str, Enum):
    """Processing pipeline status for an evaluation."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Evaluation(BaseModel):
    """
    One-to-one AI evaluation of a simulation session.

    Attributes:
        id: Primary key UUID
        session_id: The session being evaluated (unique)
        tenant_id: Owning tenant
        status: Pipeline status
        overall_score: 0-100 composite score
        feedback_summary: Narrative summary
        strengths / improvements: Bullet-point text blocks
        highlights: JSONB array of notable moments
    """

    __tablename__ = "evaluations"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[EvalStatus] = mapped_column(
        SQLEnum(EvalStatus, name="eval_status_enum", native_enum=True),
        default=EvalStatus.PENDING,
        nullable=False,
        index=True,
    )
    overall_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strengths: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    improvements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    highlights: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    session: Mapped["SimulationSession"] = relationship("SimulationSession", back_populates="evaluation")
    tenant: Mapped["Tenant"] = relationship("Tenant")
    scores: Mapped[list["EvaluationScore"]] = relationship(
        "EvaluationScore",
        back_populates="evaluation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Evaluation(id={self.id!s}, session_id={self.session_id!s}, status={self.status})"
