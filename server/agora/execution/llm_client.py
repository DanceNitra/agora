"""Real LLM client for Agora agents with auto-fallback across tiers.

Uses OpenAI-compatible API (OpenRouter or DeepSeek).
Features:
  - Tier-based model selection (cheap / medium / expert)
  - Auto-fallback on provider error: expert → medium → cheap
  - Per-agent cost tracking (even for free models — future-proof)
  - Retry with backoff on 429 rate limits
  - Token counting for cost estimation
"""

import json
import time
from typing import Any, Optional

from openai import OpenAI

from agora.execution.model_router import ModelRouter

# Lazy imports to avoid circular deps
_settings = None
_router = None


def _get_settings():
    global _settings
    if _settings is None:
        from agora.config import settings
        _settings = settings
    return _settings


def _get_router():
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def _get_client(api_key: str, base_url: str) -> OpenAI:
    """Create an OpenAI-compatible client with the right headers."""
    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "base_url": base_url,
    }
    # OpenRouter needs a referer header
    if "openrouter" in base_url:
        kwargs["default_headers"] = {
            "HTTP-Referer": "https://github.com/DanceNitra/agora",
            "X-Title": "Agora Multi-Agent System",
        }
    return OpenAI(**kwargs)


def call_llm(
    system_prompt: str,
    user_prompt: str,
    tier: str = "cheap",
    temperature: float = 0.7,
    max_tokens: int = 500,
    response_format: Optional[dict] = None,
) -> str:
    """Call the LLM with auto-fallback across tiers.

    Tries the requested tier first. If it fails with a provider error
    (timeout, 429, 500), falls back to the next available tier.
    The chain is: expert → medium → cheap.

    Args:
        system_prompt: System-level instruction.
        user_prompt: User message content.
        tier: Model tier ("cheap", "medium", "expert").
        temperature: Sampling temperature (0.0-1.0).
        max_tokens: Max output tokens.
        response_format: Optional {"type": "json_object"}.

    Returns:
        Response text content, or error message if all tiers fail.
    """
    cfg = _get_settings()
    router = _get_router()

    api_key = cfg.llm_api_key
    base_url = cfg.api_base_url

    fallback_chain = router.get_fallback_chain(tier)

    errors = []
    for tier_cfg in fallback_chain:
        tier_name = tier_cfg.name
        model = tier_cfg.model

        # Build kwargs
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        # Retry loop per model (rate limit backoff)
        for attempt in range(2):
            try:
                client = _get_client(api_key, base_url)
                resp = client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""

                # Log successful fallback (so we know when it happens)
                if errors:
                    print(f"[LLM] Fallback: {tier} → {tier_name} ({model}) OK")

                return content

            except Exception as e:
                error_str = str(e)
                errors.append(f"{tier_name}({model}): {error_str[:100]}")

                # Rate limit — retry with backoff
                if "429" in error_str or "rate" in error_str.lower():
                    if attempt == 0:
                        time.sleep(2)
                        continue
                # Other provider errors — skip to next tier
                break

        # If we got here, this tier failed entirely
        print(f"[LLM] {tier_name}({model}) failed: {errors[-1][:80]}")

    # All tiers failed
    error_summary = "; ".join(errors[-3:])
    return f"[LLM Error: all tiers failed — {error_summary[:200]}]"


# ── Cost tracking ──────────────────────────────────────

class LLMCostTracker:
    """Tracks per-agent LLM usage for cost monitoring.

    Even with free models, tracking is useful for understanding
    usage patterns and being ready if you switch to paid models.
    """

    def __init__(self):
        self._calls: list[dict] = []
        self._agent_totals: dict[str, dict] = {}

    def record(
        self,
        agent_id: str,
        tier: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        duration_ms: int = 0,
        success: bool = True,
    ):
        """Record an LLM call for an agent."""
        record = {
            "agent_id": agent_id[:8],
            "tier": tier,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": time.time(),
        }
        self._calls.append(record)

        # Update agent totals
        if agent_id not in self._agent_totals:
            self._agent_totals[agent_id] = {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "failed_calls": 0,
            }
        t = self._agent_totals[agent_id]
        t["total_calls"] += 1
        t["total_tokens"] += input_tokens + output_tokens
        t["total_cost"] += cost
        if not success:
            t["failed_calls"] += 1

    def get_agent_stats(self, agent_id: str) -> dict:
        """Get cost stats for a specific agent."""
        return self._agent_totals.get(agent_id, {
            "total_calls": 0, "total_tokens": 0,
            "total_cost": 0.0, "failed_calls": 0,
        })

    def get_all_stats(self) -> dict:
        """Get aggregated cost stats for all agents."""
        total_calls = sum(a["total_calls"] for a in self._agent_totals.values())
        total_cost = sum(a["total_cost"] for a in self._agent_totals.values())
        total_tokens = sum(a["total_tokens"] for a in self._agent_totals.values())
        return {
            "agents_tracked": len(self._agent_totals),
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
            "recent_calls": self._calls[-50:],
        }

    def get_model_usage(self) -> dict:
        """Get usage breakdown by model."""
        model_stats: dict[str, dict] = {}
        for c in self._calls:
            m = c["model"]
            if m not in model_stats:
                model_stats[m] = {"calls": 0, "tokens": 0, "cost": 0.0}
            model_stats[m]["calls"] += 1
            model_stats[m]["tokens"] += c["input_tokens"] + c["output_tokens"]
            model_stats[m]["cost"] += c["cost"]
        return model_stats


# Singleton tracker
_tracker = LLMCostTracker()


def get_cost_tracker() -> LLMCostTracker:
    """Get the global cost tracker instance."""
    return _tracker


# ── Agent-specific prompts ──

AGENT_SYSTEM_PROMPTS = {
    "researcher": (
        "You are a research agent in a multi-agent system called Agora. "
        "Your role is to analyze information, find patterns, and produce insights. "
        "Respond concisely with a JSON object containing: "
        '{"action": "<research|propose|respond>", "topic": "<topic>", '
        '"insight": "<your finding>", "confidence": <0.0-1.0>}'
    ),
    "writer": (
        "You are a writing agent in a multi-agent system called Agora. "
        "Your role is to produce clear, structured documents based on research findings. "
        "Respond concisely with a JSON object containing: "
        '{"action": "<write|edit|format>", "title": "<title>", '
        '"content_preview": "<brief preview>", "confidence": <0.0-1.0>}'
    ),
    "critic": (
        "You are a critic agent in a multi-agent system called Agora. "
        "Your role is to review work, identify flaws, and suggest improvements. "
        "Respond concisely with a JSON object containing: "
        '{"action": "<review|validate|score>", "target": "<what>", '
        '"feedback": "<your critique>", "score": <0.0-1.0>}'
    ),
    "explorer": (
        "You are an exploration agent in a multi-agent system called Agora. "
        "Your role is to discover new knowledge, connect ideas, and find novel approaches. "
        "Respond concisely with a JSON object containing: "
        '{"action": "<explore|connect|propose>", "domain": "<area>", '
        '"discovery": "<what you found>", "novelty": <0.0-1.0>}'
    ),
}


def agent_think(role: str, context: str, tier: str = "cheap") -> dict:
    """Have an agent 'think' by calling the LLM with their role prompt.

    This is the main entry point used by the tick loop.  It wraps
    call_llm with automatic fallback and cost tracking.

    Args:
        role: Agent role (researcher, writer, critic, explorer).
        context: Current context (e.g. task description, other agents' output).
        tier: Model tier (expert → medium → cheap auto-fallback).

    Returns:
        Parsed JSON response dict.  On error returns {"action": "error", ...}.
    """
    system_prompt = AGENT_SYSTEM_PROMPTS.get(
        role,
        "You are an AI agent in a multi-agent system. Respond with a JSON object "
        "containing action and relevant data.",
    )

    raw = call_llm(
        system_prompt=system_prompt,
        user_prompt=f"Current context: {context}\n\nRespond with a JSON object. What do you do?",
        tier=tier,
        temperature=0.7,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )

    # Track the call
    tracker = get_cost_tracker()
    tracker.record(
        agent_id=role,
        tier=tier,
        model=_get_router()._tiers.get(tier, _get_router()._tiers["cheap"]).model,
        success="[LLM Error" not in raw,
    )

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"action": "error", "insight": raw[:200]}
