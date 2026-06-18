from typing import Optional, Sequence
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.database.models import Article
from app.parsers.rss_parser import RSS_SOURCES


async def add_article(
    session: AsyncSession,
    title: str,
    url: str,
    source: str,
    content: Optional[str] = None,
    country: Optional[str] = None,
    language: Optional[str] = None,
    viral_score: int = 0,
    views_count: int = 0,
    likes_count: int = 0,
    comments_count: int = 0,
    shares_count: int = 0,
    mentions_count: int = 0,
) -> Optional[Article]:
    existing = await get_article_by_url(session, url)
    if existing:
        return None
    article = Article(
        title=title,
        original_title=title,
        url=url,
        source=source,
        content=content,
        country=country,
        language=language,
        viral_score=viral_score,
        views_count=views_count,
        likes_count=likes_count,
        comments_count=comments_count,
        shares_count=shares_count,
        mentions_count=mentions_count,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)
    logger.info(f"Article saved: id={article.id} source={source} score={viral_score}")
    return article


async def get_article_by_url(session: AsyncSession, url: str) -> Optional[Article]:
    result = await session.execute(select(Article).where(Article.url == url))
    return result.scalar_one_or_none()


async def get_article_by_id(session: AsyncSession, article_id: int) -> Optional[Article]:
    result = await session.execute(select(Article).where(Article.id == article_id))
    return result.scalar_one_or_none()


async def get_unprocessed_articles(
    session: AsyncSession, limit: int = 30
) -> Sequence[Article]:
    result = await session.execute(
        select(Article)
        .where(Article.translation.is_(None))
        .order_by(Article.viral_score.desc(), Article.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_unpublished_articles(
    session: AsyncSession, limit: int = 10
) -> Sequence[Article]:
    result = await session.execute(
        select(Article)
        .where(Article.published.is_(False), Article.translation.isnot(None))
        .order_by(Article.viral_score.desc(), Article.created_at.asc())
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
    trend_reason: Optional[str] = None,
) -> Optional[Article]:
    article = await get_article_by_id(session, article_id)
    if not article:
        return None
    article.title_ru = title_ru
    article.translation = translation
    article.summary = summary
    article.category = category
    if trend_reason:
        article.trend_reason = trend_reason
    await session.commit()
    await session.refresh(article)
    return article


async def mark_published(session: AsyncSession, article_id: int) -> bool:
    article = await get_article_by_id(session, article_id)
    if not article:
        return False
    article.published = True
    await session.commit()
    return True


async def get_top_trends(
    session: AsyncSession, limit: int = 10, min_score: int = 70
) -> Sequence[Article]:
    result = await session.execute(
        select(Article)
        .where(Article.viral_score >= min_score)
        .order_by(Article.viral_score.desc(), Article.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_stats(session: AsyncSession) -> dict:
    total = await session.scalar(select(func.count(Article.id)))
    published = await session.scalar(
        select(func.count(Article.id)).where(Article.published.is_(True))
    )
    translated = await session.scalar(
        select(func.count(Article.id)).where(Article.translation.isnot(None))
    )
    high_score = await session.scalar(
        select(func.count(Article.id)).where(Article.viral_score >= 70)
    )
    avg_score = await session.scalar(select(func.avg(Article.viral_score)))
    categories_result = await session.execute(
        select(Article.country, func.count(Article.id))
        .where(Article.country.isnot(None))
        .group_by(Article.country)
    )
    countries = {row[0]: row[1] for row in categories_result}
    return {
        "total": total or 0,
        "published": published or 0,
        "unpublished": (total or 0) - (published or 0),
        "translated": translated or 0,
        "high_score": high_score or 0,
        "avg_score": round(avg_score or 0, 1),
        "countries": countries,
    }


async def get_sources_stats(session: AsyncSession) -> list:
    result = await session.execute(
        select(Article.source, func.count(Article.id), func.avg(Article.viral_score))
        .group_by(Article.source)
        .order_by(func.count(Article.id).desc())
    )
    return [
        {"source": row[0], "count": row[1], "avg_score": round(row[2] or 0, 1)}
        for row in result
    ]


async def get_all_articles(
    session: AsyncSession, limit: int = 200, offset: int = 0
) -> Sequence[Article]:
    result = await session.execute(
        select(Article)
        .order_by(Article.viral_score.desc(), Article.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


async def get_articles_by_sources(
    session: AsyncSession, sources: list[str], limit: int = 50
) -> Sequence[Article]:
    result = await session.execute(
        select(Article)
        .where(Article.source.in_(sources))
        .order_by(Article.viral_score.desc(), Article.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


SOURCE_PREFIXES = {
    "youtube": "YouTube",
    "reddit": "reddit/r/",
    "google_trends": "Google Trends",
    "hacker_news": "Hacker News",
    "product_hunt": "Product Hunt",
    "rss": None,
}


async def get_articles_by_source_key(
    session: AsyncSession, source_key: str, limit: int = 30
) -> Sequence[Article]:
    prefix = SOURCE_PREFIXES.get(source_key)
    if prefix is None:
        return await get_articles_by_sources(
            session, list(RSS_SOURCES.keys()), limit
        )
    if source_key == "reddit":
        result = await session.execute(
            select(Article)
            .where(Article.source.startswith("reddit/r/"))
            .order_by(Article.viral_score.desc(), Article.created_at.desc())
            .limit(limit)
        )
    else:
        result = await session.execute(
            select(Article)
            .where(Article.source == prefix)
            .order_by(Article.viral_score.desc(), Article.created_at.desc())
            .limit(limit)
        )
    return result.scalars().all()


async def delete_article_by_id(session: AsyncSession, article_id: int) -> bool:
    article = await get_article_by_id(session, article_id)
    if not article:
        return False
    await session.delete(article)
    await session.commit()
    return True


async def get_fallback_articles(
    session: AsyncSession, limit: int = 50
) -> Sequence[Article]:
    result = await session.execute(
        select(Article)
        .where(Article.title_ru.isnot(None), Article.title_ru == Article.original_title)
        .order_by(Article.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def reset_article_translations(
    session: AsyncSession, article_ids: list[int]
) -> int:
    result = await session.execute(
        update(Article)
        .where(Article.id.in_(article_ids))
        .values(translation=None, title_ru=None, summary=None, category=None, trend_reason=None)
    )
    await session.commit()
    return result.rowcount


async def delete_old_articles(session: AsyncSession, days: int = 30):
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        delete(Article).where(Article.created_at < cutoff)
    )
    await session.commit()
    logger.info(f"Deleted {result.rowcount} old articles")
