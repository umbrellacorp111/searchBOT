from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from app.config import settings
from app.database.session import async_session_factory
from app.database import crud
from app.scheduler.scheduler import force_fetch_trends_now
from app.keyboards.inline import get_start_keyboard

router = Router()


def _is_owner(user_id: int) -> bool:
    return settings.owner_id == 0 or user_id == settings.owner_id


class BroadcastState(StatesGroup):
    waiting_for_message = State()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = get_start_keyboard()
    await message.answer(
        "👋 <b>Trend Aggregator Bot</b>\n\n"
        "Собираю зарубежные тренды из США, Европы, Кореи, Японии и Китая.\n"
        "Перевожу на русский с помощью AI и отправляю готовые карточки.\n\n"
        "<b>Кнопки ниже</b> — найти статьи по региону.\n"
        "Команды администратора:\n"
        "/stats — статистика\n"
        "/sources — статистика по источникам\n"
        "/articles — все статьи\n"
        "/force_fetch — принудительный сбор трендов\n"
        "/reprocess — переобработать статьи (сбросить старый перевод)\n"
        "/broadcast — массовая рассылка",
        reply_markup=keyboard,
    )


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if not _is_owner(message.from_user.id):
        return
    async with async_session_factory() as session:
        stats = await crud.get_stats(session)
    text = (
        "<b>📊 Статистика</b>\n\n"
        f"Всего статей: {stats['total']}\n"
        f"Опубликовано: {stats['published']}\n"
        f"Не опубликовано: {stats['unpublished']}\n"
        f"Переведено: {stats['translated']}\n"
        f"Не переведено: {stats['untranslated']}\n\n"
        "<b>Категории:</b>\n"
    )
    for cat, count in stats["categories"].items():
        text += f"  {cat}: {count}\n"
    await message.answer(text)


@router.message(Command("sources"))
async def cmd_sources(message: types.Message):
    if not _is_owner(message.from_user.id):
        return
    async with async_session_factory() as session:
        sources = await crud.get_sources_stats(session)
    text = "<b>📡 Источники:</b>\n\n"
    for s in sources:
        text += f"  {s['source']}: {s['count']} статей\n"
    await message.answer(text)


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
    from sqlalchemy.ext.asyncio import AsyncSession

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
                    f"<b>📢 Рассылка</b>\n\n{message.text}",
                )
                sent += 1
            except Exception as e:
                logger.error(f"Broadcast send failed: {e}")
                failed += 1

    await message.answer(
        f"✅ Рассылка завершена.\nОтправлено: {sent}\nОшибок: {failed}"
    )
    await state.clear()
