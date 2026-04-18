"""
User model: platform identity, authentication, and platform-wide role.
Organization roles live on Membership.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.auth.membership import Membership
    from app.models.auth.auth_session import AuthSession
    from app.models.auth.password_reset import PasswordReset
    from app.models.auth.email_verification import EmailVerification


class PlatformRole(str, Enum):
    """Platform-wide role (platform_role_enum)."""

    PLATFORM_OWNER = "PLATFORM_OWNER"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    USER = "USER"


class User(BaseModel):
    """
    Global user account (not tenant-scoped).

    Attributes:
        id: Primary key UUID
        email: Unique login email
        password_hash: Nullable for SSO-only accounts
        full_name: Display name
        platform_role: Staff / owner capabilities at platform level
        is_active: Account enabled
        is_verified: Email (or equivalent) verified
        last_login_at: Last successful authentication
        deleted_at: Soft-delete timestamp
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform_role: Mapped[PlatformRole] = mapped_column(
        SQLEnum(PlatformRole, name="platform_role_enum", native_enum=True),
        default=PlatformRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    memberships: Mapped[list["Membership"]] = relationship(
        "Membership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_resets: Mapped[list["PasswordReset"]] = relationship(
        "PasswordReset",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    email_verifications: Mapped[list["EmailVerification"]] = relationship(
        "EmailVerification",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def is_platform_staff(self) -> bool:
        """True if the user can perform platform administration tasks."""
        return self.platform_role in (PlatformRole.PLATFORM_OWNER, PlatformRole.PLATFORM_ADMIN)

    def __repr__(self) -> str:
        return f"User(id={self.id!s}, email={self.email!r}, platform_role={self.platform_role})"
