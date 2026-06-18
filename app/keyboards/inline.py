from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

REGION_SOURCES = {
    "japan": [
        "Fashion Press Japan", "Fashionsnap",
        "reddit/r/japanesebeauty", "reddit/r/JapaneseFashion", "reddit/r/JBeauty",
    ],
    "korea": [
        "reddit/r/Kbeauty", "reddit/r/AsianBeauty", "reddit/r/KoreanBeauty",
    ],
    "china": [
        "Sina Fashion", "Sohu Fashion",
        "reddit/r/ChinaFashion", "reddit/r/ChineseBeauty",
    ],
}


def get_start_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📋 Все статьи", callback_data="all_articles")],
        [InlineKeyboardButton(text="🇯🇵 Найти статьи с Японии", callback_data="region:japan")],
        [InlineKeyboardButton(text="🇰🇷 Найти статьи с Кореи", callback_data="region:korea")],
        [InlineKeyboardButton(text="🇨🇳 Найти статьи с Китая", callback_data="region:china")],
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
