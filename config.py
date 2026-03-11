import os
from typing import List, Optional
from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram Settings
    TG_API_ID: int
    TG_API_HASH: str
    TG_SESSION_STRING: str  # StringSession for auth
    TG_TARGET_CHANNEL: str  # Destination channel username or ID
    TG_SOURCE_CHANNELS: List[str]  # List of source channel usernames/IDs

    # Reddit Settings
    REDDIT_CLIENT_ID: str
    REDDIT_CLIENT_SECRET: str
    REDDIT_USER_AGENT: str = "ContentFactory/2.0"
    REDDIT_SUBREDDITS: List[str] = ["gaming", "Games"]

    # LLM Settings
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    
    # Database Settings
    DATABASE_URL: PostgresDsn

    # Processing Settings
    DEDUPLICATION_THRESHOLD: float = 0.15  # Cosine distance
    LLM_TIMEOUT: int = 15

    @field_validator("TG_SOURCE_CHANNELS", "REDDIT_SUBREDDITS", mode="before")
    @classmethod
    def split_csv(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",")]
        return v

config = Settings()
