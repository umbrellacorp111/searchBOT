from typing import Optional
import feedparser
import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from app.utils.cache import cache

RSS_SOURCES = {
    "Allure": "https://www.allure.com/feed/rss",
    "Vogue": "https://www.vogue.com/feed/rss",
    "Cosmopolitan": "https://www.cosmopolitan.com/rss/all.xml/",
    "Refinery29": "https://www.refinery29.com/en-us/beauty/rss.xml",
    "WWD": "https://wwd.com/feed/",
    "Byrdie": "https://www.byrdie.com/feed",
    "Fashion Press Japan": "https://www.fashion-press.net/feed",
    "Fashionsnap": "https://www.fashionsnap.com/feed/",
    "Sina Fashion": "https://fashion.sina.com.cn/rss/",
    "Sohu Fashion": "https://www.sohu.com/rss/fashion.xml",
}


async def fetch_rss(source_name: str, url: str) -> list[dict]:
    cache_key = f"rss:{source_name}:{url}"
    cached = await cache.get(cache_key)
    if cached:
        logger.debug(f"RSS cache hit for {source_name}")
        return cached

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:
            async with session.get(url, headers={"User-Agent": "TrendAggregatorBot/1.0"}) as resp:
                if resp.status != 200:
                    logger.warning(f"RSS {source_name} returned {resp.status}")
                    return []
                text = await resp.text()

        feed = feedparser.parse(text)
        articles = []
        for entry in feed.entries[:10]:
            content_text = _extract_content(entry)
            articles.append(
                {
                    "title": entry.get("title", "No title"),
                    "url": entry.get("link", ""),
                    "source": source_name,
                    "content": content_text,
                }
            )
        await cache.set(cache_key, articles, ttl=600)
        logger.info(f"Fetched {len(articles)} articles from {source_name}")
        return articles
    except Exception as e:
        logger.error(f"Failed to fetch RSS {source_name}: {e}")
        return []


def _extract_content(entry: feedparser.FeedParserDict) -> str:
    content = ""
    if hasattr(entry, "content") and entry.content:
        content = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        content = entry.summary
    elif hasattr(entry, "description"):
        content = entry.description
    if content:
        try:
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            content = soup.get_text(separator="\n", strip=True)
        except Exception:
            pass
    return content[:5000]


async def fetch_all_rss() -> list[dict]:
    all_articles = []
    for name, url in RSS_SOURCES.items():
        articles = await fetch_rss(name, url)
        all_articles.extend(articles)
    logger.info(f"Total RSS articles fetched: {len(all_articles)}")
    return all_articles
