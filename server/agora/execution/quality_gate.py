"""
Quality gate — keeps SHALLOW, ungrounded agent output OUT of the knowledge vault.

Every note an agent wants to persist is first judged by a strict critic LLM. Only notes
that are specific, grounded in real concepts, and genuinely worth deeper research pass.
Everything vague / generic / self-referential / restating-the-obvious is rejected so it
never reaches the vault.
"""
from __future__ import annotations

import asyncio
import json

from agora.execution.llm_client import call_llm

_SYSTEM = (
    "You are the strict QUALITY GATE of a serious research vault (a personal 'second brain'). "
    "Your one job is to KEEP SHALLOW NOISE OUT. REJECT the note if it is vague, generic, "
    "self-referential filler, restating the obvious, ungrounded speculation, buzzword soup, or "
    "has no concrete substance a researcher would actually keep. ACCEPT only if it is specific, "
    "grounded in real concepts or sources, non-obvious, and genuinely worth deeper research. "
    "Be harsh — when in doubt, REJECT. "
    'Reply ONLY JSON: {"score": <int 0-10>, "verdict": "accept" or "reject", "reason": "<=12 words"}'
)


async def assess_quality(title: str, content: str, min_score: int = 6) -> dict:
    """Judge a note. Returns {pass: bool, score: int, reason: str}.

    Fails CLOSED (reject) if the evaluator is unavailable — the whole point is to keep noise
    out, so we never let unjudged content slip through.
    """
    user = (f"Title: {title}\n\nNote:\n{(content or '')[:2400]}\n\n"
            "Does this deserve a permanent place in a serious research vault?")
    try:
        out = await asyncio.to_thread(
            call_llm, _SYSTEM, user, "cheap", 0.2, 160, {"type": "json_object"})
        d = json.loads(out)
        score = int(d.get("score", 0))
        passed = (str(d.get("verdict", "")).lower() == "accept") and score >= min_score
        return {"pass": passed, "score": score, "reason": str(d.get("reason", ""))[:140]}
    except Exception as e:
        return {"pass": False, "score": 0, "reason": f"evaluator unavailable ({e})"}
