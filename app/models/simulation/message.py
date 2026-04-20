"""
Message: a single conversational turn inside a simulation session.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.simulation.simulation_session import SimulationSession


class MessageRole(str, Enum):
    """Who produced the message."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class Message(Base):
    """Single message in a simulation conversation."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("session_id", "turn_number", name="uq_messages_session_turn"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole, name="message_role_enum", native_enum=True),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["SimulationSession"] = relationship("SimulationSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"Message(id={self.id!s}, role={self.role}, turn={self.turn_number})"
