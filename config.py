import os
from typing import List, Optional, Union
from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    # Telegram API settings (used by Telethon StringSession, replace with real values later)
    TG_API_ID: int = 12345
    TG_API_HASH: str = "your_api_hash"
    TG_SESSION_STRING: str = "" # Optional init
    
    # Bot token fallback / publishing
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHANNEL_ID: str = "@gg_times"
    TG_SOURCE_CHANNELS: str = "@some_gaming_channel"

    # Reddit Settings
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "ContentFactory/2.0"
    REDDIT_SUBREDDITS: str = "gaming,Games"

    # LLM Settings
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    
    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/content_factory"

    # Processing Settings
    DEDUPLICATION_THRESHOLD: float = 0.15  # Cosine distance
    LLM_TIMEOUT: int = 15

    @property
    def get_source_channels(self) -> List[str]:
        return [x.strip() for x in self.TG_SOURCE_CHANNELS.split(",") if x.strip()]

    @property
    def get_subreddits(self) -> List[str]:
        return [x.strip() for x in self.REDDIT_SUBREDDITS.split(",") if x.strip()]

config = Settings()
