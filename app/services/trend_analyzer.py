import re
from loguru import logger

RUSSIAN_KEYWORDS = [
    "россия", "росси", "русский", "русск", "москва", "моск", "спб",
    "петербург", "рф", "руб", "российск",
]

RUSSIAN_DOMAINS = [
    ".ru", ".рф", "yandex", "vk.com", "mail.ru", "ozon", "wb.ru",
    "wildberries", "sber", "tinkoff",
]


def detect_category(title: str, content: str = "") -> str:
    text = (title + " " + content).lower()

    categories = [
        ("beauty", ["beauty", "skincare", "makeup", "cosmetic", "hair", "nail", "lip"],
         "Beauty"),
        ("fashion", ["fashion", "outfit", "style", "wear", "dress", "bag", "shoe",
                     "accessory", "trendy"], "Fashion"),
        ("home", ["home", "decor", "interior", "furniture", "room", "house",
                  "garden", "kitchen", "storage", "organizing", "organization", "diy"],
         "Home & Decor"),
        ("food", ["recipe", "cook", "food", "delicious", "meal", "baking",
                  "kitchen", "dinner", "lunch", "breakfast"], "Food & Recipes"),
        ("wedding", ["wedding", "bride", "bridal", "marriage", "engagement",
                     "honeymoon"], "Weddings"),
        ("wellness", ["wellness", "health", "fitness", "yoga", "meditation",
                      "selfcare", "self-care", "mental", "health"], "Wellness"),
        ("travel", ["travel", "trip", "vacation", "holiday", "destination",
                    "hotel", "beach"], "Travel"),
        ("tech", ["tech", "ai", "robot", "digital", "app", "software",
                  "startup", "gadget"], "Technology"),
        ("lifestyle", ["lifestyle", "life", "habit", "routine", "mom", "mother",
                       "parent", "baby", "family", "relationship"], "Lifestyle"),
    ]

    for _, keywords, cat in categories:
        for kw in keywords:
            if kw in text:
                return cat
    return "Trends"


def detect_country(source: str, title: str = "", content: str = "") -> str:
    text = (title + " " + content).lower()

    korea_words = ["korea", "k-beauty", "korean", "kpop", "seoul", "k beauty"]
    japan_words = ["japan", "j-beauty", "japanese", "tokyo", "j beauty"]
    china_words = ["china", "c-beauty", "chinese", "beijing", "shanghai", "c beauty"]
    us_words = ["usa", "united states", "america", "new york", "la", "los angeles",
                "california"]
    uk_words = ["uk", "united kingdom", "london", "england", "britain"]
    france_words = ["france", "paris", "french"]
    germany_words = ["germany", "berlin", "german"]

    if any(w in text for w in korea_words):
        return "Korea"
    if any(w in text for w in japan_words):
        return "Japan"
    if any(w in text for w in china_words):
        return "China"
    if any(w in text for w in us_words):
        return "USA"
    if any(w in text for w in uk_words):
        return "UK"
    if any(w in text for w in france_words):
        return "France"
    if any(w in text for w in germany_words):
        return "Germany"

    source_lower = source.lower()
    if source in (
        "Fashion Press Japan", "Fashionsnap", "Tokyo Beauty Book",
    ) or source.startswith("reddit/r/japan"):
        return "Japan"
    if source in ("Fifty Shades of Snail", "Christinahello"):
        return "Korea"
    if source.startswith("reddit/r/K") or source in ("reddit/r/AsianBeauty",):
        return "Korea"
    if source in ("Sina Fashion", "Sohu Fashion") or source.startswith("reddit/r/China"):
        return "China"
    if source in ("Allure", "Vogue", "Cosmopolitan", "Refinery29", "WWD", "Byrdie"):
        return "USA"
    if source == "BBC News" or source.startswith("reddit/r/CasualUK"):
        return "UK"

    return "Global"


def detect_language(source: str) -> str:
    if source in (
        "Fashion Press Japan", "Fashionsnap", "Tokyo Beauty Book",
    ) or source.startswith("reddit/r/japan"):
        return "en"
    if source in ("Fifty Shades of Snail", "Christinahello"):
        return "en"
    if source in ("Sina Fashion", "Sohu Fashion"):
        return "zh"
    return "en"


def check_russian_gap(title: str, content: str) -> int:
    """Returns 0-25 points: higher = less known in Russia (bigger opportunity)."""
    text = (title + " " + content).lower()

    russian_mention_count = 0
    for kw in RUSSIAN_KEYWORDS:
        russian_mention_count += len(re.findall(kw, text))

    domain_count = 0
    for domain in RUSSIAN_DOMAINS:
        if domain in text:
            domain_count += 1

    cyrillic_chars = len(re.findall(r'[а-яё]', text))
    has_cyrillic = cyrillic_chars > 20

    if russian_mention_count > 3 or domain_count > 2 or has_cyrillic:
        return 5
    if russian_mention_count > 0 or domain_count > 0:
        return 10
    if any(word in text for word in ["russian", "russia", "moscow"]):
        return 15

    return 25


def calculate_content_score(metrics: dict, title: str = "", content: str = "") -> int:
    score = 0.0

    views = metrics.get("views", 0) or 0
    likes = metrics.get("likes", 0) or 0
    comments = metrics.get("comments", 0) or 0
    shares = metrics.get("shares", 0) or 0
    mentions = metrics.get("mentions_count", 0) or 0
    source_count = metrics.get("source_count", 1) or 1
    reddit_score = metrics.get("reddit_score", 0) or 0
    google_trends = metrics.get("google_trends_score", 0) or 0
    author_followers = metrics.get("author_followers", 0) or 0

    source_name = metrics.get("source", "")
    is_visual_source = (
        source_name == "YouTube"
        or source_name.startswith("reddit/r/")
    )

    has_image_content = bool(
        re.search(r'<img[^>]+>', content) or
        re.search(r'\.(jpg|jpeg|png|gif|webp)', content) or
        "image" in (title + content).lower() or
        "photo" in (title + content).lower() or
        "video" in (title + content).lower() or
        "pic" in (title + content).lower()
    )

    visual_potential = 0
    if is_visual_source:
        visual_potential += 15
    if views > 0:
        visual_potential += 5
    if has_image_content:
        visual_potential += 10

    visual_score = min(30, visual_potential)
    score += visual_score

    if views >= 1000000:
        score += 20
    elif views >= 100000:
        score += 15
    elif views >= 10000:
        score += 10
    elif views >= 1000:
        score += 5

    total_engagement = likes + comments + shares
    if total_engagement >= 10000:
        score += 15
    elif total_engagement >= 1000:
        score += 10
    elif total_engagement >= 100:
        score += 5

    if comments >= 500:
        score += 10
    elif comments >= 100:
        score += 5

    if shares >= 1000:
        score += 5

    if reddit_score >= 1000:
        score += 10
    elif reddit_score >= 100:
        score += 5

    if google_trends >= 80:
        score += 15
    elif google_trends >= 50:
        score += 8
    elif google_trends >= 20:
        score += 3

    if source_count >= 3:
        score += 10
    elif source_count >= 2:
        score += 5

    if mentions >= 10:
        score += 5

    gap_score = check_russian_gap(title, content)
    score += gap_score

    final_score = min(100, int(score))
    logger.debug(f"Content Score: {final_score} | gap={gap_score} visual={visual_score}")
    return final_score
