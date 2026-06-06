"""Real LLM client for Agora agents.
Uses OpenAI-compatible API (DeepSeek or OpenRouter)."""

import json
import time
from typing import Any
from openai import OpenAI

# Lazy import to avoid circular deps
_settings = None

def _get_settings():
    global _settings
    if _settings is None:
        from agora.config import settings
        _settings = settings
    return _settings


def _get_client(model_tier: str = "cheap") -> tuple[OpenAI, str]:
    """Return (client, resolved_model) for any model tier."""
    cfg = _get_settings()
    api_key = cfg.api_key
    base_url = cfg.api_base_url

    model_map = {
        "cheap": cfg.llm_model_cheap,
        "medium": cfg.llm_model_medium,
        "expert": cfg.llm_model_expert,
    }
    model = model_map.get(model_tier, cfg.llm_model_cheap)

    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model


def call_llm(
    system_prompt: str,
    user_prompt: str,
    tier: str = "cheap",
    temperature: float = 0.7,
    max_tokens: int = 500,
    response_format: dict | None = None,
) -> str:
    """Call the LLM and return the response content.

    Args:
        system_prompt: System-level instruction.
        user_prompt: User message content.
        tier: Model tier ("cheap", "medium", "expert").
        temperature: Sampling temperature (0.0-1.0).
        max_tokens: Max output tokens.
        response_format: Optional {"type": "json_object"}.

    Returns:
        Response text content.
    """
    client, model = _get_client(tier)
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

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            # Return error as response so agent can handle it
            return f"[LLM Error: {error_str[:200]}]"

    return "[LLM Error: max retries exceeded]"


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

    Args:
        role: Agent role (researcher, writer, critic, explorer).
        context: Current context (e.g. task description, other agents' output).
        tier: Model tier.

    Returns:
        Parsed JSON response dict.
    """
    system_prompt = AGENT_SYSTEM_PROMPTS.get(
        role,
        "You are an AI agent in a multi-agent system. Respond with a JSON object "
        'containing action and relevant data.',
    )

    raw = call_llm(
        system_prompt=system_prompt,
        user_prompt=f"Current context: {context}\n\nRespond with a JSON object. What do you do?",
        tier=tier,
        temperature=0.7,
        max_tokens=300,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"action": "error", "insight": raw[:200]}
