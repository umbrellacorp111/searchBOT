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

BLOCKED_PATTERNS = [
    r'\bgam(e|ing|er|ers|play)\b', r'\besports\b',
    r'\bpolitic(s|al|ian)\b', r'\belection\b',
    r'\bcryptocurrency\b', r'\bbitcoin\b', r'\bether(eum)?\b', r'\bnft(s)?\b', r'\bblockchain\b',
    r'\bpress.release\b', r'\bquarterly.result\b', r'\bstartup.rais(e|es|ed)\b',
    r'\bfunding.round\b', r'\bacquisit(ion|ed)\b',
    r'\bsport(s)?\b', r'\bnfl\b', r'\bnba\b', r'\bmlb\b', r'\bnhl\b',
    r'\bsoccer\b', r'\bfootball\b', r'\bbasketball\b',
    r'\bcorporate\b', r'\binvestor\b', r'\bstock\b', r'\brevenue\b',
    r'\bapi\b', r'\bsoftware.update\b', r'\bversion.\d+',
]

HIGH_VISUAL_SOURCES = [
    "YouTube", "Pixiv", "Bilibili", "Pinterest", "TikTok",
    "Instagram", "Xiaohongshu", "Douyin", "@cosme",
]

PINTEREST_SOURCES = ["Pinterest", "TikTok", "Instagram", "Pixiv", "Bilibili", "YouTube", "@cosme"]

PIN_SAVE_KEYWORDS = [
    "ideas", "inspo", "inspiration", "aesthetic", "outfit", "look", "style",
    "routine", "tips", "tutorial", "haul", "collection", "decor", "diy",
    "how to", "guide", "best", "top", "trending", "viral", "must have",
    "wishlist", "favorite", "amazon find", "essentials", "capsule",
    "minimalist", "mood board", "color palette",
]

VIRAL_KEYWORDS = [
    "viral", "trending", "everyone", "obsessed", "love this", "need this",
    "game changer", "holy grail", "must have", "hack", "secret",
    "tik tok made me buy", "amazon must have",
]

NOVELTY_KEYWORDS = [
    "new", "trending", "just dropped", "latest", "this season",
    "spring", "summer", "fall", "winter", "just launched",
    "new in", "fresh", "emerging", "next big", "upcoming", "2025", "2026",
]


def is_blocked(title: str, content: str) -> bool:
    text = (title + " " + content).lower()
    return sum(1 for p in BLOCKED_PATTERNS if re.search(p, text)) >= 2


def has_visual(source: str, content: str) -> bool:
    if any(s in source for s in HIGH_VISUAL_SOURCES):
        return True
    return bool(
        re.search(r'<img[^>]+>', content) or
        re.search(r'\.(jpg|jpeg|png|gif|webp|mp4)', content) or
        "photo" in content.lower() or "video" in content.lower() or "image" in content.lower()
    )


def visual_appeal(source: str, content: str, views: int) -> int:
    s = 45 if any(s in source for s in HIGH_VISUAL_SOURCES) else 0
    if re.search(r'<img[^>]+>', content) or re.search(r'\.(jpg|jpeg|png|gif|webp)', content):
        s += 30
    if "video" in content.lower() or "photo" in content.lower() or "image" in content.lower():
        s += 10
    if views > 10000:
        s += 10
    if views > 100000:
        s += 5
    return min(100, s)


def pinterest_potential(source: str, title: str, content: str) -> int:
    s = 30 if any(s in source for s in PINTEREST_SOURCES) else 0
    if any(kw in title.lower() for kw in PIN_SAVE_KEYWORDS):
        s += 30
    if any(kw in content.lower() for kw in PIN_SAVE_KEYWORDS):
        s += 20
    if re.search(r'\.(jpg|jpeg|png|gif|webp)', content):
        s += 20
    return min(100, s)


def save_potential(source: str, title: str, content: str) -> int:
    s = 0
    if any(kw in source.lower() for kw in ["tiktok", "instagram", "youtube", "pinterest"]):
        s += 25
    if any(kw in title.lower() for kw in PIN_SAVE_KEYWORDS):
        s += 25
    if any(kw in content.lower() for kw in PIN_SAVE_KEYWORDS):
        s += 15
    if "photo" in content.lower() or "video" in content.lower():
        s += 10
    return min(100, s)


def repost_potential(source: str, title: str, content: str) -> int:
    s = 25 if any(kw in source.lower() for kw in ["tiktok", "instagram", "youtube", "pinterest"]) else 0
    if any(kw in title.lower() for kw in VIRAL_KEYWORDS):
        s += 25
    if any(kw in content.lower() for kw in VIRAL_KEYWORDS):
        s += 15
    return min(100, s)


def novelty_score(title: str, content: str) -> int:
    text = (title + " " + content).lower()
    return min(100, sum(1 for kw in NOVELTY_KEYWORDS if kw in text) * 15)


def global_spread(source: str, country: str, title: str, content: str) -> int:
    text = (title + " " + content).lower()
    s = 0
    if country in ("USA", "UK", "Global"):
        s += 30
    if any(kw in text for kw in ["korea", "japan", "china", "france", "paris", "london", "new york"]):
        s += 25
    if any(kw in text for kw in ["trending", "viral", "global", "worldwide"]):
        s += 15
    return min(100, s + 30)


def russia_rarity(title: str, content: str) -> int:
    text = (title + " " + content).lower()
    cyrillic = len(re.findall(r'[а-яё]', text))
    if cyrillic > 20:
        return 10
    if any(kw in text for kw in ["россия", "росси", "русский", "рф", "москва"]):
        return 20
    return 90


def check_russian_gap(title: str, content: str) -> int:
    return russia_rarity(title, content)


def calculate_content_score(metrics: dict, title: str = "", content: str = "") -> int:
    if is_blocked(title, content):
        logger.debug(f"Blocked: {title[:60]}")
        return 0

    source = metrics.get("source", "")
    views = metrics.get("views", 0) or 0
    likes = metrics.get("likes", 0) or 0
    comments = metrics.get("comments", 0) or 0
    country = metrics.get("country", "")

    vis = visual_appeal(source, content, views)
    pin = pinterest_potential(source, title, content)
    save = save_potential(source, title, content)
    rep = repost_potential(source, title, content)
    nov = novelty_score(title, content)
    glob = global_spread(source, country, title, content)
    rare = russia_rarity(title, content)

    score = vis * 0.30 + pin * 0.20 + save * 0.15 + rep * 0.10 + nov * 0.10 + glob * 0.10 + rare * 0.05

    # Text-only penalty: -40%
    if not has_visual(source, content):
        score *= 0.6
        logger.debug(f"Text penalty for {source}: {title[:50]}")

    final = max(0, min(100, int(round(score))))
    logger.debug(f"Score: {final} | vis={vis} pin={pin} save={save} rep={rep} nov={nov} glob={glob} rare={rare}")
    return final


def detect_category(title: str, content: str = "") -> str:
    text = (title + " " + content).lower()
    cats = [
        ("luxury", ["luxury", "designer", "hermes", "chanel", "gucci", "prada", "louis vuitton", "dior", "premium", "exclusive"], "Luxury"),
        ("celebrity", ["celebrity", "red carpet", "met gala", "oscar", "grammy", "celebrity style", "celebrity beauty", "royal"], "Celebrity Fashion"),
        ("jewelry", ["jewelry", "jewellery", "necklace", "earring", "bracelet", "ring", "diamond", "gold", "silver", "watch"], "Jewelry"),
        ("handbags", ["handbag", "purse", "tote", "crossbody", "shoulder bag", "clutch", "designer bag", "it bag"], "Handbags"),
        ("shoes", ["shoe", "sneaker", "heel", "boot", "flat", "loafer", "sandals", "pumps"], "Shoes"),
        ("nails", ["nail", "manicure", "nail art", "nail design", "gel", "acrylic", "nail polish"], "Nail Trends"),
        ("makeup", ["makeup", "make.up", "lipstick", "foundation", "eyeshadow", "blush", "highlighter", "contour", "concealer", "eyeliner", "mascara", "lip gloss"], "Makeup Trends"),
        ("skincare", ["skincare", "skin care", "serum", "moisturizer", "cleanser", "sunscreen", "retinol", "vitamin c", "face mask", "toner", "essence", "cream"], "Skincare Trends"),
        ("hair", ["hair", "hairstyle", "hair color", "haircut", "hairstyling", "curly", "blowout", "braid"], "Hair Trends"),
        ("beauty", ["beauty", "cosmetic", "beauty product", "beauty routine", "beauty tip"], "Beauty"),
        ("fashion", ["fashion", "outfit", "style", "wear", "dress", "trendy", "street style", "ootd", "fashion week", "collection"], "Fashion"),
        ("home", ["home", "decor", "interior", "furniture", "room", "house", "garden", "storage", "organizing", "organization", "diy"], "Home Decor"),
        ("wedding", ["wedding", "bride", "bridal", "marriage", "engagement", "honeymoon", "wedding dress"], "Wedding Trends"),
        ("wellness", ["wellness", "health", "fitness", "yoga", "meditation", "selfcare", "self-care", "mental health"], "Wellness"),
        ("travel", ["travel", "trip", "vacation", "holiday", "destination", "hotel", "beach"], "Travel Ideas"),
        ("lifestyle", ["lifestyle", "life", "habit", "routine", "mom", "mother", "parent", "baby", "family", "relationship"], "Lifestyle"),
        ("viral", ["viral", "trending", "tiktok viral", "amazon find", "tiktok made me buy"], "Viral Products"),
        ("aesthetic", ["aesthetic", "mood board", "vibe", "coquette", "clean girl", "old money", "ballet core", "cottagecore", "vanilla girl", "that girl"], "Aesthetic Trends"),
    ]
    for _, kw, cat in cats:
        if any(k in text for k in kw):
            return cat
    return "Trends"


def detect_country(source: str, title: str = "", content: str = "") -> str:
    text = (title + " " + content).lower()
    for words, country in [
        (["korea", "k-beauty", "korean", "kpop", "seoul"], "Korea"),
        (["japan", "j-beauty", "japanese", "tokyo"], "Japan"),
        (["china", "c-beauty", "chinese", "beijing", "shanghai"], "China"),
        (["usa", "united states", "america", "new york", "la", "california"], "USA"),
        (["uk", "united kingdom", "london", "england", "britain"], "UK"),
        (["france", "paris", "french"], "France"),
        (["germany", "berlin", "german"], "Germany"),
    ]:
        if any(w in text for w in words):
            return country

    source_map = {
        "Fashion Press Japan": "Japan", "Fashionsnap": "Japan", "Tokyo Beauty Book": "Japan",
        "Pixiv": "Japan", "@cosme": "Japan",
        "Fifty Shades of Snail": "Korea", "Christinahello": "Korea",
        "Bilibili": "China", "Weibo": "China",
        "Sina Fashion": "China", "Sohu Fashion": "China",
        "Allure": "USA", "Vogue": "USA", "Cosmopolitan": "USA",
        "Refinery29": "USA", "WWD": "USA", "Byrdie": "USA",
    }
    if source in source_map:
        return source_map[source]
    if source.startswith("reddit/r/japan"):
        return "Japan"
    if source.startswith("reddit/r/China"):
        return "China"
    return "Global"


def detect_language(source: str) -> str:
    if source in ("Bilibili", "Weibo", "Sina Fashion", "Sohu Fashion"):
        return "zh"
    if source == "@cosme":
        return "ja"
    return "en"
