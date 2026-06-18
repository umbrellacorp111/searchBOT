import aiohttp
from loguru import logger
from app.utils.cache import cache

HN_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"


async def fetch_hackernews() -> list[dict]:
    cache_key = "hackernews:top"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:
            async with session.get(HN_TOP_STORIES) as resp:
                if resp.status != 200:
                    logger.warning(f"HN top stories returned {resp.status}")
                    return []
                story_ids = await resp.json()

            stories = []
            for story_id in story_ids[:30]:
                try:
                    async with session.get(HN_ITEM.format(story_id)) as item_resp:
                        if item_resp.status != 200:
                            continue
                        item = await item_resp.json()
                        if not item or item.get("type") != "story" or not item.get("title"):
                            continue
                        stories.append(
                            {
                                "title": item.get("title", ""),
                                "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                                "source": "Hacker News",
                                "content": item.get("title", ""),
                                "country": "Global",
                                "language": "en",
                                "views": item.get("score", 0) * 100,
                                "likes": item.get("score", 0),
                                "comments": item.get("descendants", 0),
                                "shares": 0,
                                "mentions_count": 0,
                                "google_trends_score": 0,
                                "reddit_score": 0,
                                "author_followers": 0,
                            }
                        )
                except Exception as e:
                    logger.debug(f"HN item {story_id} error: {e}")

        await cache.set(cache_key, stories, ttl=900)
        logger.info(f"Fetched {len(stories)} stories from Hacker News")
        return stories
    except Exception as e:
        logger.error(f"Hacker News fetch failed: {e}")
        return []
