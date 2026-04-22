"""
Redis cache utility for performance optimization.
Implements caching strategies for read-heavy operations.
"""
import json
from typing import Optional, Any, Callable
from functools import wraps
import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """
    Redis cache manager for caching application data.
    Implements TTL-based caching and cache invalidation.
    """
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Initialize Redis connection."""
        try:
            self._redis = await redis.from_url(
                str(settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self._redis = None
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")
    
    @property
    def available(self) -> bool:
        return self._redis is not None

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        if not self.available:
            return None
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not self.available:
            return False
        try:
            ttl = ttl or settings.REDIS_CACHE_TTL
            serialized = json.dumps(value)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        if not self.available:
            return False
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        if not self.available:
            return 0
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error("Cache pattern delete error", pattern=pattern, error=str(e))
            return 0

    async def exists(self, key: str) -> bool:
        if not self.available:
            return False
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error("Cache exists error", key=key, error=str(e))
            return False


# Global cache manager instance
cache_manager = CacheManager()


def cache_response(
    key_prefix: str,
    ttl: Optional[int] = None
):
    """
    Decorator for caching endpoint responses.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Cache TTL in seconds
        
    Example:
        @cache_response("users", ttl=300)
        async def get_users():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            cache_key = f"{key_prefix}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached = await cache_manager.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit", key=cache_key)
                return cached
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            logger.debug("Cache miss", key=cache_key)
            
            return result
        return wrapper
    return decorator
