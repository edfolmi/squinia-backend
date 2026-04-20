"""
AssignmentSubmission: a user's response to an assignment.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auth.user import User
    from app.models.simulation.assignment import Assignment


class AssignmentSubmission(Base):
    """One submission per user per assignment."""

    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "user_id", name="uq_assignment_submissions_assign_user"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    assignment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    files: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    assignment: Mapped["Assignment"] = relationship("Assignment", back_populates="submissions")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"AssignmentSubmission(id={self.id!s}, assignment_id={self.assignment_id!s})"
