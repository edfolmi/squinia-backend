from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.exceptions import AppError
from app.core.security import security_service
from app.models.auth.membership import OrgRole
from app.models.auth.user import PlatformRole, User
from app.services.auth import AuthService
from app.services.me import build_me_response


def make_user(*, password: str = "Password123!", active: bool = True) -> User:
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid4(),
        email="learner@example.com",
        password_hash=security_service.get_password_hash(password),
        full_name="Learner Example",
        platform_role=PlatformRole.USER,
        is_active=active,
        is_verified=True,
        onboarding={},
        created_at=now,
        updated_at=now,
    )
    return user


@dataclass
class FakeTenant:
    id: object
    name: str = "Squinia Bootcamp"
    slug: str = "squinia-bootcamp"
    deleted_at: object = None


@dataclass
class FakeMembership:
    user_id: object
    tenant_id: object
    role: OrgRole = OrgRole.STUDENT
    tenant: FakeTenant | None = None
    joined_at: datetime = datetime.now(timezone.utc)


class FakeUserRepo:
    def __init__(self, user: User | None) -> None:
        self.user = user

    async def get_by_email(self, email: str) -> User | None:
        if self.user and email == self.user.email:
            return self.user
        return None

    async def get_by_email_lower(self, email: str) -> User | None:
        if self.user and email.strip().lower() == self.user.email.lower():
            return self.user
        return None

    async def get(self, user_id) -> User | None:
        if self.user and user_id == self.user.id:
            return self.user
        return None


class FakeMembershipRepo:
    def __init__(self, membership: FakeMembership | None) -> None:
        self.membership = membership

    async def get_default_for_user(self, user_id):
        if self.membership and self.membership.user_id == user_id:
            return self.membership
        return None


def auth_service_for(user: User | None, membership: FakeMembership | None = None) -> AuthService:
    svc = AuthService(db=None)  # type: ignore[arg-type]
    svc.user_repo = FakeUserRepo(user)  # type: ignore[assignment]
    svc.membership_repo = FakeMembershipRepo(membership)  # type: ignore[assignment]
    return svc


@pytest.mark.asyncio
async def test_login_returns_access_and_refresh_tokens_with_tenant_claims() -> None:
    user = make_user()
    tenant_id = uuid4()
    membership = FakeMembership(user_id=user.id, tenant_id=tenant_id)
    svc = auth_service_for(user, membership)

    result = await svc.login("  LEARNER@EXAMPLE.COM  ", "Password123!")

    access_payload = security_service.decode_token(result["tokens"].access_token)
    refresh_payload = security_service.decode_token(result["tokens"].refresh_token)
    assert result["user"] is user
    assert access_payload is not None
    assert access_payload["sub"] == str(user.id)
    assert access_payload["type"] == "access"
    assert access_payload["tenant_id"] == str(tenant_id)
    assert access_payload["org_role"] == OrgRole.STUDENT.value
    assert refresh_payload is not None
    assert refresh_payload["type"] == "refresh"


@pytest.mark.asyncio
async def test_login_rejects_bad_password_quickly() -> None:
    user = make_user()
    svc = auth_service_for(user)

    with pytest.raises(AppError) as exc:
        await svc.login(user.email, "wrong-password")

    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_expired_or_invalid_access_token_cannot_resolve_current_user() -> None:
    svc = auth_service_for(make_user())

    with pytest.raises(AppError) as exc:
        await svc.get_current_user("not-a-jwt")

    assert exc.value.status_code == 401
    assert exc.value.code == "UNAUTHORIZED"


def test_me_response_includes_membership_for_post_login_routing() -> None:
    user = make_user()
    tenant_id = uuid4()
    membership = FakeMembership(
        user_id=user.id,
        tenant_id=tenant_id,
        tenant=FakeTenant(id=tenant_id),
        role=OrgRole.ORG_ADMIN,
    )

    me = build_me_response(user, [membership])  # type: ignore[list-item]

    assert me.default_tenant_id == tenant_id
    assert me.default_org_role == OrgRole.ORG_ADMIN
    assert me.memberships[0].tenant_name == "Squinia Bootcamp"
