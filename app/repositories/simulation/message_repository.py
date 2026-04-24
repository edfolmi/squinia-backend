"""Session message persistence."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation.message import Message


class MessageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_session(self, session_id: UUID) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.turn_number.asc(), Message.created_at.asc())
        )
        r = await self.db.execute(stmt)
        return list(r.scalars().all())

    async def get_max_turn(self, session_id: UUID) -> int:
        stmt = select(Message.turn_number).where(Message.session_id == session_id).order_by(Message.turn_number.desc()).limit(1)
        r = await self.db.execute(stmt)
        v = r.scalar_one_or_none()
        return int(v or 0)

    async def create(self, data: dict[str, Any]) -> Message:
        row = Message(**data)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row
