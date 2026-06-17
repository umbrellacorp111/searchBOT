from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from app.config import settings
from app.database.session import async_session_factory
from app.database import crud
from app.parsers.rss_parser import fetch_all_rss
from app.parsers.reddit_parser import fetch_all_reddit
from app.services.ai_processor import process_article

scheduler = AsyncIOScheduler()


async def fetch_trends() -> int:
    logger.info("Starting trend fetch cycle...")
    articles = []
    articles.extend(await fetch_all_rss())
    articles.extend(await fetch_all_reddit())

    added_count = 0
    async with async_session_factory() as session:
        for article_data in articles:
            try:
                saved = await crud.add_article(
                    session=session,
                    title=article_data["title"],
                    url=article_data["url"],
                    source=article_data["source"],
                    content=article_data.get("content", ""),
                )
                if saved:
                    added_count += 1
            except Exception as e:
                logger.error(f"Failed to save article: {e}")

    logger.info(f"Trend fetch complete: {added_count} new articles added")
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
            )
            async with async_session_factory() as session:
                await crud.update_article_translation(
                    session=session,
                    article_id=article.id,
                    title_ru=result["title_ru"],
                    translation=result["translation"],
                    summary=result["summary"],
                    category=result["category"],
                )
            processed += 1
            logger.info(f"Processed article {article.id}: {result['category']}")
        except Exception as e:
            logger.error(f"Failed to process article {article.id}: {e}")

    logger.info(f"AI processing complete: {processed} articles processed")
    return processed


async def send_unpublished():
    from app.bot.bot import bot
    from app.handlers.content import _send_article

    async with async_session_factory() as session:
        articles = await crud.get_unpublished_articles(session, limit=5)
        if not articles:
            return

    for article in articles:
        try:
            if settings.channel_id:
                await _send_article(settings.channel_id, article)
                async with async_session_factory() as session:
                    await crud.mark_published(session, article.id)
                logger.info(f"Auto-published article {article.id} to channel")
        except Exception as e:
            logger.error(f"Failed to auto-publish article {article.id}: {e}")


async def force_fetch_trends_now() -> int:
    added = await fetch_trends()
    processed = await process_unprocessed()
    logger.info(f"Force fetch done: added={added}, processed={processed}")
    return added


def setup_scheduler() -> AsyncIOScheduler:
    fetch_interval = settings.fetch_interval_minutes
    publish_interval = settings.publish_interval_minutes

    scheduler.add_job(
        fetch_and_process,
        IntervalTrigger(minutes=fetch_interval),
        id="fetch_trends",
        replace_existing=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        send_unpublished,
        IntervalTrigger(minutes=publish_interval),
        id="send_unpublished",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info(f"Scheduler configured: fetch every {fetch_interval}m, publish every {publish_interval}m")
    return scheduler


async def fetch_and_process():
    added = await fetch_trends()
    if added > 0:
        await process_unprocessed()
