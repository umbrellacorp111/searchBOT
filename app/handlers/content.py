import html
from typing import Optional
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from app.config import settings
from app.bot.bot import bot
from app.database.session import async_session_factory
from app.database import crud
from app.keyboards.inline import get_content_keyboard, get_start_keyboard

router = Router()


class EditState(StatesGroup):
    waiting_for_title = State()
    waiting_for_translation = State()
    waiting_for_summary = State()


def _score_emoji(score: int) -> str:
    if score >= 95:
        return "🔥🔥"
    if score >= 90:
        return "🔥"
    if score >= 85:
        return "💎"
    if score >= 50:
        return "📈"
    return "📌"


def _truncate(text: str, limit: int) -> str:
    if len(text) > limit:
        return text[:limit].rsplit(" ", 1)[0] + "..."
    return text


def _format_content_card(article) -> str:
    title = html.escape(article.title_ru or article.title)
    summary = html.escape(article.summary or "No summary")
    source = html.escape(article.source)
    category = html.escape(article.category or "Trends")
    score = article.viral_score

    card = f"{_score_emoji(score)} <b>Content Score: {score}/100</b>\n"
    card += f"📂 <b>{category}</b>\n\n"
    card += f"<b>{_truncate(title, 200)}</b>\n\n"

    media_url = (article.media_urls or "").split(",")[0].strip()
    if media_url:
        card += f"🖼 <a href='{html.escape(media_url)}'>Media</a> | "
    if article.product_url:
        card += f"🛒 <a href='{html.escape(article.product_url)}'>Product</a> | "
    if article.original_post_url:
        card += f"📱 <a href='{html.escape(article.original_post_url)}'>Original</a>"
    card += "\n\n"

    trend_reason = article.trend_reason or ""
    if trend_reason and trend_reason != "Discarded":
        card += f"💡 <b>Why trending:</b>\n{_truncate(trend_reason, 400)}\n\n"

    card += f"📝 <b>Summary:</b>\n{_truncate(summary, 400)}\n\n"
    card += f"🌍 {source}"

    if len(card) > 4000:
        card = card[:3800].rsplit("\n", 1)[0] + "\n\n..."
    return card


def _format_analytics(article) -> str:
    return (
        f"📊 <b>Content Analytics</b>\n\n"
        f"{_score_emoji(article.viral_score)} <b>Score:</b> {article.viral_score}/100\n"
        f"📂 <b>Category:</b> {article.category or 'N/A'}\n"
        f"🌐 <b>Country:</b> {article.country or 'Global'}\n"
        f"👁 Views: {article.views_count:,}\n"
        f"❤️ Likes: {article.likes_count:,}\n"
        f"💬 Comments: {article.comments_count:,}\n"
        f"🔄 Reposts: {article.shares_count:,}\n"
        f"📌 Saved: {article.mentions_count:,}\n"
        f"🌍 Source: {article.source}\n"
        f"🔗 <a href='{html.escape(article.url)}'>Link</a>\n"
    )


async def _send_content_card(
    chat_id: int,
    article,
    edit_message_id: Optional[int] = None,
) -> Optional[types.Message]:
    text = _format_content_card(article)
    keyboard = get_content_keyboard(
        article.id,
        url=article.url,
        media_url=article.media_urls or "",
        original_post_url=article.original_post_url or "",
    )
    if edit_message_id:
        return await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=edit_message_id,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )
    return await bot.send_message(
        chat_id,
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=False,
    )


async def _show_content_by_category(chat_id: int, category: str, edit_msg_id: Optional[int] = None):
    async with async_session_factory() as session:
        articles = await crud.get_unseen_by_category(
            session, category=category, min_score=settings.min_viral_score, limit=10
        )
        if not articles:
            # Auto-trigger new discovery
            from app.scheduler.scheduler import fetch_and_process
            await bot.send_message(chat_id, "🔍 No new content found. Running discovery...")
            await fetch_and_process()
            async with async_session_factory() as session:
                articles = await crud.get_unseen_by_category(
                    session, category=category, min_score=settings.min_viral_score, limit=10
                )
            if not articles:
                await bot.send_message(chat_id, "📭 Still no content found. Try again later.")
                return

    article = articles[0]
    async with async_session_factory() as session:
        await crud.mark_articles_as_shown(session, [article.id])
    await _send_content_card(chat_id, article, edit_message_id=edit_msg_id)


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    is_admin = message.from_user.id == settings.owner_id
    await message.answer(
        "🔥 <b>Global Female Trend Intelligence</b>\n\n"
        "Discover the next viral trends before they hit Russia.\n"
        "Powered by AI analysis of 10+ global sources.\n\n"
        "Choose a category:",
        reply_markup=get_start_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("cat:"))
async def cb_category(callback: types.CallbackQuery):
    category = callback.data.split(":", 1)[1]
    await callback.answer(f"Loading {category}...")
    await _show_content_by_category(callback.message.chat.id, category)


@router.callback_query(F.data.startswith("next:"))
async def cb_next(callback: types.CallbackQuery):
    current_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        article = await crud.get_article_by_id(session, current_id)
        if not article:
            await callback.answer("❌ Article not found")
            return
        category = article.category

        await crud.mark_articles_as_shown(session, [current_id])

        remaining = await crud.get_unseen_by_category(
            session, category=category, min_score=settings.min_viral_score, limit=1
        )
        if not remaining:
            await callback.answer("📭 No more in this category")
            return
        next_article = remaining[0]

    await _send_content_card(callback.message.chat.id, next_article)
    await callback.answer()


@router.callback_query(F.data == "delete_all_now")
async def cb_delete_all_now(callback: types.CallbackQuery):
    async with async_session_factory() as session:
        count = await crud.delete_all_articles(session)
    await callback.message.edit_text(f"🗑 Удалено {count} статей")
    await callback.answer(f"✅ Удалено {count}")


@router.callback_query(F.data == "show_archive")
async def cb_show_archive(callback: types.CallbackQuery):
    async with async_session_factory() as session:
        articles = await crud.get_all_articles_no_filter(session, limit=20)
    if not articles:
        await callback.message.answer("📭 Архив пуст")
        await callback.answer()
        return
    lines = []
    for i, a in enumerate(articles, 1):
        score_emoji = "🆕" if not a.shown else "✅"
        cat = a.category or "—"
        title = a.title or "No title"
        if len(title) > 50:
            title = title[:47] + "..."
        lines.append(f"{i}. {score_emoji} [{cat}] {title}")
    text = "<b>📦 Архив (последние 20):</b>\n\n" + "\n".join(lines)
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "show_stats")
async def cb_show_stats(callback: types.CallbackQuery):
    async with async_session_factory() as session:
        stats = await crud.get_stats(session, min_high_score=settings.min_viral_score)
        unseen = await crud.get_unseen_count(session, min_score=settings.min_viral_score)
    text = (
        f"<b>📊 Statistics</b>\n\n"
        f"Total articles: {stats['total']}\n"
        f"Published: {stats['published']}\n"
        f"AI-processed: {stats['translated']}\n"
        f"Avg Score: {stats['avg_score']}\n\n"
        f"<b>Unseen by category:</b>\n"
    )
    for cat, count in unseen.items():
        text += f"  {cat}: {count}\n"
    text += "\n<b>By country:</b>\n"
    for country, count in stats["countries"].items():
        text += f"  {country}: {count}\n"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("analytics:"))
async def cb_analytics(callback: types.CallbackQuery):
    article_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        article = await crud.get_article_by_id(session, article_id)
        if not article:
            await callback.answer("❌ Article not found")
            return
        text = _format_analytics(article)
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()



