import sys
import os

_file = os.path.abspath(__file__)
_possible_roots = [
    os.path.dirname(os.path.dirname(_file)),
    os.path.dirname(_file),
    os.getcwd(),
]
for _p in _possible_roots:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from typing import Optional
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

_bot_instance: Optional[Bot] = None


def get_bot(token: Optional[str] = None) -> Bot:
    global _bot_instance
    if _bot_instance is not None:
        return _bot_instance
    if token:
        _bot_instance = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode="HTML"),
        )
        return _bot_instance
    try:
        from app.config import settings
    except ModuleNotFoundError:
        try:
            from config import settings
        except ModuleNotFoundError:
            raise RuntimeError(
                "Cannot import settings. Ensure project root is in PYTHONPATH."
            )
    _bot_instance = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    return _bot_instance


bot = get_bot()
