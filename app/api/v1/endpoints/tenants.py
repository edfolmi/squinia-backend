"""Tenant read models for authenticated members."""
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.core.exceptions import AppError
from app.db.session import get_db
from app.repositories.auth.membership_repository import MembershipRepository
from app.repositories.auth.tenant_repository import TenantRepository
from app.schemas.auth.tenant_public import TenantPublicResponse
from app.schemas.response import ok


async def get_tenant_for_member(
    tenant_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Return basic tenant fields if the current user has an active membership in this tenant.

    Registered on the v1 router as ``GET /tenants/{tenant_id}`` only (see ``router.py``) so a
    sub-router can never accidentally mount ``GET /{tenant_id}`` at the API root and shadow
    ``/cohorts``, ``/sessions``, etc.
    """
    mrepo = MembershipRepository(db)
    if not await mrepo.get_active(current_user.id, tenant_id):
        raise AppError(status_code=404, code="NOT_FOUND", message="Tenant not found or access denied")
    trepo = TenantRepository(db)
    tenant = await trepo.get_active(tenant_id)
    if not tenant:
        raise AppError(status_code=404, code="NOT_FOUND", message="Tenant not found")
    return ok(TenantPublicResponse.model_validate(tenant).model_dump(mode="json"))
