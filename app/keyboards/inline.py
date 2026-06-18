from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔍 Лучшие тренды", callback_data="top_trends")],
        [InlineKeyboardButton(text="📋 Все статьи", callback_data="all_articles")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_article_keyboard(
    article_id: int, published: bool = False
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="📝 Опубликовать",
                callback_data=f"publish:{article_id}",
            ),
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=f"edit:{article_id}",
            ),
            InlineKeyboardButton(
                text="🔗 Открыть",
                callback_data=f"open:{article_id}",
            ),
            InlineKeyboardButton(
                text="📊 Аналитика",
                callback_data=f"analytics:{article_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=f"delete:{article_id}",
            ),
        ],
    ]
    if published:
        buttons[0][0] = InlineKeyboardButton(
            text="✅ Опубликовано",
            callback_data="already_published",
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
