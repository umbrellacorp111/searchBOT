from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


CATEGORIES = [
    "🔥 Hot Trends",
    "💄 Beauty",
    "👗 Fashion",
    "✨ Aesthetics",
    "🛍 Viral Products",
    "🏠 Home Decor",
    "🎥 Viral Videos",
    "💎 Luxury",
    "🌸 Asia Trends",
    "📌 Pinterest Ideas",
]


def get_start_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for cat in CATEGORIES:
        row.append(InlineKeyboardButton(text=cat, callback_data=f"cat:{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats"),
    ])
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="🗑 Удалить все", callback_data="delete_all_confirm"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_content_keyboard(
    article_id: int,
    url: str,
    media_url: str = "",
    original_post_url: str = "",
) -> InlineKeyboardMarkup:
    buttons = []
    if original_post_url:
        buttons.append([
            InlineKeyboardButton(text="📱 Оригинал", url=original_post_url),
        ])
    elif url:
        buttons.append([
            InlineKeyboardButton(text="🔗 Источник", url=url),
        ])
    if media_url:
        buttons.append([
            InlineKeyboardButton(text="🖼 Медиа", url=media_url),
        ])
    buttons.append([
        InlineKeyboardButton(text="▶️ Далее", callback_data=f"next:{article_id}"),
        InlineKeyboardButton(text="📊 Аналитика", callback_data=f"analytics:{article_id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_delete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить всё", callback_data="delete_all_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="delete_all_no"),
        ],
    ])
