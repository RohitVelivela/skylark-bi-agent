"""
Central configuration — reads from environment / .env file.
All other modules import from here instead of calling os.getenv directly.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Monday.com
    monday_api_token:     str = ""
    deals_board_id:       str = ""
    work_orders_board_id: str = ""

    # Groq
    groq_api_key: str = ""
    groq_model:   str = "llama-3.3-70b-versatile"

    # Agent
    agent_max_iterations: int = 8
    tool_item_limit:      int = 500   # max items to fetch from Monday.com per call
    context_item_limit:   int = 50    # max items passed back to the model

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Singleton — cached after first call."""
    return Settings()
