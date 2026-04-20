"""
Tenant-scoped request context: validates JWT ``tenant_id`` against active membership.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Callable, Iterable
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import security_service
from app.db.session import get_db
from app.models.auth.membership import Membership, OrgRole
from app.models.auth.user import User
from app.core.dependencies import get_current_active_user

security = HTTPBearer()


@dataclass
class ActiveTenantContext:
    """Authenticated user plus verified membership in the JWT tenant."""

    user: User
    membership: Membership
    tenant_id: UUID

    @property
    def org_role(self) -> OrgRole:
        return self.membership.role


async def get_active_tenant_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ActiveTenantContext:
    """
    Resolve ``tenant_id`` from the access token and verify an active membership row.

    Org role for authorization must come from ``context.membership.role``, not from JWT alone.
    """
    payload = security_service.decode_token(credentials.credentials)
    if not payload:
        raise AppError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raw_tid = payload.get("tenant_id")
    if not raw_tid:
        raise AppError(
            status_code=403,
            code="NO_TENANT_CONTEXT",
            message="No tenant context in token; user must belong to an organization",
        )
    try:
        tenant_id = UUID(str(raw_tid))
    except ValueError:
        raise AppError(status_code=403, code="TENANT_MISMATCH", message="Invalid tenant in token")

    from app.repositories.auth import MembershipRepository

    repo = MembershipRepository(db)
    membership = await repo.get_active(current_user.id, tenant_id)
    if not membership:
        raise AppError(status_code=403, code="TENANT_MISMATCH", message="Not a member of this tenant")

    return ActiveTenantContext(user=current_user, membership=membership, tenant_id=tenant_id)


TenantMember = Annotated[ActiveTenantContext, Depends(get_active_tenant_context)]


def require_org_roles(*allowed: OrgRole) -> Callable:
    """Dependency factory: membership org role must be one of ``allowed``."""

    allowed_set: Iterable[OrgRole] = allowed

    async def _check(ctx: TenantMember) -> ActiveTenantContext:
        if ctx.org_role not in allowed_set:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Insufficient organization privileges for this action",
            )
        return ctx

    return _check


def block_students() -> Callable:
    """Reject organization members whose role is ``STUDENT`` (cohort admin routes)."""

    async def _check(ctx: TenantMember) -> ActiveTenantContext:
        if ctx.org_role == OrgRole.STUDENT:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Students cannot access this resource",
            )
        return ctx

    return _check


CohortStaff = Annotated[
    ActiveTenantContext,
    Depends(require_org_roles(OrgRole.ORG_OWNER, OrgRole.ORG_ADMIN, OrgRole.INSTRUCTOR)),
]
CohortWriter = Annotated[
    ActiveTenantContext,
    Depends(require_org_roles(OrgRole.ORG_OWNER, OrgRole.ORG_ADMIN)),
]
ScenarioWriter = Annotated[
    ActiveTenantContext,
    Depends(require_org_roles(OrgRole.ORG_OWNER, OrgRole.ORG_ADMIN, OrgRole.INSTRUCTOR)),
]


async def get_cohort_reader(ctx: TenantMember) -> ActiveTenantContext:
    """Instructor+ can read cohort APIs; students are blocked entirely."""
    if ctx.org_role == OrgRole.STUDENT:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Students cannot access cohort endpoints",
        )
    if ctx.org_role not in (OrgRole.INSTRUCTOR, OrgRole.ORG_ADMIN, OrgRole.ORG_OWNER):
        raise AppError(status_code=403, code="FORBIDDEN", message="Insufficient organization privileges")
    return ctx


async def get_cohort_writer(ctx: TenantMember) -> ActiveTenantContext:
    if ctx.org_role not in (OrgRole.ORG_ADMIN, OrgRole.ORG_OWNER):
        raise AppError(status_code=403, code="FORBIDDEN", message="Only org admins can modify cohorts")
    return ctx


CohortReader = Annotated[ActiveTenantContext, Depends(get_cohort_reader)]
CohortWriter = Annotated[ActiveTenantContext, Depends(get_cohort_writer)]
