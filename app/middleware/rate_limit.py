"""
Rate limiting middleware using slowapi.
Protects endpoints from abuse with configurable limits.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.schemas.response import fail

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=str(settings.REDIS_URL),
    strategy="fixed-window",
)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded,
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=fail(code="RATE_LIMIT_EXCEEDED", message="Too many requests"),
    )
