"""Model router for selecting LLM tiers based on task complexity and cost."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TierConfig:
    name: str
    model: str
    cost_per_token: float  # USD per token (approximate)
    description: str


DEFAULT_TIERS = [
    TierConfig(
        name="cheap",
        model="deepseek-v4-flash",
        cost_per_token=0.000_000_15,
        description="Fast, low-cost model for simple queries and classification.",
    ),
    TierConfig(
        name="medium",
        model="deepseek-v4",
        cost_per_token=0.000_000_60,
        description="Balanced model for general reasoning tasks.",
    ),
    TierConfig(
        name="expert",
        model="deepseek-v4-ultra",
        cost_per_token=0.000_003_00,
        description="Highest-quality model for complex reasoning and codegen.",
    ),
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

    def estimate_cost(
        self, tier_name: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate the USD cost for a given tier and token counts.

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
