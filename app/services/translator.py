from typing import Optional
from loguru import logger
from app.utils.cache import cache


try:
    from googletrans import Translator as GoogleTranslator

    GT_AVAILABLE = True
except ImportError:
    GT_AVAILABLE = False


_gt_instance: Optional["GoogleTranslator"] = None


def _get_gt():
    global _gt_instance
    if GT_AVAILABLE and _gt_instance is None:
        _gt_instance = GoogleTranslator()
    return _gt_instance


async def fallback_translate(text: str) -> Optional[str]:
    if not text:
        return None
    cache_key = f"fallback_translate:{hash(text[:200])}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    translator = _get_gt()
    if not translator:
        logger.warning("GoogleTranslate not available for fallback")
        return None

    try:
        result = await translator.translate(text[:5000], src="en", dest="ru")
        translated = result.text if result else None
        if translated:
            await cache.set(cache_key, translated, ttl=3600)
            logger.info("Fallback translation completed")
        return translated
    except Exception as e:
        logger.error(f"Fallback translation failed: {e}")
        return None


async def is_english(text: str) -> bool:
    if not text:
        return True
    latin_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    total_chars = sum(1 for c in text if c.isalpha())
    if total_chars == 0:
        return True
    return latin_chars / total_chars > 0.8
