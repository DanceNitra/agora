"""Agora configuration — Pydantic BaseSettings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./agora.db"
    redis_url: str = "redis://localhost:6379/0"
    use_redis: bool = False
    tick_interval: int = 5
    max_agents: int = 30
    debug: bool = True
    api_key: str = ""
    api_base_url: str = "https://api.deepseek.com/v1"
    llm_model_cheap: str = "deepseek-v4-flash"
    llm_model_medium: str = "deepseek-v4-pro"
    llm_model_expert: str = "deepseek-v4-pro"
    llm_enabled: bool = True

    model_config = {"env_prefix": "AGORA_", "env_file": ".env"}


settings = Settings()
