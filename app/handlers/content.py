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
    title = article.title_ru or article.title
    translation = article.translation or "Перевод не выполнен"
    summary = article.summary or "Резюме не сгенерировано"
    category = article.category or "Без категории"
    category_emoji = {
        "Beauty": "💄", "Fashion": "👗", "Lifestyle": "🌟",
        "Trends": "📈", "K-Beauty": "🇰🇷", "J-Beauty": "🇯🇵", "C-Beauty": "🇨🇳",
    }.get(category, "📰")

    return (
        f"{category_emoji} <b>{title}</b>\n\n"
        f"🌍 Источник: {article.source}\n"
        f"🔗 Ссылка: {article.url}\n\n"
        f"📝 <b>AI-резюме:</b>\n{summary}\n\n"
        f"🇷🇺 <b>Перевод:</b>\n{translation}"
    )


async def _send_article(
    chat_id: int,
    article,
    edit_message_id: Optional[int] = None,
) -> Optional[types.Message]:
    text = _format_article_card(article)
    keyboard = get_article_keyboard(article.id)
    if edit_message_id:
        return await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=edit_message_id,
            reply_markup=keyboard,
        )
    return await bot.send_message(
        chat_id, text, reply_markup=keyboard
    )


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
    await callback.message.answer(f"🔗 Оригинал: {article.url}")
