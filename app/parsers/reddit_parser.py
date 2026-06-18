import asyncio
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
    "KoreanBeauty",
    "Makeup",
    "HaircareScience",
    "Fashion",
    "KpopFashion",
    "japanesebeauty",
    "JapaneseFashion",
    "JBeauty",
    "ChinaFashion",
    "ChineseBeauty",
    "technology",
    "artificial",
    "Futurology",
    "marketing",
    "startups",
    "Entrepreneur",
    "Productivity",
    "LifeProTips",
    "science",
    "Health",
    "Fitness",
    "Supplements",
    "Nootropics",
    "Biohackers",
]


async def fetch_reddit_posts(subreddit: str, limit: int = 10) -> list[dict]:
    cache_key = f"reddit:{subreddit}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    headers = {
        "User-Agent": settings.reddit_user_agent,
    }

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20)
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

            ups = post_data.get("ups", 0) or 0
            comments = post_data.get("num_comments", 0) or 0
            awards = post_data.get("total_awards_received", 0) or 0
            subreddit_subs = post_data.get("subreddit_subscribers", 0) or 0

            reddit_score = ups + comments * 2 + awards * 10
            likes_estimate = ups if ups > 0 else 0
            views_estimate = max(ups * 10, subreddit_subs // 100)

            articles.append(
                {
                    "title": post_data.get("title", "No title"),
                    "url": f"https://reddit.com{post_data.get('permalink', '')}",
                    "source": f"reddit/r/{subreddit}",
                    "content": (post_data.get("selftext", "") or "")[:5000]
                    or post_data.get("title", ""),
                    "country": "Global",
                    "language": "en",
                    "views": views_estimate,
                    "likes": likes_estimate,
                    "comments": comments,
                    "shares": awards,
                    "mentions_count": 0,
                    "google_trends_score": 0,
                    "reddit_score": reddit_score,
                    "author_followers": subreddit_subs,
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
        await asyncio.sleep(0.5)
    logger.info(f"Total Reddit posts fetched: {len(all_posts)}")
    return all_posts
