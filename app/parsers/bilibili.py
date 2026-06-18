import aiohttp
from loguru import logger
from app.utils.cache import cache

API_URL = "https://api.bilibili.com/x/web-interface/ranking/v2"


async def fetch_bilibili() -> list[dict]:
    cache_key = "bilibili:trending"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:
            async with session.get(
                API_URL,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Bilibili returned {resp.status}")
                    return []
                data = await resp.json()

        videos = data.get("data", {}).get("list", [])
        results = []
        for v in videos[:10]:
            stat = v.get("stat", {})
            results.append({
                "title": v.get("title", ""),
                "url": f"https://www.bilibili.com/video/{v.get('bvid', '')}",
                "source": "Bilibili",
                "content": v.get("desc", "")[:2000],
                "country": "China",
                "language": "zh",
                "views": stat.get("view", 0),
                "likes": stat.get("like", 0),
                "comments": stat.get("reply", 0),
                "shares": stat.get("share", 0),
                "mentions_count": 0,
                "google_trends_score": 0,
                "reddit_score": 0,
                "author_followers": stat.get("favorite", 0),
            })

        await cache.set(cache_key, results, ttl=1800)
        logger.info(f"Fetched {len(results)} videos from Bilibili")
        return results
    except Exception as e:
        logger.error(f"Bilibili fetch failed: {e}")
        return []
