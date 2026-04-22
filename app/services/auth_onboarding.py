"""Persist first-run onboarding (student goals or admin cohort stub)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.auth.membership import OrgRole
from app.models.auth.user import User
from app.models.simulation.cohort import CohortStatus
from app.models.simulation.cohort_member import CohortMemberRole
from app.repositories.auth.membership_repository import MembershipRepository
from app.repositories.auth.user_repository import UserRepository
from app.repositories.simulation.cohort_repository import CohortRepository
from app.schemas.auth.flows import AdminOnboardingRequest, StudentOnboardingRequest
from app.services.workspace_bootstrap import ensure_personal_workspace


class AuthOnboardingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.memberships = MembershipRepository(db)
        self.cohorts = CohortRepository(db)

    async def complete(self, current_user: User, body: StudentOnboardingRequest | AdminOnboardingRequest) -> dict:
        m = await self.memberships.get_default_for_user(current_user.id)
        if not m:
            if isinstance(body, AdminOnboardingRequest):
                m = await ensure_personal_workspace(
                    self.db,
                    user_id=current_user.id,
                    user_email=current_user.email,
                    full_name=current_user.full_name,
                    tenant_display_name=body.cohort_name,
                )
            else:
                m = await ensure_personal_workspace(
                    self.db,
                    user_id=current_user.id,
                    user_email=current_user.email,
                    full_name=current_user.full_name,
                )

        now = datetime.now(timezone.utc)

        if isinstance(body, StudentOnboardingRequest):
            payload = {"role": "student", "goalIds": list(body.goal_ids)}
            await self.users.update(
                current_user.id,
                {
                    "onboarding": payload,
                    "onboarding_completed_at": now,
                },
            )
            return {"onboarding": payload, "completed_at": now.isoformat()}

        if m.role not in (OrgRole.ORG_OWNER, OrgRole.ORG_ADMIN):
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Only organization admins can create the first cohort this way",
            )

        desc_raw = body.cohort_description
        desc = (desc_raw.strip() if desc_raw and desc_raw.strip() else None)

        cohort_data: dict = {
            "tenant_id": m.tenant_id,
            "name": body.cohort_name.strip(),
            "description": desc,
            "status": CohortStatus.DRAFT,
        }
        weeks = body.program_length_weeks
        if weeks is not None:
            start = now
            cohort_data["starts_at"] = start
            cohort_data["ends_at"] = start + timedelta(weeks=int(weeks))

        cohort = await self.cohorts.create(cohort_data)
        await self.cohorts.add_member(cohort.id, current_user.id, CohortMemberRole.INSTRUCTOR)

        payload = {
            "role": "admin",
            "cohortId": str(cohort.id),
            "cohortName": body.cohort_name,
        }
        if body.cohort_description:
            payload["cohortDescription"] = body.cohort_description
        if body.program_length_weeks is not None:
            payload["programLengthWeeks"] = body.program_length_weeks

        await self.users.update(
            current_user.id,
            {
                "onboarding": payload,
                "onboarding_completed_at": now,
            },
        )
        return {"onboarding": payload, "completed_at": now.isoformat()}
