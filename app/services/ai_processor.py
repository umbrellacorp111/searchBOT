import asyncio
import re
from typing import Optional
from loguru import logger
from app.config import settings
from app.utils.cache import cache
from app.services.ai.prompts import (
    TRANSLATE_PROMPT,
    SUMMARY_PROMPT,
    CATEGORY_PROMPT,
    TITLE_RU_PROMPT,
    TREND_ANALYSIS_PROMPT,
    AUDIENCE_FILTER_PROMPT,
    TRANSLATE_KO_PROMPT,
    TRANSLATE_JA_PROMPT,
    TRANSLATE_ZH_PROMPT,
)

_client_instance: Optional[object] = None

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


def get_client():
    global _client_instance
    if _client_instance is not None:
        return _client_instance
    try:
        from openai import AsyncOpenAI

        _client_instance = AsyncOpenAI(api_key=settings.openai_api_key)
    except Exception as e:
        logger.error(f"Failed to init OpenAI client: {e}")
        raise
    return _client_instance


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
            "Technology", "AI", "Marketing", "E-Commerce",
            "Social Media", "Startups", "Culture", "Science",
            "K-Beauty", "J-Beauty", "C-Beauty",
        }
        if result in valid:
            return result
        logger.warning(f"Invalid category: {result}")
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


async def is_relevant_for_audience(title: str, content: str) -> bool:
    text = content or title
    if not text or len(text.strip()) < 10:
        return True
    prompt = AUDIENCE_FILTER_PROMPT.format(title=title[:200], text=text[:1500])
    result = await _call_openai(prompt, max_tokens=10)
    if result:
        result = result.strip().upper()
        if result == "NO":
            logger.info(f"Audience filter rejected: {title[:60]}")
            return False
    return True


async def analyze_trend(title: str, content: str) -> dict:
    cache_key = f"trend_analysis:{hash(content[:500])}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    text = content or title
    text = text[:3000]
    prompt = TREND_ANALYSIS_PROMPT.format(title=title[:200], text=text)
    result = await _call_openai(prompt, max_tokens=1000)
    if not result:
        return {"trend_reason": "Не удалось выполнить анализ тренда."}

    parsed = {
        "trend_reason": _extract_field(result, "Почему это тренд"),
        "who_discusses": _extract_field(result, "Кто обсуждает"),
        "growth_speed": _extract_field(result, "Скорость роста"),
        "scope": _extract_field(result, "Локальный/Мировой"),
        "forecast": _extract_field(result, "Прогноз"),
        "market_impact": _extract_field(result, "Влияние на рынок"),
    }

    trend_reason_parts = []
    for key, label in [
        ("trend_reason", "Почему это тренд"),
        ("who_discusses", "Кто обсуждает"),
        ("growth_speed", "Скорость роста"),
        ("scope", "Локальный/Мировой"),
        ("forecast", "Прогноз"),
        ("market_impact", "Влияние на рынок"),
    ]:
        val = parsed.get(key, "")
        if val:
            trend_reason_parts.append(f"<b>{label}:</b> {val}")

    trend_reason = "\n".join(trend_reason_parts) if trend_reason_parts else result

    await cache.set(cache_key, {"trend_reason": trend_reason}, ttl=3600)
    return {"trend_reason": trend_reason}


def _extract_field(text: str, field_name: str) -> str:
    pattern = rf"{field_name}:\s*(.+?)(?:\n\n|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith(field_name + ":"):
            parts = []
            parts.append(line[len(field_name) + 1:].strip())
            for j in range(i + 1, len(lines)):
                if ":" in lines[j] and not lines[j].startswith(" "):
                    break
                if lines[j].strip():
                    parts.append(lines[j].strip())
            return " ".join(parts).strip()
    return ""


async def process_article(
    title: str,
    content: str,
    source: str,
    viral_score: int = 0,
) -> dict:
    cache_key = f"processed:{source}:{hash(content)}"
    cached = await cache.get(cache_key)
    if cached:
        logger.info(f"Cache hit for {source}")
        return cached

    text_to_process = content or title
    logger.info(f"Processing article from {source}: {title[:50]}...")

    if not await is_relevant_for_audience(title, text_to_process):
        result = {
            "title_ru": title,
            "translation": "Отфильтровано: не соответствует целевой аудитории.",
            "summary": "Контент не релевантен для молодой женской аудитории.",
            "trend_reason": "Discarded",
            "category": "Discarded",
            "source": source,
        }
        await cache.set(cache_key, result, ttl=3600)
        return result

    translation, summary, category, title_ru, trend_analysis = await asyncio.gather(
        translate_text(text_to_process, source),
        generate_summary(text_to_process),
        determine_category(text_to_process),
        generate_title_ru(text_to_process),
        analyze_trend(title, text_to_process),
    )

    result = {
        "title_ru": title_ru or title,
        "translation": translation or text_to_process[:500],
        "summary": summary or "Резюме не сгенерировано.",
        "trend_reason": trend_analysis.get("trend_reason", "Анализ не выполнен."),
        "category": category or "Trends",
        "source": source,
    }

    await cache.set(cache_key, result, ttl=3600)
    return result
