import aiohttp
from loguru import logger
from app.config import settings
from app.utils.cache import cache

PH_API = "https://api.producthunt.com/v2/api/graphql"

QUERY = """
{
  posts(first: 20, order: VOTES) {
    edges {
      node {
        id
        name
        tagline
        url
        votesCount
        commentsCount
        reviewsCount
        website
        createdAt
      }
    }
  }
}
"""


async def fetch_producthunt() -> list[dict]:
    if not settings.producthunt_token:
        logger.debug("No Product Hunt token configured, skipping")
        return []

    cache_key = "producthunt:top"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    headers = {
        "Authorization": f"Bearer {settings.producthunt_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:
            async with session.post(
                PH_API, json={"query": QUERY}, headers=headers
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Product Hunt returned {resp.status}")
                    return []
                data = await resp.json()

        posts = data.get("data", {}).get("posts", {}).get("edges", [])
        results = []
        for edge in posts:
            node = edge.get("node", {})
            results.append(
                {
                    "title": node.get("name", ""),
                    "url": node.get("url", ""),
                    "source": "Product Hunt",
                    "content": node.get("tagline", ""),
                    "country": "Global",
                    "language": "en",
                    "views": node.get("votesCount", 0) * 50,
                    "likes": node.get("votesCount", 0),
                    "comments": node.get("commentsCount", 0),
                    "shares": node.get("reviewsCount", 0),
                    "mentions_count": 0,
                    "google_trends_score": 0,
                    "reddit_score": 0,
                    "author_followers": 0,
                }
            )

        await cache.set(cache_key, results, ttl=1800)
        logger.info(f"Fetched {len(results)} products from Product Hunt")
        return results
    except Exception as e:
        logger.error(f"Product Hunt fetch failed: {e}")
        return []
