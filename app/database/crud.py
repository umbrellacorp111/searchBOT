from typing import Optional, Sequence
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.database.models import Article


async def add_article(
    session: AsyncSession,
    title: str,
    url: str,
    source: str,
    content: Optional[str] = None,
) -> Optional[Article]:
    existing = await get_article_by_url(session, url)
    if existing:
        logger.debug(f"Duplicate article skipped: {url}")
        return None
    article = Article(
        title=title,
        url=url,
        source=source,
        content=content,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)
    logger.info(f"Article saved: id={article.id} source={source}")
    return article


async def get_article_by_url(session: AsyncSession, url: str) -> Optional[Article]:
    result = await session.execute(select(Article).where(Article.url == url))
    return result.scalar_one_or_none()


async def get_article_by_id(session: AsyncSession, article_id: int) -> Optional[Article]:
    result = await session.execute(select(Article).where(Article.id == article_id))
    return result.scalar_one_or_none()


async def get_unprocessed_articles(
    session: AsyncSession, limit: int = 20
) -> Sequence[Article]:
    result = await session.execute(
        select(Article)
        .where(Article.translation.is_(None))
        .order_by(Article.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_unpublished_articles(
    session: AsyncSession, limit: int = 10
) -> Sequence[Article]:
    result = await session.execute(
        select(Article)
        .where(Article.published.is_(False), Article.translation.isnot(None))
        .order_by(Article.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()


async def update_article_translation(
    session: AsyncSession,
    article_id: int,
    title_ru: str,
    translation: str,
    summary: str,
    category: str,
) -> Optional[Article]:
    article = await get_article_by_id(session, article_id)
    if not article:
        logger.warning(f"Article {article_id} not found for translation update")
        return None
    article.title_ru = title_ru
    article.translation = translation
    article.summary = summary
    article.category = category
    await session.commit()
    await session.refresh(article)
    logger.info(f"Article {article_id} translation updated")
    return article


async def mark_published(session: AsyncSession, article_id: int) -> bool:
    article = await get_article_by_id(session, article_id)
    if not article:
        return False
    article.published = True
    await session.commit()
    logger.info(f"Article {article_id} marked as published")
    return True


async def get_stats(session: AsyncSession) -> dict:
    total = await session.scalar(select(func.count(Article.id)))
    published = await session.scalar(
        select(func.count(Article.id)).where(Article.published.is_(True))
    )
    translated = await session.scalar(
        select(func.count(Article.id)).where(Article.translation.isnot(None))
    )
    categories_result = await session.execute(
        select(Article.category, func.count(Article.id))
        .where(Article.category.isnot(None))
        .group_by(Article.category)
    )
    categories = {row[0]: row[1] for row in categories_result}
    return {
        "total": total or 0,
        "published": published or 0,
        "unpublished": (total or 0) - (published or 0),
        "translated": translated or 0,
        "untranslated": (total or 0) - (translated or 0),
        "categories": categories,
    }


async def get_sources_stats(session: AsyncSession) -> list:
    result = await session.execute(
        select(Article.source, func.count(Article.id))
        .group_by(Article.source)
        .order_by(func.count(Article.id).desc())
    )
    return [{"source": row[0], "count": row[1]} for row in result]


async def delete_old_articles(session: AsyncSession, days: int = 30):
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        delete(Article).where(Article.created_at < cutoff)
    )
    await session.commit()
    logger.info(f"Deleted {result.rowcount} old articles")
