from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import Field


class Settings(BaseSettings):
    bot_token: str = Field(validation_alias="BOT_TOKEN")
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/trends.db",
        validation_alias="DATABASE_URL",
    )
    openai_model: str = Field(default="gpt-4o", validation_alias="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=2000, validation_alias="OPENAI_MAX_TOKENS")
    owner_id: int = Field(default=0, validation_alias="OWNER_ID")
    channel_id: Optional[int] = Field(default=None, validation_alias="CHANNEL_ID")
    log_level: str = Field(default="DEBUG", validation_alias="LOG_LEVEL")

    reddit_client_id: Optional[str] = Field(default=None, validation_alias="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(default=None, validation_alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(
        default="GlobalTrendHunter/1.0",
        validation_alias="REDDIT_USER_AGENT",
    )

    youtube_api_key: Optional[str] = Field(default=None, validation_alias="YOUTUBE_API_KEY")
    producthunt_token: Optional[str] = Field(default=None, validation_alias="PRODUCTHUNT_TOKEN")

    fetch_interval_minutes: int = Field(
        default=15, validation_alias="FETCH_INTERVAL_MINUTES"
    )
    analyze_interval_minutes: int = Field(
        default=10, validation_alias="ANALYZE_INTERVAL_MINUTES"
    )
    publish_interval_minutes: int = Field(
        default=10, validation_alias="PUBLISH_INTERVAL_MINUTES"
    )
    max_articles_per_fetch: int = Field(
        default=10, validation_alias="MAX_ARTICLES_PER_FETCH"
    )
    min_viral_score: int = Field(
        default=50, validation_alias="MIN_VIRAL_SCORE"
    )

    use_redis_cache: bool = Field(default=False, validation_alias="USE_REDIS_CACHE")
    redis_url: Optional[str] = Field(default=None, validation_alias="REDIS_URL")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
