"""Create tenant invites (org admin) and send optional email."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.core.tenant_access import ActiveTenantContext
from app.integrations.email import get_email_provider
from app.models.auth.membership import OrgRole
from app.repositories.auth.tenant_invite_repository import TenantInviteRepository
from app.utils.tokens import new_url_token

logger = get_logger(__name__)

_INVITE_ROLES = (OrgRole.STUDENT, OrgRole.INSTRUCTOR)


class TenantInviteMintService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.invites = TenantInviteRepository(db)

    async def mint(
        self,
        ctx: ActiveTenantContext,
        *,
        email: str,
        role: OrgRole,
        expires_in_days: int,
    ) -> dict:
        if role not in _INVITE_ROLES:
            raise AppError(
                status_code=400,
                code="INVALID_INVITE_ROLE",
                message="Invites may only grant STUDENT or INSTRUCTOR organization roles",
            )

        em = email.strip().lower()
        raw, token_hash = new_url_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        row = await self.invites.create(
            tenant_id=ctx.tenant_id,
            email=em,
            role=role,
            token_hash=token_hash,
            expires_at=expires_at,
            invited_by_user_id=ctx.user.id,
        )

        base = settings.PUBLIC_APP_URL.rstrip("/")
        invite_url = f"{base}/accept-invite?token={raw}"
        subject = f"You have been invited to join an organization on {settings.APP_NAME}"
        text = (
            f"You were invited with role {role.value}.\n\n"
            f"Accept the invite:\n{invite_url}\n\n"
            "If you were not expecting this, you can ignore this email."
        )
        try:
            await get_email_provider().send(to_address=em, subject=subject, text_body=text)
        except Exception:
            logger.exception("invite_email_failed", invite_id=str(row.id), email=em)

        return {
            "invite_id": row.id,
            "email": em,
            "role": role,
            "expires_at": expires_at,
            "token": raw,
            "invite_url": invite_url,
        }
