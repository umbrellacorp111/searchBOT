from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔍 Лучшие тренды", callback_data="top_trends")],
        [
            InlineKeyboardButton(text="🔴 YouTube", callback_data="source:youtube"),
            InlineKeyboardButton(text="🔵 Reddit", callback_data="source:reddit"),
        ],
        [
            InlineKeyboardButton(text="🟢 Google Trends", callback_data="source:google_trends"),
            InlineKeyboardButton(text="⚫ Hacker News", callback_data="source:hacker_news"),
        ],
        [
            InlineKeyboardButton(text="🟠 Product Hunt", callback_data="source:product_hunt"),
            InlineKeyboardButton(text="📡 RSS", callback_data="source:rss"),
        ],
        [
            InlineKeyboardButton(text="📋 Все статьи", callback_data="all_articles"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats"),
        ],
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="🗑 Удалить все статьи", callback_data="delete_all_confirm"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_delete_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да, удалить всё", callback_data="delete_all_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="delete_all_no"),
        ],
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
