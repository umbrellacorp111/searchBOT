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
from app.keyboards.inline import get_article_keyboard

router = Router()


class EditState(StatesGroup):
    waiting_for_title = State()
    waiting_for_translation = State()
    waiting_for_summary = State()


def _format_article_card(article) -> str:
    title = html.escape(article.title_ru or article.title)
    translation = html.escape(article.translation or "Перевод не выполнен")
    summary = html.escape(article.summary or "Резюме не сгенерировано")
    trend_reason = html.escape(article.trend_reason or "")
    source = html.escape(article.source)
    url = html.escape(article.url)
    score = article.viral_score

    score_emoji = "🔥" if score >= 90 else "📈" if score >= 80 else "💡" if score >= 70 else "📌"

    card = f"{score_emoji} <b>VIRAL SCORE: {score}/100</b>\n\n"
    card += f"🌍 Источник: {source}\n"
    card += f"🔗 Ссылка: {url}\n"

    if trend_reason:
        card += f"\n📈 <b>Почему это тренд:</b>\n{trend_reason}\n"

    card += f"\n📝 <b>AI-резюме:</b>\n{summary}\n"
    card += f"\n🇷🇺 <b>Перевод:</b>\n{translation}"

    return card


def _format_analytics(article) -> str:
    growth = "Быстрый" if article.viral_score >= 85 else "Умеренный" if article.viral_score >= 70 else "Низкий"
    scope = "Мировой"
    if article.country and article.country not in ("Global", ""):
        scope = f"Локальный ({article.country})"

    return (
        f"📊 <b>Аналитика тренда</b>\n\n"
        f"🔥 <b>Viral Score:</b> {article.viral_score}/100\n"
        f"📰 <b>Упоминаний:</b> {article.mentions_count}\n"
        f"🌍 <b>Источников:</b> 1+\n"
        f"📈 <b>Скорость роста:</b> {growth}\n"
        f"🌐 <b>Охват:</b> {scope}\n"
        f"👁 <b>Просмотров:</b> {article.views_count:,}\n"
        f"❤️ <b>Лайков:</b> {article.likes_count:,}\n"
        f"💬 <b>Комментариев:</b> {article.comments_count:,}\n"
        f"🔄 <b>Репостов:</b> {article.shares_count:,}\n"
    )


async def _send_article(
    chat_id: int,
    article,
    edit_message_id: Optional[int] = None,
) -> Optional[types.Message]:
    text = _format_article_card(article)
    keyboard = get_article_keyboard(article.id, published=article.published)
    if edit_message_id:
        return await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=edit_message_id,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    return await bot.send_message(
        chat_id, text, reply_markup=keyboard, parse_mode="HTML"
    )


@router.message(Command("articles"))
async def cmd_articles(message: types.Message):
    async with async_session_factory() as session:
        articles = await crud.get_all_articles(session, limit=200)
    if not articles:
        await message.answer("📭 Нет статей в базе.")
        return
    await message.answer(f"📋 Найдено статей: {len(articles)}. Отправляю...")
    for article in articles[:50]:
        await _send_article(message.chat.id, article)
    remaining = len(articles) - 50
    if remaining > 0:
        await message.answer(f"📌 Показано 50 из {len(articles)}. Остальные — /articles")


@router.callback_query(F.data == "all_articles")
async def cb_all_articles(callback: types.CallbackQuery):
    async with async_session_factory() as session:
        articles = await crud.get_all_articles(session, limit=200)
    if not articles:
        await callback.answer("📭 Нет статей в базе")
        return
    await callback.answer(f"Отправляю до 50 статей...")
    for article in articles[:50]:
        await _send_article(callback.message.chat.id, article)
    remaining = len(articles) - 50
    if remaining > 0:
        await callback.message.answer(f"📌 Показано 50 из {len(articles)}. Остальные — /articles")


@router.callback_query(F.data == "top_trends")
async def cb_top_trends(callback: types.CallbackQuery):
    async with async_session_factory() as session:
        articles = await crud.get_top_trends(session, limit=10, min_score=70)
    if not articles:
        await callback.answer("📭 Нет трендов с высоким Viral Score")
        return
    await callback.answer(f"Отправляю топ тренды...")
    for article in articles:
        await _send_article(callback.message.chat.id, article)


@router.callback_query(F.data == "show_stats")
async def cb_show_stats(callback: types.CallbackQuery):
    async with async_session_factory() as session:
        stats = await crud.get_stats(session)
    text = (
        f"<b>📊 Статистика</b>\n\n"
        f"Всего статей: {stats['total']}\n"
        f"Опубликовано: {stats['published']}\n"
        f"Переведено AI: {stats['translated']}\n"
        f"Viral Score ≥ 70: {stats['high_score']}\n"
        f"Средний Score: {stats['avg_score']}\n\n"
        f"<b>По странам:</b>\n"
    )
    for country, count in stats["countries"].items():
        text += f"  {country}: {count}\n"
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data.startswith("analytics:"))
async def cb_analytics(callback: types.CallbackQuery):
    article_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        article = await crud.get_article_by_id(session, article_id)
        if not article:
            await callback.answer("❌ Статья не найдена")
            return
        text = _format_analytics(article)
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()


@router.message(Command("next"))
async def cmd_next(message: types.Message):
    async with async_session_factory() as session:
        articles = await crud.get_unpublished_articles(session, limit=1)
        if not articles:
            await message.answer("✅ Нет неопубликованных статей.")
            return
        article = articles[0]
    await _send_article(message.chat.id, article)


@router.callback_query(F.data.startswith("publish:"))
async def cb_publish(callback: types.CallbackQuery):
    article_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        article = await crud.get_article_by_id(session, article_id)
        if not article:
            await callback.answer("❌ Статья не найдена")
            return
        if settings.channel_id:
            msg = await _send_article(settings.channel_id, article)
            if msg:
                await crud.mark_published(session, article_id)
                await callback.answer("✅ Опубликовано в канал")
                await callback.message.edit_reply_markup(
                    reply_markup=get_article_keyboard(article_id, published=True)
                )
        else:
            await crud.mark_published(session, article_id)
            await callback.answer("✅ Помечено как опубликовано")
            await callback.message.edit_reply_markup(
                reply_markup=get_article_keyboard(article_id, published=True)
            )


@router.callback_query(F.data.startswith("edit:"))
async def cb_edit(callback: types.CallbackQuery, state: FSMContext):
    article_id = int(callback.data.split(":")[1])
    await state.update_data(article_id=article_id)
    await callback.message.answer(
        "✏️ Введите новый заголовок (или /cancel для отмены):"
    )
    await state.set_state(EditState.waiting_for_title)
    await callback.answer()


@router.message(EditState.waiting_for_title)
async def edit_title(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Редактирование отменено")
        return
    await state.update_data(new_title=message.text)
    await message.answer("✏️ Введите новый перевод (или /cancel):")
    await state.set_state(EditState.waiting_for_translation)


@router.message(EditState.waiting_for_translation)
async def edit_translation(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Редактирование отменено")
        return
    await state.update_data(new_translation=message.text)
    await message.answer("✏️ Введите новое резюме (или /cancel):")
    await state.set_state(EditState.waiting_for_summary)


@router.message(EditState.waiting_for_summary)
async def edit_summary(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Редактирование отменено")
        return
    data = await state.get_data()
    article_id = data["article_id"]
    new_title = data.get("new_title")
    new_translation = data.get("new_translation")

    async with async_session_factory() as session:
        article = await crud.get_article_by_id(session, article_id)
        if article:
            article.title_ru = new_title or article.title_ru
            article.translation = new_translation or article.translation
            article.summary = message.text or article.summary
            await session.commit()
            await _send_article(
                message.chat.id, article,
                edit_message_id=data.get("original_message_id"),
            )
            await message.answer("✅ Статья обновлена")
    await state.clear()


@router.callback_query(F.data.startswith("open:"))
async def cb_open(callback: types.CallbackQuery):
    article_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        article = await crud.get_article_by_id(session, article_id)
        if not article:
            await callback.answer("❌ Статья не найдена")
            return
    await callback.answer()
    await callback.message.answer(f"🔗 Оригинал: {html.escape(article.url)}")


@router.callback_query(F.data.startswith("delete:"))
async def cb_delete(callback: types.CallbackQuery):
    article_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        deleted = await crud.delete_article_by_id(session, article_id)
    if deleted:
        await callback.answer("🗑 Статья удалена")
        await callback.message.delete()
    else:
        await callback.answer("❌ Статья не найдена")
