import asyncio
from loguru import logger
from app.config import settings
from app.parsers.rss_parser import fetch_all_rss
from app.parsers.reddit_parser import fetch_all_reddit
from app.parsers.google_trends import fetch_google_trends
from app.parsers.hackernews import fetch_hackernews
from app.parsers.producthunt import fetch_producthunt
from app.parsers.youtube import fetch_youtube_trending
from app.parsers.bilibili import fetch_bilibili
from app.parsers.pixiv import fetch_pixiv
from app.parsers.cosme import fetch_cosme
from app.parsers.weibo import fetch_weibo
from app.database.session import async_session_factory
from app.database import crud
from app.services.trend_analyzer import (
    calculate_content_score,
    detect_category,
    detect_country,
    detect_language,
)


async def fetch_all_sources() -> list[dict]:
    tasks = await asyncio.gather(
        fetch_all_rss(),
        fetch_all_reddit(),
        fetch_google_trends(),
        fetch_hackernews(),
        fetch_producthunt(),
        fetch_youtube_trending(),
        fetch_bilibili(),
        fetch_pixiv(),
        fetch_cosme(),
        fetch_weibo(),
        return_exceptions=True,
    )

    all_articles = []
    source_names = [
        "RSS", "Reddit", "Google Trends", "HN", "Product Hunt",
        "YouTube", "Bilibili", "Pixiv", "@cosme", "Weibo",
    ]
    for name, result in zip(source_names, tasks):
        if isinstance(result, Exception):
            logger.error(f"{name} fetch failed: {result}")
            continue
        all_articles.extend(result)

    logger.info(f"Fetched {len(all_articles)} raw articles from {len(source_names)} sources")
    return all_articles[:settings.max_articles_per_fetch]


async def run_discovery_cycle() -> int:
    raw = await fetch_all_sources()

    added = 0
    async with async_session_factory() as session:
        for data in raw:
            try:
                title = data.get("title", "No title")
                content = data.get("content", "")
                source = data.get("source", "")

                content_score = calculate_content_score(
                    data, title=title, content=content
                )
                category = detect_category(title, content)
                country = detect_country(source, title, content)
                language = detect_language(source)

                saved = await crud.add_article(
                    session=session,
                    title=title,
                    url=data.get("url", ""),
                    source=source,
                    content=content,
                    country=country or data.get("country"),
                    language=language or data.get("language"),
                    viral_score=content_score,
                    views_count=data.get("views", 0),
                    likes_count=data.get("likes", 0),
                    comments_count=data.get("comments", 0),
                    shares_count=data.get("shares", 0),
                    mentions_count=data.get("mentions_count", 0),
                )
                if saved:
                    added += 1
            except Exception as e:
                logger.error(f"Failed during discovery: {e}")

    logger.info(f"Discovery cycle done: {added} new articles saved")
    return added
