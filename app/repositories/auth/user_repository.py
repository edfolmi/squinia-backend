"""
User repository: async CRUD and lookups for platform users.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.user import User


class UserRepository:
    """Data access for ``users`` table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_email_lower(self, email: str) -> Optional[User]:
        em = email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == em)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(self, email: str, exclude_user_id: Optional[UUID] = None) -> bool:
        stmt = select(func.count()).select_from(User).where(User.email == email)
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        result = await self.db.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def create(self, data: dict[str, Any]) -> User:
        user = User(**data)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: UUID, data: dict[str, Any]) -> Optional[User]:
        if not data:
            return await self.get(user_id)
        await self.db.execute(update(User).where(User.id == user_id).values(**data))
        await self.db.flush()
        return await self.get(user_id)

    async def get_multi(self, skip: int = 0, limit: int = 50) -> list[User]:
        stmt = (
            select(User)
            .where(User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        stmt = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return int(result.scalar_one() or 0)
