"""Pydantic schemas for reusable agent personas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.simulation.agent_persona import PersonaGender


class AgentPersonaBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    title: Optional[str] = Field(default=None, max_length=180)
    gender: PersonaGender = PersonaGender.UNSPECIFIED
    avatar_url: Optional[str] = None
    voice_provider: str = Field(default="deepgram", max_length=80)
    voice_id: Optional[str] = Field(default=None, max_length=160)
    personality: Optional[str] = None
    communication_style: Optional[str] = None
    background: Optional[str] = None
    is_default: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class AgentPersonaCreate(AgentPersonaBase):
    pass


class AgentPersonaUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    title: Optional[str] = Field(default=None, max_length=180)
    gender: Optional[PersonaGender] = None
    avatar_url: Optional[str] = None
    voice_provider: Optional[str] = Field(default=None, max_length=80)
    voice_id: Optional[str] = Field(default=None, max_length=160)
    personality: Optional[str] = None
    communication_style: Optional[str] = None
    background: Optional[str] = None
    is_default: Optional[bool] = None
    meta: Optional[dict[str, Any]] = None


class AgentPersonaResponse(AgentPersonaBase):
    id: UUID
    tenant_id: UUID
    created_by: UUID
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
