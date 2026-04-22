"""Org-admin: mint tenant membership invites (JWT tenant context)."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_access import ActiveTenantContext, require_org_roles
from app.db.session import get_db
from app.models.auth.membership import OrgRole
from app.schemas.auth.tenant_invite_create import CreateTenantInviteRequest, CreateTenantInviteResponse
from app.schemas.response import ok
from app.services.tenant_invite_mint import TenantInviteMintService

router = APIRouter()

InviteMintContext = Annotated[
    ActiveTenantContext,
    Depends(require_org_roles(OrgRole.ORG_OWNER, OrgRole.ORG_ADMIN)),
]


@router.post(
    "/invites",
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant invite",
    description="Requires Bearer token with `tenant_id` claim. Caller must be ORG_OWNER or ORG_ADMIN in that tenant.",
)
async def create_tenant_invite(
    body: CreateTenantInviteRequest,
    ctx: InviteMintContext,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    data = await TenantInviteMintService(db).mint(
        ctx,
        email=str(body.email),
        role=body.role,
        expires_in_days=body.expires_in_days,
    )
    return ok(CreateTenantInviteResponse.model_validate(data).model_dump(mode="json"))
