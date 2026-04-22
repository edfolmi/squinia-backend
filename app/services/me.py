"""Assemble ``GET /auth/me`` payload for dashboard shell routing."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.membership import Membership, OrgRole
from app.models.auth.user import User
from app.repositories.auth.membership_repository import MembershipRepository
from app.schemas.auth.me import MeMembershipItem, MeResponse
from app.schemas.auth.user import UserResponse


def build_me_response(user: User, memberships: list[Membership]) -> MeResponse:
    items: list[MeMembershipItem] = []
    for m in memberships:
        t = m.tenant
        if t is None or t.deleted_at is not None:
            continue
        items.append(
            MeMembershipItem(
                tenant_id=m.tenant_id,
                tenant_name=t.name,
                tenant_slug=t.slug,
                org_role=m.role,
                joined_at=m.joined_at,
            ),
        )

    default_tid: Optional[UUID] = None
    default_role: Optional[OrgRole] = None
    if items:
        default_tid = items[0].tenant_id
        default_role = items[0].org_role

    base_user: dict[str, Any] = UserResponse.model_validate(user).model_dump(mode="json")
    base_user["onboarding"] = user.onboarding if isinstance(user.onboarding, dict) else {}
    base_user["onboarding_completed_at"] = (
        user.onboarding_completed_at.isoformat() if user.onboarding_completed_at else None
    )

    return MeResponse(
        user=base_user,
        memberships=items,
        default_tenant_id=default_tid,
        default_org_role=default_role,
    )


class MeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.memberships = MembershipRepository(db)

    async def get_me(self, user: User) -> MeResponse:
        rows = await self.memberships.list_active_with_tenant(user.id)
        return build_me_response(user, rows)
