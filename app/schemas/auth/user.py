"""
Pydantic v2 schemas for User model.
Provides request/response validation and serialization.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.auth.user import PlatformRole


class UserBase(BaseModel):
    """Base User schema with common fields."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for user registration."""

    password: Optional[str] = Field(None, min_length=8, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "password": "strongpassword123",
            }
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    platform_role: Optional[PlatformRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "newemail@example.com",
                "full_name": "John Updated Doe",
            }
        }
    )


class UserResponse(UserBase):
    """Schema for user response (public data)."""

    id: UUID
    platform_role: PlatformRole
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "platform_role": "USER",
                "is_active": True,
                "is_verified": True,
                "last_login_at": "2026-01-01T12:00:00Z",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        },
    )


class UserInDB(UserResponse):
    """Schema for user in database (includes sensitive fields)."""

    password_hash: Optional[str] = None
    deleted_at: Optional[datetime] = None


class UserList(BaseModel):
    """Schema for paginated user list."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
