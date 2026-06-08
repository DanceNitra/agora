"""Model router for selecting LLM tiers based on task complexity and cost.

All models are free via OpenRouter (Nemotron family from NVIDIA).
Zero cost — no API spending, no credit limits.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TierConfig:
    name: str
    model: str
    cost_per_token: float  # USD per token (0 for free models)
    description: str


import os as _os

# A single override model for every tier (e.g. deepseek-v4-flash via DeepSeek/Ollama).
# Set AGORA_LLM_MODEL to switch the whole stack off the free Nemotron tier.
_OVERRIDE = _os.environ.get("AGORA_LLM_MODEL", "").strip()
_CHEAP = _OVERRIDE or "nvidia/nemotron-3-nano-30b-a3b:free"
_BIG = _OVERRIDE or "nvidia/nemotron-3-ultra-550b-a55b:free"

# ── Model tiers (override-aware) ──
DEFAULT_TIERS = [
    TierConfig(name="cheap", model=_CHEAP, cost_per_token=0.0,
               description="Cheap tier — fast model for real-time NPC/brain dialogue."),
    TierConfig(name="medium", model=_BIG, cost_per_token=0.0,
               description="Medium tier — balanced reasoning."),
    TierConfig(name="expert", model=_BIG, cost_per_token=0.0,
               description="Expert tier — top quality for complex reasoning."),
]


class ModelRouter:
    """Routes tasks to the appropriate LLM tier based on complexity heuristics.

    The router analyses task properties (estimated tokens, required reasoning
    depth, tool usage) and selects the most cost-effective tier.
    """

    def __init__(self, tiers: Optional[list[TierConfig]] = None):
        self._tiers = {t.name: t for t in (tiers or DEFAULT_TIERS)}

    def select_tier(
        self,
        estimated_tokens: int = 0,
        requires_reasoning: bool = False,
        requires_codegen: bool = False,
        uses_tools: bool = False,
        priority: Optional[str] = None,
    ) -> TierConfig:
        """Select the most appropriate model tier for a task.

        Heuristics (overridable by explicit *priority*):
          - cheap:   < 200 tokens, no reasoning, no tools, no codegen
          - medium:  < 2000 tokens or light reasoning or tool use
          - expert:  >= 2000 tokens or heavy reasoning or codegen

        Args:
            estimated_tokens: Estimated token count for input + output.
            requires_reasoning: Whether multi-step reasoning is needed.
            requires_codegen: Whether code generation is involved.
            uses_tools: Whether tool calling is used.
            priority: Explicit override ("cheap", "medium", "expert").

        Returns:
            The selected TierConfig.
        """
        if priority and priority in self._tiers:
            return self._tiers[priority]

        # Expert tier conditions
        if (
            estimated_tokens >= 2000
            or requires_codegen
            or (requires_reasoning and estimated_tokens >= 500)
        ):
            return self._tiers["expert"]

        # Medium tier conditions
        if (
            estimated_tokens >= 200
            or requires_reasoning
            or uses_tools
        ):
            return self._tiers["medium"]

        # Default to cheap
        return self._tiers["cheap"]

    def get_fallback_chain(self, tier_name: str) -> list[TierConfig]:
        """Return fallback chain: started tier → next cheaper tier(s).

        If the primary tier fails, fall back down the chain so that
        even degraded service keeps working.
        """
        order = ["expert", "medium", "cheap"]
        try:
            idx = order.index(tier_name)
        except ValueError:
            return [self._tiers.get(tier_name, self._tiers["cheap"])]
        chain = [self._tiers[o] for o in order[idx:] if o in self._tiers]
        return chain if chain else [self._tiers["cheap"]]

    def estimate_cost(
        self, tier_name: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate the USD cost for a given tier and token counts.

        All tiers are $0 (free models), but this method exists for
        future paid-model compatibility.

        Args:
            tier_name: One of "cheap", "medium", "expert".
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        tier = self._tiers.get(tier_name)
        if tier is None:
            raise ValueError(f"Unknown tier: {tier_name!r}")
        total_tokens = input_tokens + output_tokens
        return round(total_tokens * tier.cost_per_token, 8)

    def list_tiers(self) -> list[TierConfig]:
        """Return all configured tiers."""
        return list(self._tiers.values())
