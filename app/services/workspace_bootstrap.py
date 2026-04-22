"""Create a personal / first workspace tenant + org-owner membership when missing."""
from __future__ import annotations

import re
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.membership import OrgRole
from app.models.auth.tenant import Plan, Tenant
from app.repositories.auth.membership_repository import MembershipRepository


def _slug_candidate(seed: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", seed.lower())[:48].strip("-") or "workspace"
    return f"{base}-{uuid4().hex[:12]}"


async def _unique_tenant_slug(db: AsyncSession, seed: str) -> str:
    for _ in range(12):
        slug = _slug_candidate(seed)[:255]
        r = await db.execute(select(Tenant.id).where(Tenant.slug == slug, Tenant.deleted_at.is_(None)))
        if r.scalar_one_or_none() is None:
            return slug
    return f"w-{uuid4().hex}"[:255]


async def ensure_personal_workspace(
    db: AsyncSession,
    *,
    user_id: UUID,
    user_email: str,
    full_name: str,
    tenant_display_name: str | None = None,
):
    """
    If the user has no active membership, create a starter tenant and ORG_OWNER row.

    ``tenant_display_name`` defaults to ``\"{full_name}'s workspace\"`` when omitted.
    """
    memberships = MembershipRepository(db)
    existing = await memberships.get_default_for_user(user_id)
    if existing:
        return existing

    name = (
        tenant_display_name.strip()
        if tenant_display_name and tenant_display_name.strip()
        else f"{full_name.strip()}'s workspace"
    )
    if len(name) > 255:
        name = name[:255]

    slug_seed = user_email.split("@")[0] if tenant_display_name is None else name
    slug = await _unique_tenant_slug(db, slug_seed)

    tenant = Tenant(
        name=name,
        slug=slug,
        plan=Plan.starter,
        is_active=True,
        max_seats=50,
        billing_email=user_email,
    )
    db.add(tenant)
    await db.flush()

    m = await memberships.create(
        user_id=user_id,
        tenant_id=tenant.id,
        role=OrgRole.ORG_OWNER,
    )
    return m
