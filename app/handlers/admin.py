import html
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from app.config import settings
from app.database.session import async_session_factory
from app.database import crud
from app.scheduler.scheduler import force_fetch_trends_now
from app.keyboards.inline import get_confirm_delete_keyboard

router = Router()


def _is_owner(user_id: int) -> bool:
    return settings.owner_id == 0 or user_id == settings.owner_id


class BroadcastState(StatesGroup):
    waiting_for_message = State()





@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if not _is_owner(message.from_user.id):
        return
    async with async_session_factory() as session:
        stats = await crud.get_stats(session, min_high_score=settings.min_viral_score)
    text = (
        "<b>📊 Статистика</b>\n\n"
        f"Всего статей: {stats['total']}\n"
        f"Опубликовано: {stats['published']}\n"
        f"Не опубликовано: {stats['unpublished']}\n"
        f"Переведено AI: {stats['translated']}\n"
        f"Content Score ≥ {settings.min_viral_score}: {stats['high_score']}\n"
        f"Средний Score: {stats['avg_score']}\n\n"
        "<b>По странам:</b>\n"
    )
    for country, count in stats["countries"].items():
        text += f"  {country}: {count}\n"
    await message.answer(text)


@router.message(Command("sources"))
async def cmd_sources(message: types.Message):
    if not _is_owner(message.from_user.id):
        return
    async with async_session_factory() as session:
        sources = await crud.get_sources_stats(session)
    text = "<b>📡 Источники:</b>\n\n"
    for s in sources:
        text += f"  {html.escape(s['source'])}: {s['count']} статей (avg score: {s['avg_score']})\n"
    await message.answer(text)


@router.message(Command("top"))
async def cmd_top(message: types.Message):
    async with async_session_factory() as session:
        articles = await crud.get_top_trends(session, limit=10, min_score=settings.min_viral_score)
    if not articles:
        await message.answer(f"📭 Нет трендов с Content Score ≥ {settings.min_viral_score}.")
        return
    from app.handlers.content import _send_content_card
    await message.answer(f"🔍 Топ трендов: {len(articles)}")
    for article in articles:
        await _send_content_card(message.chat.id, article)


@router.message(Command("rescore"))
async def cmd_rescore(message: types.Message):
    if not _is_owner(message.from_user.id):
        return
    await message.answer("🔄 Пересчитываю Content Score для всех статей...")
    from app.services.trend_analyzer import calculate_content_score

    async with async_session_factory() as session:
        articles = await crud.get_all_articles(session)
        updates = []
        for a in articles:
            metrics = {"source": a.source or "", "views": a.views or 0, "likes": a.likes or 0, "comments": a.comments or 0, "country": a.country or ""}
            text = (a.content or "") + (a.summary or "")
            new_score = calculate_content_score(metrics, title=a.title or "", content=text)
            if new_score != a.viral_score:
                updates.append((a.id, new_score))
        if updates:
            count = await crud.batch_update_scores(session, updates)
            await message.answer(f"✅ Пересчитано {count} статей.")
        else:
            await message.answer("✅ Все оценки актуальны.")


@router.message(Command("reprocess"))
async def cmd_reprocess(message: types.Message):
    if not _is_owner(message.from_user.id):
        return
    await message.answer("🔄 Ищу статьи со старым переводом...")
    async with async_session_factory() as session:
        fallback = await crud.get_fallback_articles(session)
        if not fallback:
            await message.answer("✅ Нет статей, требующих переобработки.")
            return
        ids = [a.id for a in fallback]
        count = await crud.reset_article_translations(session, ids)
    await message.answer(f"🔄 Сброшено {count} статей. Запускаю перевод...")
    from app.scheduler.scheduler import process_unprocessed
    processed = await process_unprocessed()
    await message.answer(f"✅ Переведено {processed} статей.")


@router.message(Command("force_fetch"))
async def cmd_force_fetch(message: types.Message):
    if not _is_owner(message.from_user.id):
        return
    await message.answer("🔄 Запускаю принудительный сбор трендов...")
    added, processed = await force_fetch_trends_now()
    await message.answer(
        f"✅ Сбор завершён.\n"
        f"Добавлено новых: {added}\n"
        f"Обработано AI: {processed}"
    )


@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, state: FSMContext):
    if not _is_owner(message.from_user.id):
        return
    await message.answer("📝 Введите сообщение для рассылки:")
    await state.set_state(BroadcastState.waiting_for_message)


@router.message(BroadcastState.waiting_for_message)
async def process_broadcast(message: types.Message, state: FSMContext):
    if not _is_owner(message.from_user.id):
        return
    from app.bot.bot import bot
    from app.database.session import async_session_factory
    from sqlalchemy import select
    from app.database.models import Article

    async with async_session_factory() as session:
        sent = 0
        failed = 0
        result = await session.execute(
            select(Article).where(Article.published.is_(True))
        )
        articles = result.scalars().all()
        for article in articles:
            try:
                await bot.send_message(
                    message.chat.id,
                    f"<b>📢 Рассылка</b>\n\n{html.escape(message.text)}",
                )
                sent += 1
            except Exception as e:
                logger.error(f"Broadcast send failed: {e}")
                failed += 1

    await message.answer(
        f"✅ Рассылка завершена.\nОтправлено: {sent}\nОшибок: {failed}"
    )
    await state.clear()


@router.callback_query(F.data == "delete_all_confirm")
async def cb_delete_all_confirm(callback: types.CallbackQuery):
    if not _is_owner(callback.from_user.id):
        await callback.answer("❌ Только админ")
        return
    await callback.message.answer(
        "⚠️ <b>Точно удалить ВСЕ статьи из базы?</b>\n\n"
        "Это действие нельзя отменить.",
        reply_markup=get_confirm_delete_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("clear"))
async def cmd_clear(message: types.Message):
    if not _is_owner(message.from_user.id):
        return
    await message.answer(
        "⚠️ <b>Точно удалить ВСЕ статьи из базы?</b>\n\n"
        "Это действие нельзя отменить.",
        reply_markup=get_confirm_delete_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "delete_all_yes")
async def cb_delete_all_yes(callback: types.CallbackQuery):
    if not _is_owner(callback.from_user.id):
        await callback.answer("❌ Только админ")
        return
    async with async_session_factory() as session:
        count = await crud.delete_all_articles(session)
    await callback.message.edit_text(
        f"🗑 Удалено {count} статей.",
    )
    await callback.answer()


@router.callback_query(F.data == "delete_all_no")
async def cb_delete_all_no(callback: types.CallbackQuery):
    if not _is_owner(callback.from_user.id):
        await callback.answer("❌ Только админ")
        return
    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()
