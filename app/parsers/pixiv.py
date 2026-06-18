import re
import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from app.utils.cache import cache

RANKING_URL = "https://www.pixiv.net/ranking.php?mode=daily&content=illust"


async def fetch_pixiv() -> list[dict]:
    cache_key = "pixiv:daily_ranking"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20)
        ) as session:
            async with session.get(
                RANKING_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Pixiv returned {resp.status}")
                    return []
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        results = []
        for section in soup.select("section.ranking-item")[:10]:
            anchor = section.select_one("a.work")
            if not anchor:
                continue
            illust_id = anchor.get("href", "").split("/")[-1]
            title_tag = section.select_one(".title")
            title = title_tag.text.strip() if title_tag else "No title"
            user_tag = section.select_one(".user")
            author = user_tag.text.strip() if user_tag else "Unknown"
            img_tag = section.select_one("img")
            content = f"Illustration by {author} on Pixiv"

            results.append({
                "title": title,
                "url": f"https://www.pixiv.net/en/artworks/{illust_id}",
                "source": "Pixiv",
                "content": content,
                "country": "Japan",
                "language": "en",
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "mentions_count": 0,
                "google_trends_score": 0,
                "reddit_score": 0,
                "author_followers": 0,
            })

        await cache.set(cache_key, results, ttl=1800)
        logger.info(f"Fetched {len(results)} illustrations from Pixiv")
        return results
    except Exception as e:
        logger.error(f"Pixiv fetch failed: {e}")
        return []
