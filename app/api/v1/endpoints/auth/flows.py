"""
Public auth flows: email verification, password reset, invites, onboarding.
"""
from typing import Annotated, Union

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, OptionalUser
from app.db.session import get_db
from app.schemas.auth.auth import Token
from app.schemas.auth.flows import (
    AcceptInviteRequest,
    AdminOnboardingRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    StudentOnboardingRequest,
    VerifyEmailRequest,
)
from app.schemas.auth.user import UserResponse
from app.schemas.response import ok
from app.services.auth import AuthService
from app.services.auth_invite import AuthInviteService
from app.services.auth_onboarding import AuthOnboardingService
from app.services.auth_password_recovery import AuthPasswordRecoveryService
from app.services.auth_verification import AuthVerificationService

router = APIRouter()


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AuthVerificationService(db)
    user = await svc.verify_email_token(body.token)
    return ok(
        {
            "verified": True,
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
        },
    )


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await AuthPasswordRecoveryService(db).forgot_password(str(body.email))
    return ok({"sent": True})


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await AuthPasswordRecoveryService(db).reset_password(body.token, body.password)
    return ok({"ok": True})


@router.post("/accept-invite")
async def accept_invite(
    body: AcceptInviteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    optional_user: OptionalUser,
):
    svc = AuthInviteService(db)
    bundle = await svc.accept_invite(
        body.token,
        password=body.password,
        full_name=body.full_name,
        optional_user=optional_user,
    )
    tokens: Token = bundle["tokens"]
    return ok(
        {
            "user": UserResponse.model_validate(bundle["user"]).model_dump(mode="json"),
            "tokens": tokens.model_dump(mode="json"),
        },
    )


@router.post("/onboarding", status_code=status.HTTP_200_OK)
async def complete_onboarding(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    body: Annotated[
        Union[StudentOnboardingRequest, AdminOnboardingRequest],
        Body(discriminator="role"),
    ],
):
    data = await AuthOnboardingService(db).complete(current_user, body)
    bundle = await AuthService(db).build_login_bundle(current_user)
    data["tokens"] = bundle["tokens"].model_dump(mode="json")
    return ok(data)
