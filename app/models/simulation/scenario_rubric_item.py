"""
ScenarioRubricItem: a single grading criterion attached to a scenario.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.simulation.scenario import Scenario
    from app.models.simulation.evaluation_score import EvaluationScore


class ScenarioRubricItem(Base):
    """One rubric criterion for a scenario."""

    __tablename__ = "scenario_rubric_items"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    scenario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_score: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="rubric_items")
    evaluation_scores: Mapped[list["EvaluationScore"]] = relationship(
        "EvaluationScore",
        back_populates="rubric_item",
    )

    def __repr__(self) -> str:
        return f"ScenarioRubricItem(id={self.id!s}, criterion={self.criterion!r})"
