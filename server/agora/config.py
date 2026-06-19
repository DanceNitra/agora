"""Agora configuration — Pydantic BaseSettings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./agora.db"
    redis_url: str = "redis://localhost:6379/0"
    use_redis: bool = False
    tick_interval: int = 10
    max_agents: int = 30
    # Roleplay-cognition throttle (the tick-loop "thinking" is a 0-direct-value cost centre that
    # shares the flash rate-limit with the value-producing organs). think_pct = fraction of ticks
    # on which agents think at all; agents_per_tick = how many think when they do. Lowering either
    # frees flash budget for research/replication/prediction. 1.0 + 2 reproduces the old behaviour.
    roleplay_think_pct: float = 0.5
    roleplay_agents_per_tick: int = 1
    # When False, the tick-loop roleplay uses FREE canned SIMULATED_THOUGHTS instead of a per-agent
    # LLM call. The agents still "think" every tick (trust/ESS/stigmergy updates via
    # _process_agent_thought are preserved), but the metered 'agent-think' organ (1.7M tok / value 0 —
    # generic flavor like "Analyzing trace patterns") stops growing. The dungeon characters' REAL
    # cognition (AgentOS._think = agent-dialogue) and all research organs are untouched. Set True to
    # restore LLM-generated roleplay flavor.
    roleplay_use_llm: bool = False
    debug: bool = True
    api_key: str = ""
    api_base_url: str = "https://api.deepseek.com/v1"
    llm_model_cheap: str = "deepseek-v4-flash"
    llm_model_medium: str = "deepseek-v4-flash"
    llm_model_expert: str = "deepseek-v4-flash"
    llm_model: str = ""   # single override for ALL tiers (AGORA_LLM_MODEL)
    # Reasoning-tier (medium/expert) override: route ONLY the low-volume reasoning calls to a
    # separate endpoint+model (e.g. glm-5.2 via the local Ollama cloud-route), while the high-volume
    # cheap tier stays on api_base_url. Set AGORA_REASONING_BASE_URL + AGORA_REASONING_MODEL to enable.
    reasoning_base_url: str = ""
    reasoning_model: str = ""
    reasoning_key: str = "local"
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
