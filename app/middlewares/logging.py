from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from loguru import logger


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            logger.info(
                f"Message from {event.from_user.id} "
                f"(@{event.from_user.username or 'no_username'}): "
                f"'{event.text or '[non-text]'}'"
            )
        elif isinstance(event, CallbackQuery):
            logger.info(
                f"Callback from {event.from_user.id}: "
                f"'{event.data}'"
            )
        return await handler(event, data)
