import asyncio
from typing import Optional
from openai import AsyncOpenAI
from loguru import logger
from app.config import settings
from app.utils.cache import cache
from app.services.ai.prompts import (
    TRANSLATE_PROMPT,
    SUMMARY_PROMPT,
    CATEGORY_PROMPT,
    TITLE_RU_PROMPT,
    TRANSLATE_KO_PROMPT,
    TRANSLATE_JA_PROMPT,
    TRANSLATE_ZH_PROMPT,
)

client: Optional[AsyncOpenAI] = None

LANGUAGE_MAP = {
    "Naver Beauty": TRANSLATE_KO_PROMPT,
    "Beauty Korea": TRANSLATE_KO_PROMPT,
    "K-Beauty RSS": TRANSLATE_KO_PROMPT,
    "Fashion Press Japan": TRANSLATE_JA_PROMPT,
    "Fashionsnap": TRANSLATE_JA_PROMPT,
    "Yahoo Japan Beauty": TRANSLATE_JA_PROMPT,
    "Sina Fashion": TRANSLATE_ZH_PROMPT,
    "Xiaohongshu": TRANSLATE_ZH_PROMPT,
    "Sohu Fashion": TRANSLATE_ZH_PROMPT,
}


def get_client() -> AsyncOpenAI:
    global client
    if client is None:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
    return client


async def _call_openai(prompt: str, max_tokens: int = 1000) -> Optional[str]:
    retries = 3
    for attempt in range(retries):
        try:
            response = await get_client().chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"OpenAI call failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
    return None


async def _get_translate_prompt(source: str) -> str:
    return LANGUAGE_MAP.get(source, TRANSLATE_PROMPT)


async def translate_text(text: str, source: str) -> Optional[str]:
    if not text or len(text.strip()) < 10:
        return None
    text = text[:settings.openai_max_tokens]
    prompt_template = await _get_translate_prompt(source)
    prompt = prompt_template.format(text=text)
    result = await _call_openai(prompt, max_tokens=settings.openai_max_tokens)
    if result:
        logger.info(f"Translation completed for source={source} ({len(text)} chars)")
    return result


async def generate_summary(text: str) -> Optional[str]:
    if not text:
        return None
    text = text[:settings.openai_max_tokens]
    prompt = SUMMARY_PROMPT.format(text=text)
    return await _call_openai(prompt, max_tokens=600)


async def determine_category(text: str) -> Optional[str]:
    if not text:
        return None
    text = text[:2000]
    prompt = CATEGORY_PROMPT.format(text=text)
    result = await _call_openai(prompt, max_tokens=20)
    if result:
        result = result.strip()
        valid = {
            "Beauty", "Fashion", "Lifestyle", "Trends",
            "K-Beauty", "J-Beauty", "C-Beauty",
        }
        if result in valid:
            return result
        logger.warning(f"Invalid category returned: {result}, defaulting to Trends")
    return "Trends"


async def generate_title_ru(text: str) -> Optional[str]:
    if not text:
        return None
    text = text[:2000]
    prompt = TITLE_RU_PROMPT.format(text=text)
    result = await _call_openai(prompt, max_tokens=150)
    if result:
        result = result.strip().strip('"').strip("'")
        if len(result) > 120:
            result = result[:117] + "..."
    return result


async def process_article(
    title: str,
    content: str,
    source: str,
) -> dict:
    cache_key = f"processed:{source}:{hash(content)}"
    cached = await cache.get(cache_key)
    if cached:
        logger.info(f"Cache hit for processed article from {source}")
        return cached

    text_to_process = content or title
    logger.info(f"Processing article from {source}: {title[:50]}...")

    translation, summary, category, title_ru = await asyncio.gather(
        translate_text(text_to_process, source),
        generate_summary(text_to_process),
        determine_category(text_to_process),
        generate_title_ru(text_to_process),
    )

    result = {
        "title_ru": title_ru or title,
        "translation": translation or text_to_process,
        "summary": summary or "Резюме не сгенерировано.",
        "category": category or "Trends",
        "source": source,
    }

    await cache.set(cache_key, result, ttl=3600)
    return result
