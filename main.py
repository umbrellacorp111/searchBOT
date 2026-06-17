import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from app.config import settings
from app.bot.bot import bot
from app.bot.dispatcher import setup_dispatcher
from app.database.session import init_db
from app.scheduler.scheduler import setup_scheduler
from app.utils.logger import setup_logger
from app.utils.cache import cache

try:
    import httpx
    logger.info(f"httpx version: {httpx.__version__}")
except Exception:
    logger.warning("Could not determine httpx version")


async def main():
    setup_logger()
    logger.info("Starting Trend Aggregator Bot...")

    await init_db()
    logger.info("Database initialized")

    await cache.init()
    logger.info("Cache service initialized")

    dp = setup_dispatcher()
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Polling error: {e}")
    finally:
        scheduler.shutdown(wait=False)
        await cache.close()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
