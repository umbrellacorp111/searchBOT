import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from app.config import settings
from app.database.session import async_session_factory
from app.database import crud
from app.parsers.rss_parser import fetch_all_rss
from app.parsers.reddit_parser import fetch_all_reddit
from app.parsers.google_trends import fetch_google_trends
from app.parsers.hackernews import fetch_hackernews
from app.parsers.producthunt import fetch_producthunt
from app.parsers.youtube import fetch_youtube_trending
from app.services.trend_analyzer import calculate_content_score, detect_category, detect_country, detect_language
from app.services.ai_processor import process_article

scheduler = AsyncIOScheduler()


async def discover_trends() -> int:
    logger.info("Starting trend discovery cycle...")

    tasks = await asyncio.gather(
        fetch_all_rss(),
        fetch_all_reddit(),
        fetch_google_trends(),
        fetch_hackernews(),
        fetch_producthunt(),
        fetch_youtube_trending(),
        return_exceptions=True,
    )

    all_articles = []
    for i, task_result in enumerate(tasks):
        if isinstance(task_result, Exception):
            logger.error(f"Discover source {i} failed: {task_result}")
            continue
        all_articles.extend(task_result)

    logger.info(f"Total articles fetched: {len(all_articles)}")

    added_count = 0
    async with async_session_factory() as session:
        for article_data in all_articles:
            try:
                content_score = calculate_content_score(
                    article_data,
                    title=article_data.get("title", ""),
                    content=article_data.get("content", ""),
                )
                category = detect_category(
                    article_data.get("title", ""),
                    article_data.get("content", ""),
                )
                country = detect_country(
                    article_data.get("source", ""),
                    article_data.get("title", ""),
                    article_data.get("content", ""),
                )
                language = detect_language(article_data.get("source", ""))

                saved = await crud.add_article(
                    session=session,
                    title=article_data.get("title", "No title"),
                    url=article_data.get("url", ""),
                    source=article_data.get("source", ""),
                    content=article_data.get("content", ""),
                    country=country or article_data.get("country"),
                    language=language or article_data.get("language"),
                    viral_score=content_score,
                    views_count=article_data.get("views", 0),
                    likes_count=article_data.get("likes", 0),
                    comments_count=article_data.get("comments", 0),
                    shares_count=article_data.get("shares", 0),
                    mentions_count=article_data.get("mentions_count", 0),
                )
                if saved:
                    added_count += 1
            except Exception as e:
                logger.error(f"Failed to save article: {e}")

    logger.info(f"Discover complete: {added_count} new articles added")
    return added_count


async def process_unprocessed() -> int:
    async with async_session_factory() as session:
        articles = await crud.get_unprocessed_articles(
            session, limit=settings.max_articles_per_fetch
        )

    processed = 0
    for article in articles:
        try:
            result = await process_article(
                title=article.title,
                content=article.content or "",
                source=article.source,
                viral_score=article.viral_score,
            )
            async with async_session_factory() as session:
                await crud.update_article_translation(
                    session=session,
                    article_id=article.id,
                    title_ru=result["title_ru"],
                    translation=result["translation"],
                    summary=result["summary"],
                    category=result["category"],
                    trend_reason=result.get("trend_reason"),
                )
            processed += 1
        except Exception as e:
            logger.error(f"Failed to process article {article.id}: {e}")

    logger.info(f"AI processing complete: {processed} articles")
    return processed


async def send_top_trends():
    from app.bot.bot import bot
    from app.handlers.content import _send_article

    async with async_session_factory() as session:
        articles = await crud.get_top_trends(
            session, limit=5, min_score=settings.min_viral_score
        )
        if not articles:
            logger.info("No top trends to send")
            return

    for article in articles:
        try:
            if settings.channel_id:
                await _send_article(settings.channel_id, article)
                async with async_session_factory() as session:
                    await crud.mark_published(session, article.id)
                logger.info(
                    f"Auto-published article {article.id} (score={article.viral_score})"
                )
        except Exception as e:
            logger.error(f"Failed to auto-publish article {article.id}: {e}")


async def force_fetch_trends_now() -> tuple:
    added = await discover_trends()
    processed = await process_unprocessed()
    logger.info(f"Force fetch done: added={added}, processed={processed}")
    return added, processed


def setup_scheduler() -> AsyncIOScheduler:
    fetch_interval = settings.fetch_interval_minutes
    analyze_interval = settings.analyze_interval_minutes
    publish_interval = settings.publish_interval_minutes

    scheduler.add_job(
        fetch_and_process,
        IntervalTrigger(minutes=fetch_interval),
        id="discover_trends",
        replace_existing=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        send_top_trends,
        IntervalTrigger(minutes=publish_interval),
        id="send_top_trends",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info(
        f"Scheduler: discover every {fetch_interval}m, "
        f"analyze every {analyze_interval}m, "
        f"send every {publish_interval}m"
    )
    return scheduler


async def fetch_and_process():
    await discover_trends()
    await process_unprocessed()


