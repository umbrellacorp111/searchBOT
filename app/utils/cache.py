import json
import time
from typing import Optional, Any
from loguru import logger
from app.config import settings

try:
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheService:
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._memory_cache: dict[str, tuple[float, Any]] = {}
        self._memory_ttl: int = 300
        self._enabled = settings.use_redis_cache

    async def init(self):
        if not self._enabled or not REDIS_AVAILABLE:
            logger.info("Redis cache disabled, using memory cache")
            return
        try:
            self._redis = aioredis.from_url(
                settings.redis_url or "redis://localhost:6379/0",
                decode_responses=True,
            )
            await self._redis.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to memory cache: {e}")
            self._redis = None

    async def get(self, key: str) -> Optional[Any]:
        if self._redis:
            try:
                data = await self._redis.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.debug(f"Redis get error: {e}")
        entry = self._memory_cache.get(key)
        if entry:
            expires, value = entry
            if time.time() < expires:
                return value
            del self._memory_cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        if self._redis:
            try:
                await self._redis.setex(key, ttl, json.dumps(value, default=str))
                return
            except Exception as e:
                logger.debug(f"Redis set error: {e}")
        self._memory_cache[key] = (time.time() + ttl, value)

    async def close(self):
        if self._redis:
            await self._redis.close()

    async def clear(self):
        self._memory_cache.clear()
        if self._redis:
            await self._redis.flushdb()


cache = CacheService()
