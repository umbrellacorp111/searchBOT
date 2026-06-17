import sys
from loguru import logger
from app.config import settings


def setup_logger() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    logger.add(
        "logs/trends_bot_{time:YYYY-MM-DD}.log",
        level="INFO",
        rotation="1 day",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
    logger.info("Logger initialized")
