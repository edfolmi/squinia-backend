"""
Platform user management (authenticated; some routes require platform staff).
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AdminUser, CurrentUser
from app.db.session import get_db
from app.schemas.auth.user import UserList, UserResponse, UserUpdate
from app.services.user import UserService

router = APIRouter()


@router.get("", response_model=UserList)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    staff: AdminUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> UserList:
    """List platform users (platform admin or owner)."""
    user_service = UserService(db)
    return await user_service.list_users(page=page, page_size=page_size)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
) -> UserResponse:
    """Get a user by id (self or platform staff)."""
    if current_user.id != user_id and not current_user.is_platform_staff():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user",
        )
    user_service = UserService(db)
    return await user_service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
) -> UserResponse:
    """Update profile or staff fields (authorization enforced in service)."""
    user_service = UserService(db)
    return await user_service.update_user(user_id, user_in, current_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    staff: AdminUser,
) -> None:
    """Soft-delete a user (platform admin or owner)."""
    user_service = UserService(db)
    await user_service.delete_user(user_id, staff)
