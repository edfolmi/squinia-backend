"""Analytics read models (Postgres-backed aggregates; ClickHouse later)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.auth.membership import OrgRole
from app.models.auth.tenant import Tenant
from app.models.auth.user import PlatformRole
from app.models.simulation.evaluation import EvalStatus, Evaluation
from app.models.simulation.simulation_session import SessionStatus, SimulationSession
from app.repositories.simulation import CohortRepository, ScenarioRepository, SessionRepository


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cohorts = CohortRepository(db)
        self.sessions = SessionRepository(db)
        self.scenarios = ScenarioRepository(db)

    async def cohort_overview(self, tenant_id: UUID, cohort_id: UUID) -> dict:
        cohort = await self.cohorts.get(cohort_id, tenant_id)
        if not cohort:
            raise AppError(status_code=404, code="NOT_FOUND", message="Cohort not found")
        members = await self.cohorts.count_members(cohort_id)
        stmt_avg = (
            select(func.avg(Evaluation.overall_score))
            .select_from(Evaluation)
            .join(SimulationSession, SimulationSession.id == Evaluation.session_id)
            .where(
                SimulationSession.cohort_id == cohort_id,
                Evaluation.status == EvalStatus.COMPLETED,
            )
        )
        avg = (await self.db.execute(stmt_avg)).scalar_one_or_none()
        stmt_done = select(func.count()).select_from(SimulationSession).where(
            SimulationSession.cohort_id == cohort_id,
            SimulationSession.status == SessionStatus.COMPLETED,
        )
        done = int((await self.db.execute(stmt_done)).scalar_one() or 0)
        stmt_total = select(func.count()).select_from(SimulationSession).where(
            SimulationSession.cohort_id == cohort_id,
        )
        total = int((await self.db.execute(stmt_total)).scalar_one() or 0)
        completion = float(done) / float(total) if total else 0.0
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        stmt_week = select(func.count()).select_from(SimulationSession).where(
            SimulationSession.cohort_id == cohort_id,
            SimulationSession.started_at.is_not(None),
            SimulationSession.started_at >= week_ago,
        )
        week_count = int((await self.db.execute(stmt_week)).scalar_one() or 0)
        return {
            "overview": {
                "total_members": members,
                "avg_score": float(avg) if avg is not None else None,
                "completion_rate": completion,
                "sessions_this_week": week_count,
                "top_skill_gaps": [],
            },
        }

    async def cohort_skill_map(self, tenant_id: UUID, cohort_id: UUID) -> dict:
        cohort = await self.cohorts.get(cohort_id, tenant_id)
        if not cohort:
            raise AppError(status_code=404, code="NOT_FOUND", message="Cohort not found")
        return {"criteria": [], "members": []}

    async def cohort_progress_over_time(
        self,
        tenant_id: UUID,
        cohort_id: UUID,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> dict:
        cohort = await self.cohorts.get(cohort_id, tenant_id)
        if not cohort:
            raise AppError(status_code=404, code="NOT_FOUND", message="Cohort not found")
        return {"dates": [], "series": []}

    async def user_summary(self, tenant_id: UUID, target_user_id: UUID, viewer_id: UUID, org_role: OrgRole) -> dict:
        if org_role == OrgRole.STUDENT and target_user_id != viewer_id:
            raise AppError(status_code=403, code="FORBIDDEN", message="Cannot view another user's analytics")
        stmt_total = select(func.count()).select_from(SimulationSession).where(
            SimulationSession.tenant_id == tenant_id,
            SimulationSession.user_id == target_user_id,
        )
        total = int((await self.db.execute(stmt_total)).scalar_one() or 0)
        stmt_avg = (
            select(func.avg(Evaluation.overall_score))
            .select_from(Evaluation)
            .join(SimulationSession, SimulationSession.id == Evaluation.session_id)
            .where(
                SimulationSession.tenant_id == tenant_id,
                SimulationSession.user_id == target_user_id,
                Evaluation.status == EvalStatus.COMPLETED,
            )
        )
        avg = (await self.db.execute(stmt_avg)).scalar_one_or_none()
        return {
            "summary": {
                "total_sessions": total,
                "avg_score": float(avg) if avg is not None else None,
                "trend": "stable",
                "weakest_criteria": [],
                "strongest_criteria": [],
            },
        }

    async def scenario_stats(self, tenant_id: UUID, scenario_id: UUID) -> dict:
        scenario = await self.scenarios.get(scenario_id, tenant_id)
        if not scenario:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        stmt_attempts = select(func.count()).select_from(SimulationSession).where(
            SimulationSession.tenant_id == tenant_id,
            SimulationSession.scenario_id == scenario_id,
        )
        attempts = int((await self.db.execute(stmt_attempts)).scalar_one() or 0)
        stmt_avg = (
            select(func.avg(Evaluation.overall_score))
            .select_from(Evaluation)
            .join(SimulationSession, SimulationSession.id == Evaluation.session_id)
            .where(
                SimulationSession.tenant_id == tenant_id,
                SimulationSession.scenario_id == scenario_id,
                Evaluation.status == EvalStatus.COMPLETED,
            )
        )
        avg = (await self.db.execute(stmt_avg)).scalar_one_or_none()
        return {
            "stats": {
                "total_attempts": attempts,
                "avg_score": float(avg) if avg is not None else None,
                "pass_rate": None,
                "avg_duration_seconds": None,
                "score_distribution": {},
            },
        }

    async def tenants_overview(self, platform_role: PlatformRole) -> dict:
        if platform_role not in (PlatformRole.PLATFORM_ADMIN, PlatformRole.PLATFORM_OWNER):
            raise AppError(status_code=403, code="FORBIDDEN", message="Platform admin access required")
        tenants = int((await self.db.execute(select(func.count()).select_from(Tenant))).scalar_one() or 0)
        now = datetime.now(timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        stmt_sessions = select(func.count()).select_from(SimulationSession).where(
            SimulationSession.created_at >= day_start,
        )
        sessions_today = int((await self.db.execute(stmt_sessions)).scalar_one() or 0)
        return {
            "overview": {
                "total_tenants": tenants,
                "total_sessions_today": sessions_today,
                "active_users_30d": 0,
            },
        }
