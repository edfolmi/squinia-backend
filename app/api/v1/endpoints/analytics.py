"""Analytics read API (Postgres aggregates; ClickHouse later)."""
from typing import Annotated
from uuid import UUID

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.core.tenant_access import CohortReader, TenantMember
from app.db.session import get_db
from app.schemas.response import ok
from app.schemas.simulation.responses import (
    AnalyticsCohortOverview,
    AnalyticsProgressOverTime,
    AnalyticsScenarioStats,
    AnalyticsSkillMap,
    AnalyticsTenantOverview,
    AnalyticsUserSummary,
)
from app.services.simulation.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/cohorts/{cohort_id}/overview")
async def cohort_overview(
    cohort_id: UUID,
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AnalyticsService(db)
    result = await svc.cohort_overview(ctx.tenant_id, cohort_id)
    payload = AnalyticsCohortOverview.model_validate(result["overview"]).model_dump(mode="json")
    return ok({"overview": payload})


@router.get("/cohorts/{cohort_id}/skill-map")
async def cohort_skill_map(
    cohort_id: UUID,
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AnalyticsService(db)
    result = await svc.cohort_skill_map(ctx.tenant_id, cohort_id)
    payload = AnalyticsSkillMap.model_validate(result).model_dump(mode="json")
    return ok({"skill_map": payload})


@router.get("/cohorts/{cohort_id}/progress-over-time")
async def cohort_progress_over_time(
    cohort_id: UUID,
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    svc = AnalyticsService(db)
    result = await svc.cohort_progress_over_time(ctx.tenant_id, cohort_id, date_from, date_to)
    payload = AnalyticsProgressOverTime.model_validate(result).model_dump(mode="json")
    return ok({"progress": payload})


@router.get("/users/{user_id}/summary")
async def user_summary(
    user_id: UUID,
    ctx: TenantMember,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AnalyticsService(db)
    result = await svc.user_summary(ctx.tenant_id, user_id, ctx.user.id, ctx.org_role)
    payload = AnalyticsUserSummary.model_validate(result["summary"]).model_dump(mode="json")
    return ok({"summary": payload})


@router.get("/scenarios/{scenario_id}/stats")
async def scenario_stats(
    scenario_id: UUID,
    ctx: CohortReader,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AnalyticsService(db)
    result = await svc.scenario_stats(ctx.tenant_id, scenario_id)
    payload = AnalyticsScenarioStats.model_validate(result["stats"]).model_dump(mode="json")
    return ok({"stats": payload})


@router.get("/tenants/overview")
async def tenants_overview(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AnalyticsService(db)
    result = await svc.tenants_overview(current_user.platform_role)
    payload = AnalyticsTenantOverview.model_validate(result["overview"]).model_dump(mode="json")
    return ok({"overview": payload})
