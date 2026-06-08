"""Agora configuration — Pydantic BaseSettings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./agora.db"
    redis_url: str = "redis://localhost:6379/0"
    use_redis: bool = False
    tick_interval: int = 10
    max_agents: int = 30
    debug: bool = True
    api_key: str = ""
    api_base_url: str = "https://api.deepseek.com/v1"
    llm_model_cheap: str = "deepseek-v4-flash"
    llm_model_medium: str = "deepseek-v4-flash"
    llm_model_expert: str = "deepseek-v4-flash"
    llm_model: str = ""   # single override for ALL tiers (AGORA_LLM_MODEL)
    llm_enabled: bool = True
    # OpenRouter-specific
    openrouter_key: str = ""
    openrouter_referer: str = "https://github.com/DanceNitra/agora"
    # VaultBridge — Obsidian "second brain" (local clone of the private repo)
    vault_path: str = ""
    vault_git_ssh_key: str = ""

    model_config = {"env_prefix": "AGORA_", "env_file": ".env", "extra": "ignore"}

    @property
    def llm_api_key(self) -> str:
        """Return the appropriate API key based on base_url."""
        if "openrouter" in self.api_base_url:
            return self.openrouter_key or self.api_key
        return self.api_key


settings = Settings()
