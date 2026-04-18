"""
User service: registration helpers and platform user management.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import security_service
from app.models.auth.user import User, PlatformRole
from app.repositories.auth import UserRepository
from app.schemas.auth.user import UserCreate, UserList, UserUpdate
logger = get_logger(__name__)


class UserService:
    """Business logic for platform users."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    async def create_user(self, user_in: UserCreate) -> User:
        if not user_in.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required for this registration flow",
            )
        if await self.user_repo.email_exists(user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user_data = {
            "email": str(user_in.email),
            "password_hash": security_service.get_password_hash(user_in.password),
            "full_name": user_in.full_name,
        }
        user = await self.user_repo.create(user_data)
        await self.db.commit()

        logger.info("User created", user_id=str(user.id), email=user.email)
        return user

    async def get_user(self, user_id: UUID) -> User:
        user = await self.user_repo.get(user_id)
        if not user or user.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def list_users(self, page: int = 1, page_size: int = 50) -> UserList:
        skip = (page - 1) * page_size
        users = await self.user_repo.get_multi(skip=skip, limit=page_size)
        total = await self.user_repo.count()
        total_pages = math.ceil(total / page_size) if page_size else 0

        return UserList(
            items=users,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def _can_manage_user(self, actor: User, target_id: UUID) -> bool:
        if actor.id == target_id:
            return True
        return actor.platform_role in (PlatformRole.PLATFORM_OWNER, PlatformRole.PLATFORM_ADMIN)

    async def update_user(
        self,
        user_id: UUID,
        user_in: UserUpdate,
        current_user: User,
    ) -> User:
        if not self._can_manage_user(current_user, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this user",
            )

        user = await self.user_repo.get(user_id)
        if not user or user.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        staff = current_user.is_platform_staff()
        update_data: dict = {}

        if user_in.email is not None:
            if user_in.email != user.email:
                if await self.user_repo.email_exists(str(user_in.email), exclude_user_id=user.id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered",
                    )
            update_data["email"] = str(user_in.email)

        if user_in.full_name is not None:
            update_data["full_name"] = user_in.full_name

        if user_in.password is not None:
            update_data["password_hash"] = security_service.get_password_hash(user_in.password)

        if user_in.platform_role is not None:
            if not staff:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to change platform role",
                )
            update_data["platform_role"] = user_in.platform_role

        if user_in.is_active is not None:
            if not staff:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to change account status",
                )
            update_data["is_active"] = user_in.is_active

        if user_in.is_verified is not None:
            if not staff:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to change verification status",
                )
            update_data["is_verified"] = user_in.is_verified

        if not update_data:
            return user

        updated = await self.user_repo.update(user_id, update_data)
        await self.db.commit()

        logger.info("User updated", user_id=str(user_id), updated_by=str(current_user.id))
        return updated or user

    async def delete_user(self, user_id: UUID, current_user: User) -> None:
        """Soft-delete: set deleted_at and deactivate."""
        user = await self.user_repo.get(user_id)
        if not user or user.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await self.user_repo.update(
            user_id,
            {
                "is_active": False,
                "deleted_at": datetime.now(timezone.utc),
            },
        )
        await self.db.commit()

        logger.info("User soft-deleted", user_id=str(user_id), deleted_by=str(current_user.id))
