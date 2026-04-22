"""Request bodies for public auth flows (verify, reset, invite, onboarding)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from app.schemas.auth.password_policy import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=512)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Frontend sends ``password`` (not ``new_password``)."""

    token: str = Field(..., min_length=1, max_length=512)
    password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )


class AcceptInviteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    token: str = Field(..., min_length=1, max_length=512)
    password: Optional[str] = Field(
        None,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    full_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        validation_alias=AliasChoices("full_name", "fullName"),
    )


class StudentOnboardingRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    role: Literal["student"] = "student"
    goal_ids: list[str] = Field(..., min_length=1, alias="goalIds")


class AdminOnboardingRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    role: Literal["admin"] = "admin"
    cohort_name: str = Field(..., min_length=1, max_length=255, alias="cohortName")
    cohort_description: Optional[str] = Field(
        None,
        max_length=4000,
        alias="cohortDescription",
    )
    program_length_weeks: Optional[int] = Field(
        None,
        ge=1,
        le=520,
        alias="programLengthWeeks",
    )
