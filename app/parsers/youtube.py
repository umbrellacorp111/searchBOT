from loguru import logger
from app.config import settings
from app.utils.cache import cache

try:
    from googleapiclient.discovery import build

    YT_AVAILABLE = True
except ImportError:
    YT_AVAILABLE = False


async def fetch_youtube_trending() -> list[dict]:
    if not settings.youtube_api_key:
        logger.debug("No YouTube API key configured, skipping")
        return []
    if not YT_AVAILABLE:
        logger.warning("google-api-python-client not installed, skipping YouTube")
        return []

    cache_key = "youtube:trending"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    try:
        results = await _fetch_trending()
        await cache.set(cache_key, results, ttl=1800)
        return results
    except Exception as e:
        logger.error(f"YouTube Trending fetch failed: {e}")
        return []


async def _fetch_trending() -> list[dict]:
    import asyncio

    def _sync():
        youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)
        request = youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode="US",
            maxResults=10,
        )
        response = request.execute()
        items = response.get("items", [])
        results = []
        for item in items:
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))
            results.append(
                {
                    "title": snippet.get("title", ""),
                    "url": f"https://www.youtube.com/watch?v={item.get('id')}",
                    "source": "YouTube",
                    "content": snippet.get("description", "")[:2000],
                    "country": "Global",
                    "language": "en",
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "shares": 0,
                    "mentions_count": 0,
                    "google_trends_score": 0,
                    "reddit_score": 0,
                    "author_followers": 0  # requires extra channels API call
                }
            )
        return results

    return await asyncio.to_thread(_sync)
