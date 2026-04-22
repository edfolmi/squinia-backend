"""Accept tenant invite: new account, existing password, or authenticated join."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import security_service
from app.models.auth.membership import Membership, OrgRole
from app.models.auth.user import PlatformRole, User
from app.repositories.auth.membership_repository import MembershipRepository
from app.repositories.auth.tenant_invite_repository import TenantInviteRepository
from app.repositories.auth.user_repository import UserRepository
from app.services.auth import AuthService
from app.utils.tokens import hash_url_token


class AuthInviteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.invites = TenantInviteRepository(db)
        self.users = UserRepository(db)
        self.memberships = MembershipRepository(db)
        self.auth = AuthService(db)

    async def _ensure_membership(self, user_id: UUID, tenant_id: UUID, role: OrgRole) -> None:
        existing = await self.memberships.get_any_for_user_tenant(user_id, tenant_id)
        if existing:
            if existing.deleted_at is not None or not existing.is_active:
                await self.memberships.reactivate(existing.id)
            return
        await self.memberships.create(user_id=user_id, tenant_id=tenant_id, role=role)

    async def accept_invite(
        self,
        raw_token: str,
        *,
        password: Optional[str],
        full_name: Optional[str],
        optional_user: Optional[User],
    ) -> dict:
        th = hash_url_token(raw_token)
        invite = await self.invites.get_open_by_token_hash(th)
        if not invite:
            raise AppError(
                status_code=400,
                code="INVALID_TOKEN",
                message="Invalid or unknown invite token",
            )
        now = datetime.now(timezone.utc)
        if invite.expires_at <= now:
            raise AppError(
                status_code=400,
                code="TOKEN_EXPIRED",
                message="Invite link has expired",
            )

        target_email = invite.email.strip().lower()

        if password:
            user = await self.users.get_by_email_lower(target_email)
            if not user:
                display = full_name.strip() if full_name and full_name.strip() else target_email.split("@")[0]
                user = await self.users.create(
                    {
                        "email": target_email,
                        "full_name": display,
                        "password_hash": security_service.get_password_hash(password),
                        "platform_role": PlatformRole.USER,
                        "is_verified": True,
                    },
                )
            else:
                if user.deleted_at is not None:
                    raise AppError(
                        status_code=403,
                        code="USER_DELETED",
                        message="User account is no longer available",
                    )
                updates: dict = {"password_hash": security_service.get_password_hash(password)}
                if full_name and full_name.strip():
                    updates["full_name"] = full_name.strip()
                await self.users.update(user.id, updates)
                user = await self.users.get(user.id) or user
        else:
            if optional_user is None:
                raise AppError(
                    status_code=401,
                    code="NEED_AUTH_OR_PASSWORD",
                    message="Sign in or provide a password to accept this invite",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if optional_user.email.strip().lower() != target_email:
                raise AppError(
                    status_code=403,
                    code="EMAIL_MISMATCH",
                    message="Signed-in user does not match the invited email",
                )
            user = optional_user
            if full_name and full_name.strip():
                await self.users.update(user.id, {"full_name": full_name.strip()})
                user = await self.users.get(user.id) or user

        await self._ensure_membership(user.id, invite.tenant_id, invite.role)
        await self.invites.mark_used(invite.id, used_at=now)
        return await self.auth.build_login_bundle(user)
