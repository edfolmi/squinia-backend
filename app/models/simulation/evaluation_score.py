"""
EvaluationScore: per-rubric-item score for an evaluation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.simulation.evaluation import Evaluation
    from app.models.simulation.scenario_rubric_item import ScenarioRubricItem


class EvaluationScore(Base):
    """Score awarded for a single rubric item within an evaluation."""

    __tablename__ = "evaluation_scores"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "rubric_item_id", name="uq_eval_scores_eval_rubric"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    evaluation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rubric_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scenario_rubric_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    example_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    improvement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evaluation: Mapped["Evaluation"] = relationship("Evaluation", back_populates="scores")
    rubric_item: Mapped["ScenarioRubricItem"] = relationship("ScenarioRubricItem", back_populates="evaluation_scores")

    def __repr__(self) -> str:
        return f"EvaluationScore(id={self.id!s}, score={self.score})"
