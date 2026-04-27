"""
API v1 router aggregating all endpoints.
"""
from __future__ import annotations

import re

from fastapi import APIRouter
from fastapi.routing import APIRoute

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.agent_personas import router as agent_personas_router
from app.api.v1.endpoints.assignments import router as assignments_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cohorts import router as cohorts_router
from app.api.v1.endpoints.evaluations import router as evaluations_router
from app.api.v1.endpoints.internal.evaluations import router as internal_evaluations_router
from app.api.v1.endpoints.scenarios import router as scenarios_router
from app.api.v1.endpoints.sessions import router as sessions_router
from app.api.v1.endpoints.tenants import get_tenant_for_member
from app.api.v1.endpoints.user_evaluations import router as user_evaluations_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(cohorts_router)
api_router.include_router(agent_personas_router)
api_router.include_router(scenarios_router)
api_router.include_router(sessions_router)
api_router.include_router(evaluations_router)
api_router.include_router(user_evaluations_router)
api_router.include_router(assignments_router)
api_router.include_router(analytics_router)
api_router.include_router(internal_evaluations_router)
# Tenant read: single explicit route (no nested router) so ``GET /{tenant_id}`` can never shadow ``/cohorts``.
api_router.add_api_route(
    "/tenants/{tenant_id}",
    get_tenant_for_member,
    methods=["GET"],
    tags=["Tenants"],
    summary="Get tenant (member only)",
)


def _reject_root_level_tenant_id_routes(router: APIRouter) -> None:
    """
    A single path segment ``/{tenant_id}`` on this router becomes ``/api/v1/{tenant_id}`` when mounted,
    which steals ``/api/v1/cohorts``, ``/api/v1/sessions``, etc. Refuse to boot if that pattern appears.
    """
    bad = re.compile(r"^/\{tenant_id\}$", re.IGNORECASE)
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        p = route.path or ""
        if bad.match(p):
            raise RuntimeError(
                f"Misconfigured API: route {p!r} would treat ``cohorts`` / ``sessions`` as a UUID. "
                "Tenant read must be registered as ``/tenants/{{tenant_id}}`` only (see ``endpoints/tenants.py``). "
                "Restart uvicorn from the repo root and delete stale ``__pycache__`` if you already fixed this file."
            )


_reject_root_level_tenant_id_routes(api_router)
