from loguru import logger
from app.config import settings

TREND_CATEGORIES = {
    "beauty": "Beauty",
    "fashion": "Fashion",
    "skincare": "Beauty",
    "makeup": "Beauty",
    "health": "Lifestyle",
    "tech": "Technology",
    "ai": "AI",
    "marketing": "Marketing",
    "e-commerce": "E-Commerce",
    "social": "Social Media",
    "startup": "Startups",
    "science": "Science",
    "culture": "Culture",
    "lifestyle": "Lifestyle",
    "k-beauty": "K-Beauty",
    "j-beauty": "J-Beauty",
    "c-beauty": "C-Beauty",
}


def detect_category(title: str, content: str = "") -> str:
    text = (title + " " + content).lower()
    for keyword, cat in TREND_CATEGORIES.items():
        if keyword in text:
            return cat
    return "Trends"


def detect_country(source: str, title: str = "", content: str = "") -> str:
    text = (title + " " + content).lower()
    if any(w in text for w in ["korea", "k-beauty", "korean", "kpop", "seoul"]):
        return "Korea"
    if any(w in text for w in ["japan", "j-beauty", "japanese", "tokyo"]):
        return "Japan"
    if any(w in text for w in ["china", "c-beauty", "chinese", "beijing", "shanghai"]):
        return "China"
    if source in (
        "Fashion Press Japan", "Fashionsnap", "Tokyo Beauty Book",
    ) or source.startswith("reddit/r/japan"):
        return "Japan"
    if source in ("Fifty Shades of Snail", "Christinahello") or source.startswith(
        "reddit/r/K"
    ):
        return "Korea"
    if source in ("Sina Fashion", "Sohu Fashion") or source.startswith("reddit/r/China"):
        return "China"
    return "Global"


def detect_language(source: str) -> str:
    if source in (
        "Fashion Press Japan", "Fashionsnap", "Tokyo Beauty Book",
    ) or source.startswith("reddit/r/japan"):
        return "en"
    if source in ("Fifty Shades of Snail", "Christinahello"):
        return "en"
    return "en"


def calculate_viral_score(metrics: dict) -> int:
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

    if views >= 1000000:
        score += 25
    elif views >= 100000:
        score += 20
    elif views >= 10000:
        score += 15
    elif views >= 1000:
        score += 10
    elif views >= 100:
        score += 5

    total_engagement = likes + comments + shares
    if total_engagement >= 10000:
        score += 25
    elif total_engagement >= 1000:
        score += 20
    elif total_engagement >= 100:
        score += 15
    elif total_engagement >= 10:
        score += 8

    if likes > 0 and views > 0:
        ratio = likes / max(views, 1)
        if ratio > 0.1:
            score += 10
        elif ratio > 0.05:
            score += 5

    if comments >= 500:
        score += 15
    elif comments >= 100:
        score += 10
    elif comments >= 10:
        score += 5

    if shares >= 1000:
        score += 10
    elif shares >= 100:
        score += 5

    if reddit_score >= 1000:
        score += 15
    elif reddit_score >= 100:
        score += 10
    elif reddit_score >= 10:
        score += 5

    if google_trends >= 80:
        score += 20
    elif google_trends >= 50:
        score += 12
    elif google_trends >= 20:
        score += 5

    if source_count >= 5:
        score += 15
    elif source_count >= 3:
        score += 10
    elif source_count >= 2:
        score += 5

    if mentions >= 100:
        score += 10
    elif mentions >= 10:
        score += 5

    if author_followers >= 100000:
        score += 5

    final_score = min(100, int(score))
    logger.debug(f"Viral Score calculated: {final_score} from {metrics}")
    return final_score
