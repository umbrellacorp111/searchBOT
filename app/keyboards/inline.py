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

CATEGORY_MAP = {
    "🔥 Hot Trends": "Trends",
    "💄 Beauty": "Beauty",
    "👗 Fashion": "Fashion",
    "✨ Aesthetics": "Aesthetic Trends",
    "🛍 Viral Products": "Viral Products",
    "🏠 Home Decor": "Home Decor",
    "🎥 Viral Videos": "Trends",
    "💎 Luxury": "Luxury",
    "🌸 Asia Trends": "K-Beauty",
    "📌 Pinterest Ideas": "Lifestyle",
}


def resolve_display_category(display: str) -> str:
    return CATEGORY_MAP.get(display, display)

def get_category_display_by_db(db_category: str) -> str:
    """Reverse lookup: DB category -> display name with emoji."""
    for display, db in CATEGORY_MAP.items():
        if db == db_category:
            return display
    return db_category


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
        InlineKeyboardButton(text="📋 Все тренды", callback_data="cat:all"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats"),
    ])
    buttons.append([
        InlineKeyboardButton(text="📦 Архив", callback_data="show_archive"),
        InlineKeyboardButton(text="🗑 Удалить всё", callback_data="delete_all_now"),
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



