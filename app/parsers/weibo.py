import aiohttp
from loguru import logger
from app.utils.cache import cache

HOT_URL = "https://m.weibo.cn/api/container/getIndex?containerid=106003&filter_type=realtimehot"


async def fetch_weibo() -> list[dict]:
    cache_key = "weibo:hot"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:
            async with session.get(
                HOT_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://m.weibo.cn/",
                },
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Weibo returned {resp.status}")
                    return []
                data = await resp.json()

        cards = data.get("data", {}).get("cards", [])
        results = []
        for card in cards:
            card_group = card.get("card_group", [])
            for item in card_group[:10]:
                title = item.get("desc", "") or item.get("word", "")
                if not title:
                    continue
                link = item.get("scheme", "") or f"https://s.weibo.com/weibo?q={title}"
                raw_hot = item.get("raw_hot", 0) or item.get("hot", 0)
                results.append({
                    "title": title,
                    "url": link,
                    "source": "Weibo",
                    "content": f"Hot topic on Weibo: {title}",
                    "country": "China",
                    "language": "zh",
                    "views": raw_hot * 1000 if raw_hot else 0,
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                    "mentions_count": raw_hot or 0,
                    "google_trends_score": 0,
                    "reddit_score": 0,
                    "author_followers": 0,
                })

        await cache.set(cache_key, results, ttl=1800)
        logger.info(f"Fetched {len(results)} topics from Weibo")
        return results
    except Exception as e:
        logger.error(f"Weibo fetch failed: {e}")
        return []
