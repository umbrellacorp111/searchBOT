from typing import Optional
import aiohttp
from loguru import logger
from app.config import settings
from app.utils.cache import cache

SUBREDDITS = [
    "beauty",
    "AsianBeauty",
    "SkincareAddiction",
    "FemaleFashionAdvice",
    "Kbeauty",
    "Makeup",
    "HaircareScience",
    "Fashion",
]


async def fetch_reddit_posts(
    subreddit: str, limit: int = 10
) -> list[dict]:
    cache_key = f"reddit:{subreddit}"
    cached = await cache.get(cache_key)
    if cached:
        logger.debug(f"Reddit cache hit for r/{subreddit}")
        return cached

    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    headers = {
        "User-Agent": settings.reddit_user_agent,
    }
    if settings.reddit_client_id and settings.reddit_client_secret:
        headers["Authorization"] = (
            f"Basic {settings.reddit_client_id}:{settings.reddit_client_secret}"
        )

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"Reddit r/{subreddit} returned {resp.status}")
                    return []
                data = await resp.json()

        articles = []
        for post in data.get("data", {}).get("children", []):
            post_data = post.get("data", {})
            if post_data.get("stickied"):
                continue
            articles.append(
                {
                    "title": post_data.get("title", "No title"),
                    "url": f"https://reddit.com{post_data.get('permalink', '')}",
                    "source": f"reddit/r/{subreddit}",
                    "content": post_data.get("selftext", "")[:5000]
                    or post_data.get("title", ""),
                }
            )
        await cache.set(cache_key, articles, ttl=600)
        logger.info(f"Fetched {len(articles)} posts from r/{subreddit}")
        return articles
    except Exception as e:
        logger.error(f"Failed to fetch Reddit r/{subreddit}: {e}")
        return []


async def fetch_all_reddit() -> list[dict]:
    all_posts = []
    for sub in SUBREDDITS:
        posts = await fetch_reddit_posts(sub)
        all_posts.extend(posts)
    logger.info(f"Total Reddit posts fetched: {len(all_posts)}")
    return all_posts
