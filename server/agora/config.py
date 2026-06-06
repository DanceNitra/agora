"""Agora configuration — Pydantic BaseSettings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agora"
    redis_url: str = "redis://localhost:6379/0"
    tick_interval: int = 30
    max_agents: int = 30
    debug: bool = True

    model_config = {"env_prefix": "AGORA_"}


settings = Settings()
