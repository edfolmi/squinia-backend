"""
Rate limiting middleware using slowapi.
Protects endpoints from abuse with configurable limits.
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=str(settings.REDIS_URL),
    strategy="fixed-window"
)

# Export rate limit exceeded handler
rate_limit_exceeded_handler = _rate_limit_exceeded_handler
