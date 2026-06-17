from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.handlers import admin, content
from app.middlewares.logging import LoggingMiddleware

try:
    from aiogram.fsm.storage.redis import RedisStorage
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.config import settings


def setup_dispatcher() -> Dispatcher:
    if REDIS_AVAILABLE and settings.redis_url:
        try:
            redis = aioredis.from_url(settings.redis_url)
            storage = RedisStorage(redis)
        except Exception:
            storage = MemoryStorage()
    else:
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.include_router(admin.router)
    dp.include_router(content.router)
    return dp
