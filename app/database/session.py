from typing import AsyncGenerator
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from loguru import logger
from app.config import settings
from app.database.models import Base

_db_url = settings.database_url
_engine_kwargs = {"echo": False}
if _db_url.startswith("postgresql"):
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(_db_url, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

NEW_COLUMNS = {
    "original_title": "VARCHAR(512)",
    "country": "VARCHAR(64)",
    "language": "VARCHAR(16)",
    "trend_reason": "TEXT",
    "viral_score": "INTEGER DEFAULT 0",
    "mentions_count": "INTEGER DEFAULT 0",
    "views_count": "INTEGER DEFAULT 0",
    "likes_count": "INTEGER DEFAULT 0",
    "comments_count": "INTEGER DEFAULT 0",
    "shares_count": "INTEGER DEFAULT 0",
}


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    def _migrate(sync_conn):
        inspector = inspect(sync_conn)
        existing = {c["name"] for c in inspector.get_columns("articles")}
        for col_name, col_type in NEW_COLUMNS.items():
            if col_name not in existing:
                q = text(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
                sync_conn.execute(q)
                logger.info(f"Added column '{col_name}' to articles table")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(_migrate)
        logger.info("Database migration complete")
    except Exception as e:
        logger.warning(f"Migration optional (non-critical): {e}")

    logger.info("Database initialized")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
