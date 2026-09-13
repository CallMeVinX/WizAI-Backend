"""Application configuration using pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/wizzai_leads"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000"

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 25
    MAX_PAGE_SIZE: int = 100

    # Deduplication thresholds
    DEDUPE_CONFIDENCE_THRESHOLD: float = 0.6
    DEDUPE_LLM_THRESHOLD: float = 0.8
    DEDUPE_LLM_MAX_PAIRS: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()

