"""
API v1 router aggregating all endpoints.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.assignments import router as assignments_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cohorts import router as cohorts_router
from app.api.v1.endpoints.evaluations import router as evaluations_router
from app.api.v1.endpoints.internal.evaluations import router as internal_evaluations_router
from app.api.v1.endpoints.scenarios import router as scenarios_router
from app.api.v1.endpoints.sessions import router as sessions_router
from app.api.v1.endpoints.user_evaluations import router as user_evaluations_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(cohorts_router)
api_router.include_router(scenarios_router)
api_router.include_router(sessions_router)
api_router.include_router(evaluations_router)
api_router.include_router(user_evaluations_router)
api_router.include_router(assignments_router)
api_router.include_router(analytics_router)
api_router.include_router(internal_evaluations_router)
