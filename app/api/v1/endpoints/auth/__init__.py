"""
Auth domain HTTP routes: session flows and platform user management.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import sessions, users

router = APIRouter(prefix="/auth", tags=["Authentication"])
router.include_router(sessions.router)
router.include_router(users.router, prefix="/users")

__all__ = ["router"]
