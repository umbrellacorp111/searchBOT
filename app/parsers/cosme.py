import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from app.utils.cache import cache

RANKING_URL = "https://www.cosme.net/ranking"


async def fetch_cosme() -> list[dict]:
    cache_key = "cosme:ranking"
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
                    "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
                },
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"@cosme returned {resp.status}")
                    return []
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        results = []
        for item in soup.select(".rankingItem, .item, .ranking-item")[:10]:
            title_tag = item.select_one("a, .title, .itemName")
            if not title_tag:
                continue
            title = title_tag.text.strip()
            link = title_tag.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.cosme.net{link}"
            brand_tag = item.select_one(".brand, .brandName")
            brand = brand_tag.text.strip() if brand_tag else ""
            content = f"Beauty product: {title}"
            if brand:
                content += f" by {brand}"

            results.append({
                "title": title,
                "url": link or "https://www.cosme.net/ranking",
                "source": "@cosme",
                "content": content,
                "country": "Japan",
                "language": "ja",
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
        logger.info(f"Fetched {len(results)} items from @cosme")
        return results
    except Exception as e:
        logger.error(f"@cosme fetch failed: {e}")
        return []
