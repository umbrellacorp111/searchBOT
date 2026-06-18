from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

REGION_SOURCES = {
    "japan": ["Fashion Press Japan", "Fashionsnap"],
    "korea": ["reddit/r/Kbeauty", "reddit/r/AsianBeauty", "reddit/r/KoreanBeauty"],
    "china": ["Sina Fashion", "Sohu Fashion"],
}

REGION_BUTTONS = [
    [
        InlineKeyboardButton(text="🇯🇵 Япония", callback_data="region:japan"),
        InlineKeyboardButton(text="🇰🇷 Корея", callback_data="region:korea"),
        InlineKeyboardButton(text="🇨🇳 Китай", callback_data="region:china"),
    ],
]


def get_start_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📋 Все статьи", callback_data="all_articles")],
        [
            InlineKeyboardButton(text="🇯🇵 Япония", callback_data="region:japan"),
            InlineKeyboardButton(text="🇰🇷 Корея", callback_data="region:korea"),
            InlineKeyboardButton(text="🇨🇳 Китай", callback_data="region:china"),
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
