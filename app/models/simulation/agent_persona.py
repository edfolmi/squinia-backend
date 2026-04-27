"""Reusable AI agent personas owned by a tenant."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.auth.tenant import Tenant
    from app.models.auth.user import User
    from app.models.simulation.scenario import Scenario


class PersonaGender(str, Enum):
    """Persona voice/presentation hint."""

    FEMALE = "FEMALE"
    MALE = "MALE"
    NON_BINARY = "NON_BINARY"
    UNSPECIFIED = "UNSPECIFIED"


class AgentPersona(BaseModel):
    """Reusable character identity for simulations."""

    __tablename__ = "agent_personas"

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
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(180), nullable=True)
    gender: Mapped[PersonaGender] = mapped_column(
        SQLEnum(PersonaGender, name="persona_gender_enum", native_enum=True),
        default=PersonaGender.UNSPECIFIED,
        nullable=False,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voice_provider: Mapped[str] = mapped_column(String(80), default="deepgram", nullable=False)
    voice_id: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    communication_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    background: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant")
    author: Mapped["User"] = relationship("User")
    scenarios: Mapped[list["Scenario"]] = relationship("Scenario", back_populates="persona")

    def __repr__(self) -> str:
        return f"AgentPersona(id={self.id!s}, name={self.name!r})"
