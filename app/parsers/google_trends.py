from typing import Optional
from loguru import logger
from app.utils.cache import cache

try:
    from pytrends.request import TrendReq

    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


async def fetch_google_trends() -> list[dict]:
    if not PYTRENDS_AVAILABLE:
        logger.warning("pytrends not installed, skipping Google Trends")
        return []

    cache_key = "google_trends:daily"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    try:
        trends = await _fetch_trends()
        await cache.set(cache_key, trends, ttl=1800)
        return trends
    except Exception as e:
        logger.error(f"Google Trends fetch failed: {e}")
        return []


async def _fetch_trends() -> list[dict]:
    def _sync_fetch():
        pytrends = TrendReq(hl="en-US", tz=0, timeout=15)
        trending = pytrends.trending_searches(pn="united_states")
        if trending is None or trending.empty:
            return []
        results = []
        for title in trending[0].tolist()[:10]:
            results.append(
                {
                    "title": title,
                    "url": f"https://www.google.com/search?q={title.replace(' ', '+')}",
                    "source": "Google Trends",
                    "content": f"Trending search: {title}",
                    "country": "Global",
                    "language": "en",
                    "views": 0,
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                    "mentions_count": 0,
                    "google_trends_score": 80,
                    "reddit_score": 0,
                    "author_followers": 0,
                }
            )
        return results

    import asyncio

    return await asyncio.to_thread(_sync_fetch)
