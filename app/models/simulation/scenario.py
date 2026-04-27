"""
Scenario: an AI-agent persona configuration for simulation sessions.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.auth.tenant import Tenant
    from app.models.auth.user import User
    from app.models.simulation.agent_persona import AgentPersona
    from app.models.simulation.scenario_rubric_item import ScenarioRubricItem
    from app.models.simulation.simulation_session import SimulationSession


class AgentRole(str, Enum):
    """Pre-defined AI agent persona type."""

    TECHNICAL_INTERVIEWER = "TECHNICAL_INTERVIEWER"
    HR_RECRUITER = "HR_RECRUITER"
    PRODUCT_MANAGER = "PRODUCT_MANAGER"
    PEER_DEVELOPER = "PEER_DEVELOPER"
    CLIENT_STAKEHOLDER = "CLIENT_STAKEHOLDER"


class ScenarioDifficulty(str, Enum):
    """Difficulty tier for a scenario."""

    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class ScenarioStatus(str, Enum):
    """Publishing lifecycle of a scenario."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Scenario(BaseModel):
    """
    Simulation scenario template.

    Attributes:
        id: Primary key UUID
        tenant_id: Owning tenant
        created_by: Author (user)
        title: Short name
        description: Long-form explanation
        agent_role: AI persona type
        difficulty: Difficulty tier
        status: Publishing status
        config: JSONB with system_prompt, persona_traits, opening_message, etc.
        estimated_minutes: Expected duration
        is_template: Whether this is a reusable template
        deleted_at: Soft-delete timestamp
    """

    __tablename__ = "scenarios"

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
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    persona_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_personas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_role: Mapped[AgentRole] = mapped_column(
        SQLEnum(AgentRole, name="agent_role_enum", native_enum=True),
        nullable=False,
        index=True,
    )
    difficulty: Mapped[ScenarioDifficulty] = mapped_column(
        SQLEnum(ScenarioDifficulty, name="scenario_difficulty_enum", native_enum=True),
        default=ScenarioDifficulty.INTERMEDIATE,
        nullable=False,
    )
    status: Mapped[ScenarioStatus] = mapped_column(
        SQLEnum(ScenarioStatus, name="scenario_status_enum", native_enum=True),
        default=ScenarioStatus.DRAFT,
        nullable=False,
        index=True,
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant")
    author: Mapped["User"] = relationship("User")
    persona: Mapped[Optional["AgentPersona"]] = relationship("AgentPersona", back_populates="scenarios")
    rubric_items: Mapped[list["ScenarioRubricItem"]] = relationship(
        "ScenarioRubricItem",
        back_populates="scenario",
        cascade="all, delete-orphan",
    )
    simulation_sessions: Mapped[list["SimulationSession"]] = relationship(
        "SimulationSession",
        back_populates="scenario",
    )

    def __repr__(self) -> str:
        return f"Scenario(id={self.id!s}, title={self.title!r}, status={self.status})"
