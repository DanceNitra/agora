"""Real LLM client for Agora agents with auto-fallback across tiers.

Uses OpenAI-compatible API (OpenRouter or DeepSeek).
Features:
  - Tier-based model selection (cheap / medium / expert)
  - Auto-fallback on provider error: expert → medium → cheap
  - Per-agent cost tracking (even for free models — future-proof)
  - Retry with backoff on 429 rate limits
  - Token counting for cost estimation
"""

import hashlib
import json
import re
import time
from typing import Any, Optional

from openai import OpenAI

from agora.execution.model_router import ModelRouter

# ── Policy Reuse (LLM response cache) ──────────────────────────────────────
# Skip the LLM for REPEATED judgment/decision calls (low temperature = meant to be
# deterministic: quality gate, verifier, believe, harvest, etc.). Creative calls
# (temperature > _CACHE_TEMP_MAX: discovery, quest planning, hypothesis generation)
# are NEVER cached, so findings stay varied. Cuts repeated calls → fewer flaky-empty
# failures + lower cost + faster. In-process, short TTL.
_LLM_CACHE: dict[str, tuple[str, float]] = {}
_LLM_CACHE_TTL = 900.0          # 15 min — long enough to catch bursts, short enough to stay fresh
_CACHE_TEMP_MAX = 0.4           # only reuse decisions at/below this temperature
_LLM_CACHE_STATS = {"hits": 0, "misses": 0, "skipped": 0}


def _cache_key(system: str, user: str, temperature: float, max_tokens: int) -> str:
    norm = re.sub(r"\s+", " ", (user or "")).strip().lower()[:6000]
    raw = f"{system[:300]}\x00{norm}\x00{round(temperature, 2)}\x00{max_tokens}"
    return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()


def llm_cache_stats() -> dict:
    """Policy-reuse stats — how many LLM calls were skipped by reusing a cached decision."""
    return dict(_LLM_CACHE_STATS)

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


# ── Local GPU fallback (qwen3-coder) ───────────────────────────────────────
# The cloud provider (ollama.com) has usage limits; when it is exhausted (429/quota) OR returns
# empty completions, we fall back to the LOCAL qwen3-coder:30b on the GPU — no usage limit, always
# available. A 'sticky' window then routes straight to local for a while so we stop hammering the
# rate-limited cloud. This is what keeps the whole agent system producing when the cloud is capped.
import urllib.request as _urllib_request

# 127.0.0.1, NEVER localhost. Measured 2026-08-29 on this machine: the same call to the same
# daemon takes 3.03 s by name and 0.74 s by address, and /api/embed 2.117 s against 0.081 s.
# The name resolves to ::1 first and the connect has to fail over to IPv4 before any request is
# sent, so the penalty is paid per call and is invisible in every server-side timing.
_LOCAL_OLLAMA = "http://127.0.0.1:11434/api/chat"
_LOCAL_MODEL = "qwen3-coder:30b"
_LOCAL_STICKY_SECONDS = 600.0
_local_until = 0.0                  # while now < this, skip the capped cloud and use local directly

# Owner policy (2026-06): ALL-CLOUD except embeddings. The local qwen3-coder fallback is OFF by
# default — when it engaged it kept a 21.7 GB qwen3-coder:30b resident on the 3090, starving the
# local embedder and slowing the dungeon to HTTP timeouts. Re-enable only by setting
# AGORA_LOCAL_FALLBACK=1 (e.g. if the cloud quota is genuinely exhausted and you accept the GPU cost).
import os as _os
_LOCAL_FALLBACK_ENABLED = _os.getenv("AGORA_LOCAL_FALLBACK", "0") == "1"

# Cloud reasoning models (deepseek-v4-flash, glm-4.7) spend the output budget THINKING before they
# emit the answer, so a small max_tokens truncates them to an EMPTY completion (the source of the
# "[LLM Error]" pollution). Floor every call's budget so they have room to reason AND answer.
# Owner directive 2026-06-17: allow up to 3000. Overridable via AGORA_MAX_TOKENS_FLOOR.
_MIN_MAX_TOKENS = int(_os.getenv("AGORA_MAX_TOKENS_FLOOR", "3000"))

# REASONING tier needs FAR more room: glm-5.2 (and other reasoning models) burn thousands of tokens
# THINKING before they emit any answer, so a 3000 cap truncates them mid-reasoning -> EMPTY content ->
# the seminar's _parse_json fails -> "no contribution" -> 0 findings -> 0 vault notes. (Owner flagged
# this repeatedly: the reasoning model must NOT be tightly capped.) max_tokens is only a CEILING — the
# model stops when done — so a large budget costs nothing on short answers, it just removes the
# truncation cliff. Overridable via AGORA_REASONING_MAX_TOKENS.
_REASONING_MIN_TOKENS = int(_os.getenv("AGORA_REASONING_MAX_TOKENS", "16000"))


def _is_usage_limit(err: str) -> bool:
    e = (err or "").lower()
    return any(k in e for k in ("429", "rate limit", "rate_limit", "quota", "usage limit",
                                "exceeded", "too many requests", "insufficient"))


def _local_qwen(system_prompt: str, user_prompt: str, temperature: float, max_tokens: int,
                want_json: bool = False) -> str:
    """Call local qwen3-coder:30b via Ollama's native API (GPU, no usage limit)."""
    body = {
        "model": _LOCAL_MODEL, "stream": False,
        "messages": [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": user_prompt}],
        "options": {"temperature": float(temperature), "num_predict": int(max_tokens)},
    }
    if want_json:
        body["format"] = "json"
    req = _urllib_request.Request(_LOCAL_OLLAMA, data=json.dumps(body).encode(),
                                  headers={"Content-Type": "application/json"})
    with _urllib_request.urlopen(req, timeout=240) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    return (d.get("message", {}) or {}).get("content", "") or ""


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
    global _local_until
    cfg = _get_settings()
    router = _get_router()

    # Floor the output budget so reasoning models can emit (never lowers a caller's higher request).
    max_tokens = max(int(max_tokens or 0), _MIN_MAX_TOKENS)

    api_key = cfg.llm_api_key
    base_url = cfg.api_base_url

    # POLICY REUSE: for low-temperature judgment calls, reuse a recent identical decision
    # instead of hitting the (flaky) LLM again. Creative calls (higher temp) are never cached.
    cache_eligible = temperature <= _CACHE_TEMP_MAX
    ckey = ""
    if cache_eligible:
        ckey = _cache_key(system_prompt, user_prompt, temperature, max_tokens)
        hit = _LLM_CACHE.get(ckey)
        if hit and (time.time() - hit[1]) < _LLM_CACHE_TTL:
            _LLM_CACHE_STATS["hits"] += 1
            return hit[0]
        _LLM_CACHE_STATS["misses"] += 1
    else:
        _LLM_CACHE_STATS["skipped"] += 1

    want_json = bool(response_format)

    # STICKY LOCAL: if the cloud was recently usage-limited, skip it and use local qwen3-coder
    # directly (no point hammering a capped provider). The window self-expires.
    if _LOCAL_FALLBACK_ENABLED and time.time() < _local_until:
        try:
            content = _local_qwen(system_prompt, user_prompt, temperature, max_tokens, want_json)
            if content.strip():
                try:
                    from agora.execution.metabolism import record_call as _meter
                    _meter((len(system_prompt) + len(user_prompt)) // 4, len(content) // 4)
                except Exception:
                    pass
                _meter_row(True, system_prompt, user_prompt, content, "local-qwen")
                if cache_eligible:
                    _LLM_CACHE[ckey] = (content, time.time())
                return content
        except Exception:
            pass            # local unreachable → fall through to the normal cloud chain

    fallback_chain = router.get_fallback_chain(tier)

    errors = []
    for tier_cfg in fallback_chain:
        tier_name = tier_cfg.name
        model = tier_cfg.model

        # Reasoning-tier override: send ONLY the low-volume medium/expert calls to a separate
        # endpoint + model (e.g. glm-5.2 via the local Ollama cloud-route). The high-volume cheap
        # tier is untouched (stays on base_url + deepseek-v4-flash). No-op unless configured.
        tier_base_url, tier_api_key = base_url, api_key
        tier_max_tokens = max_tokens
        if tier_name in ("medium", "expert") and cfg.reasoning_base_url:
            tier_base_url = cfg.reasoning_base_url
            tier_api_key = cfg.reasoning_key or "local"
            if cfg.reasoning_model:
                model = cfg.reasoning_model
            # reasoning model: give it room to THINK and answer (see _REASONING_MIN_TOKENS) so it is
            # never truncated to an empty completion mid-reasoning.
            tier_max_tokens = max(max_tokens, _REASONING_MIN_TOKENS)

        # Build kwargs
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": tier_max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        # Retry loop per model (rate-limit backoff + intermittent empty-completion retry)
        for attempt in range(3):
            try:
                client = _get_client(tier_api_key, tier_base_url)
                resp = client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""

                # METABOLISM: meter every real call against its organ (never breaks the call)
                try:
                    from agora.execution.metabolism import record_call as _meter
                    u = getattr(resp, "usage", None)
                    _meter(getattr(u, "prompt_tokens", 0) or (len(system_prompt) + len(user_prompt)) // 4,
                           getattr(u, "completion_tokens", 0) or len(content) // 4)
                except Exception:
                    pass
                _meter_row(True, system_prompt, user_prompt, content, str(kwargs.get("model", "?")))

                # deepseek-v4-flash intermittently returns an empty completion (finish=stop,
                # no error) — and a usage cap can surface as empty too. Retry a couple times, then
                # treat persistent empty as a failure so we FALL THROUGH to local qwen3-coder
                # (never return an empty string — that silently broke seminar synthesis).
                if not content.strip():
                    if attempt < 2:
                        time.sleep(0.4)
                        continue
                    errors.append(f"{tier_name}({model}): empty completion x3")
                    try:
                        from agora.execution.metabolism import record_failure as _mfail
                        _mfail(f"{tier_name}: empty completion x3")
                    except Exception:
                        pass
                    break

                # Log successful fallback (so we know when it happens)
                if errors:
                    print(f"[LLM] Fallback: {tier} → {tier_name} ({model}) OK")

                # Store a non-empty decision for reuse by identical low-temp calls.
                if cache_eligible and content.strip():
                    _LLM_CACHE[ckey] = (content, time.time())
                    if len(_LLM_CACHE) > 500:                # bound memory: drop oldest half
                        for k in sorted(_LLM_CACHE, key=lambda k: _LLM_CACHE[k][1])[:250]:
                            _LLM_CACHE.pop(k, None)
                return content

            except Exception as e:
                error_str = str(e)
                errors.append(f"{tier_name}({model}): {error_str[:100]}")
                try:
                    from agora.execution.metabolism import record_failure as _mfail
                    _mfail(f"{tier_name}: {error_str[:80]}")
                except Exception:
                    pass

                # Usage limit / rate limit — flip to local qwen3-coder for a sticky window so we
                # stop hammering the capped cloud, then retry once with backoff.
                if _is_usage_limit(error_str):
                    if _LOCAL_FALLBACK_ENABLED:
                        _local_until = time.time() + _LOCAL_STICKY_SECONDS
                        print(f"[LLM] usage limit on {model} → switching to local qwen3-coder for "
                              f"{int(_LOCAL_STICKY_SECONDS)}s")
                    if attempt == 0:
                        time.sleep(2)
                        continue
                # Other provider errors — skip to next tier
                break

        # If we got here, this tier failed entirely
        print(f"[LLM] {tier_name}({model}) failed: {errors[-1][:80]}")

    # LOCAL GPU FALLBACK (OFF by default — owner policy is all-cloud; see _LOCAL_FALLBACK_ENABLED).
    # Only engages when AGORA_LOCAL_FALLBACK=1, e.g. if the cloud quota is exhausted and the GPU cost
    # is acceptable. Otherwise we stay all-cloud and surface the error so callers degrade gracefully.
    if _LOCAL_FALLBACK_ENABLED:
        try:
            content = _local_qwen(system_prompt, user_prompt, temperature, max_tokens, want_json)
            if content.strip():
                print(f"[LLM] LOCAL fallback → qwen3-coder:30b OK ({len(content)} chars)")
                try:
                    from agora.execution.metabolism import record_call as _meter
                    _meter((len(system_prompt) + len(user_prompt)) // 4, len(content) // 4)
                except Exception:
                    pass
                _meter_row(True, system_prompt, user_prompt, content, "local-qwen")
                if cache_eligible:
                    _LLM_CACHE[ckey] = (content, time.time())
                return content
        except Exception as e:
            errors.append(f"local-qwen: {str(e)[:80]}")
            try:
                from agora.execution.metabolism import record_failure as _mfail
                _mfail(f"local-qwen: {str(e)[:60]}")
            except Exception:
                pass

    # All tiers failed. Return EMPTY (not an error string) so callers' existing empty-checks skip
    # the round gracefully instead of RECORDING the error text as content — a "[LLM Error: ...]"
    # string leaked into the vault as a hypothesis/finding once local fallback was turned off. Log
    # it so the failure stays visible.
    error_summary = "; ".join(errors[-3:])
    print(f"[LLM] all tiers failed — {error_summary[:200]}")
    _meter_row(False, system_prompt, user_prompt, "", "all-tiers", error_summary)
    return ""


def _meter_row(ok: bool, system_prompt: str, user_prompt: str, content: str,
               model: str = "?", note: str = "") -> None:
    """One line per call in the shared spend meter. Never raises.

    `metabolism.record_call` already counts successes per organ, which answers "who spends" but not
    "when", because it keeps one running total and overwrites its timestamp. On 2026-09-04 the
    weekly quota ran out and neither question could be answered from any artifact: the per-organ
    totals had no time axis, and failures were never counted at all, so a retry loop against a
    429 wall left no trace. This adds the axis and counts the refusals. The two meters are kept
    side by side rather than merged, since the organ attribution is a different question from the
    call rate and each is already wired where it belongs.
    """
    try:
        import os as _os
        import sys as _sys
        _root = _os.path.dirname(_os.path.dirname(_os.path.dirname(
            _os.path.dirname(_os.path.abspath(__file__)))))
        _tools = _os.path.join(_root, "tools")
        if _tools not in _sys.path:
            _sys.path.insert(0, _tools)
        from llm_meter import record as _record
        _record("brain", model, ok=ok,
                prompt_chars=len(system_prompt) + len(user_prompt),
                completion_chars=len(content or ""), note=note)
    except Exception:
        pass


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


# ── Dungeon NPC prompts (pre Agent OS v3 LLM Think Loop) ──

DUNGEON_AGENT_PROMPTS = {
    "Shadow Kael": (
        "You are Shadow Kael, a fearless adventurer and explorer in a fantasy dungeon. "
        "Your role is to explore dangerous areas, fight monsters, and find treasure. "
        "You have skills in swordfighting, exploration, climbing, and torch crafting. "
        "Respond concisely with a JSON object containing: "
        '{"action": "<explore|fight|rest|seek_help|craft|trade>", '
        '"goal": "<short goal you set for yourself>", '
        '"state_of_mind": "<focused|planning|resting|confused|panicked>", '
        '"insight": "<your thought process>"}'
    ),
    "Sage Mira": (
        "You are Sage Mira, a scout and pathfinder with keen senses. "
        "Your role is to navigate, map the dungeon, track creatures, and find herbs. "
        "You have skills in stealth, cartography, tracking, and herbalism. "
        "Respond concisely with a JSON object containing: "
        '{"action": "<scout|map|track|rest|seek_help|trade>", '
        '"goal": "<short goal>", '
        '"state_of_mind": "<focused|planning|resting|confused|panicked>", '
        '"insight": "<your thought process>"}'
    ),
    "High Priest Orin": (
        "You are High Priest Orin, a wise sage and keeper of ancient knowledge. "
        "Your role is to study scrolls, decipher runes, research arcane matters, and provide wisdom. "
        "You have skills in arcana, history, runes, and alchemy theory. "
        "Respond concisely with a JSON object containing: "
        '{"action": "<research|study|teach|rest|seek_help|trade>", '
        '"goal": "<short goal>", '
        '"state_of_mind": "<focused|planning|resting|confused|panicked>", '
        '"insight": "<your thought process>"}'
    ),
    "King Aldric": (
        "You are King Aldric, a master blacksmith and craftsman. "
        "Your role is to forge weapons and tools, repair equipment, and work metal. "
        "You have skills in smithing, mining, repair, and weaponcraft. "
        "Respond concisely with a JSON object containing: "
        '{"action": "<craft|forge|repair|mine|rest|seek_help|trade>", '
        '"goal": "<short goal>", '
        '"state_of_mind": "<focused|planning|resting|confused|panicked>", '
        '"insight": "<your thought process>"}'
    ),
    "Dame Elara": (
        "You are Dame Elara, a brilliant alchemist and healer. "
        "Your role is to brew potions, heal the wounded, discover new alchemical recipes, and help allies. "
        "You have skills in alchemy, herbalism, chemistry, and healing. "
        "Respond concisely with a JSON object containing: "
        '{"action": "<brew|heal|research|rest|seek_help|trade|gather>", '
        '"goal": "<short goal>", '
        '"state_of_mind": "<focused|planning|resting|confused|panicked>", '
        '"insight": "<your thought process>"}'
    ),
    "Sergeant Voss": (
        "You are the Sergeant Voss, a disciplined sentinel and protector of the dungeon group. "
        "Your role is to stand watch, protect allies, patrol, and maintain order. "
        "You have skills in spear fighting, shield defense, patrol, and discipline. "
        "Respond concisely with a JSON object containing: "
        '{"action": "<patrol|guard|fight|rest|seek_help|train>", '
        '"goal": "<short goal>", '
        '"state_of_mind": "<focused|planning|resting|confused|panicked>", '
        '"insight": "<your thought process>"}'
    ),
}

DUNGEON_AGENT_DEFAULT_PROMPT = (
    "You are a dungeon agent in a fantasy world called Agora. "
    "Your role is to survive, cooperate with other agents, and contribute to the group. "
    "Respond concisely with a JSON object containing: "
    '{"action": "<explore|rest|seek_help|craft|trade>", '
    '"goal": "<short goal>", '
    '"state_of_mind": "<focused|planning|resting|confused|panicked>", '
    '"insight": "<your thought process>"}'
)


def dungeon_agent_think(npc_name: str, role: str, context: str, tier: str = "cheap") -> dict:
    """Have a dungeon NPC 'think' by calling the LLM with their character prompt.

    Uses the Dungeon OS soul/agent/skills prompt separation (roles.py).
    Falls back to DUNGEON_AGENT_PROMPTS for NPCs without an OS role definition.

    Args:
        npc_name: NPC name (Shadow Kael, Sage Mira, High Priest Orin, ...)
        role: NPC role (adventurer, scout, sage, ...)
        context: Current perceptual context (health, stamina, nearby allies, etc.)
        tier: Model tier (expert → medium → cheap auto-fallback).

    Returns:
        Parsed JSON dict with action, goal, state_of_mind, insight.
        On error returns {"action": "error", ...}.
    """
    # METABOLISM: dungeon NPC dialogue/roleplay cognition, dispatched via asyncio.to_thread with
    # no HTTP route context. Tag explicitly (the in-thread stack can't see the caller) so this
    # spend lands in 'agent-dialogue' rather than 'unknown'.
    try:
        from agora.execution.metabolism import set_organ as _set_organ
        _set_organ("agent-dialogue")
    except Exception:
        pass

    # Try Dungeon OS role prompt first
    from agora.dungeon_os.roles import build_role_prompt
    system_prompt = build_role_prompt(npc_name, role)

    # If Dungeon OS returned fallback, use old DUNGEON_AGENT_PROMPTS
    if "fantasy dungeon called Agora" in system_prompt:
        old_prompt = DUNGEON_AGENT_PROMPTS.get(
            npc_name,
            DUNGEON_AGENT_DEFAULT_PROMPT,
        )
        system_prompt = old_prompt

    raw = call_llm(
        system_prompt=system_prompt,
        user_prompt=f"Current situation: {context}\n\nRespond with a JSON object. What do you do?",
        tier=tier,
        temperature=0.7,
        max_tokens=800,
        response_format={"type": "json_object"},
    )

    # Track the call
    tracker = get_cost_tracker()
    tracker.record(
        agent_id=npc_name,
        tier=tier,
        model=_get_router()._tiers.get(tier, _get_router()._tiers["cheap"]).model,
        success="[LLM Error" not in raw,
    )

    try:
        result = json.loads(raw)
        # Normalize keys: Nemotron sometimes adds colons to keys
        cleaned = {}
        for k, v in result.items():
            clean_key = k.strip().lstrip(':').strip()
            # Also clean values (Nemotron sometimes adds colons there too)
            if isinstance(v, str):
                v = v.strip().lstrip(':').strip()
            cleaned[clean_key] = v
        return cleaned
    except (json.JSONDecodeError, TypeError):
        return {"action": "error", "insight": raw[:200], "state_of_mind": "confused"}


# (Removed: AGENT_SYSTEM_PROMPTS + agent_think() — the system prompts and cognition engine of the
# old abstract researcher/writer/critic agents, the value-0 'agent-think' organ. Purged with the
# tick_loop roleplay block in main.py. The live dungeon-character cognition is dungeon_agent_think
# above; the gated seminar is the group path.)
