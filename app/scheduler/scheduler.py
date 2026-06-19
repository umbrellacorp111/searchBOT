import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from app.config import settings
from app.database.session import async_session_factory
from app.database import crud
from app.services.content_discovery import run_discovery_cycle
from app.services.ai_processor import process_article

scheduler = AsyncIOScheduler()


async def process_unprocessed() -> int:
    async with async_session_factory() as session:
        articles = await crud.get_unprocessed_articles(
            session, limit=settings.max_articles_per_fetch
        )

    processed = 0
    for article in articles:
        try:
            if article.viral_score == 0:
                async with async_session_factory() as session:
                    await crud.update_article_translation(
                        session=session,
                        article_id=article.id,
                        title_ru=article.title,
                        translation="Discarded",
                        summary="Discarded",
                        category="Discarded",
                        trend_reason="Discarded",
                    )
                continue

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


async def fetch_and_process():
    added = await run_discovery_cycle()
    processed = await process_unprocessed()
    logger.info(f"Cycle: +{added} articles, AI={processed}")


async def send_top_trends():
    if not settings.channel_id:
        return
    from app.bot.bot import bot
    from app.handlers.content import _send_content_card

    async with async_session_factory() as session:
        articles = await crud.get_unseen_by_category(
            session, category=None, min_score=settings.min_viral_score, limit=5
        )
        if not articles:
            logger.info("No top trends to auto-publish")
            return

    for article in articles:
        try:
            await _send_content_card(settings.channel_id, article)
            async with async_session_factory() as session:
                await crud.mark_articles_as_shown(session, [article.id])
            logger.info(f"Auto-published article {article.id} (score={article.viral_score})")
        except Exception as e:
            logger.error(f"Failed to auto-publish article {article.id}: {e}")


async def force_fetch_trends_now() -> tuple:
    from app.services.content_discovery import run_discovery_cycle
    added = await run_discovery_cycle()
    processed = await process_unprocessed()
    return added, processed


def setup_scheduler() -> AsyncIOScheduler:
    fetch_interval = settings.fetch_interval_minutes
    analyze_interval = settings.analyze_interval_minutes
    publish_interval = settings.publish_interval_minutes

    scheduler.add_job(
        fetch_and_process,
        IntervalTrigger(minutes=fetch_interval),
        id="discover_and_process",
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
        f"AI every {analyze_interval}m, "
        f"publish every {publish_interval}m"
    )
    return scheduler
