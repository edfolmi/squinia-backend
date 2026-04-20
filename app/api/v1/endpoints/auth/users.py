"""
Platform user management (authenticated; some routes require platform staff).
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AdminUser, CurrentUser
from app.core.exceptions import AppError
from app.db.session import get_db
from app.schemas.auth.user import UserResponse, UserUpdate
from app.schemas.response import ok, ok_paginated
from app.services.user import UserService

router = APIRouter()


@router.get("")
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    staff: AdminUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
):
    """List platform users (platform admin or owner)."""
    user_service = UserService(db)
    result = await user_service.list_users(page=page, page_size=page_size)
    items = [
        UserResponse.model_validate(u).model_dump(mode="json")
        for u in result["users"]
    ]
    return ok_paginated(
        items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """Get a user by id (self or platform staff)."""
    if current_user.id != user_id and not current_user.is_platform_staff():
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Not authorized to view this user",
        )
    user_service = UserService(db)
    user = await user_service.get_user(user_id)
    return ok({"user": UserResponse.model_validate(user).model_dump(mode="json")})


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """Update profile or staff fields (authorization enforced in service)."""
    user_service = UserService(db)
    user = await user_service.update_user(user_id, user_in, current_user)
    return ok({"user": UserResponse.model_validate(user).model_dump(mode="json")})


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    staff: AdminUser,
):
    """Soft-delete a user (platform admin or owner)."""
    user_service = UserService(db)
    await user_service.delete_user(user_id, staff)
    return ok({"message": "User deleted successfully"})
