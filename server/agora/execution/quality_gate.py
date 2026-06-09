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
import re

from agora.execution.llm_client import call_llm

_CITES = re.compile(r"\([A-Z][a-zA-Z]+(?: et al\.?)?,? \d{4}\)")


def _heuristic(title: str, content: str, min_score: int = 6) -> dict:
    """Deterministic quality check (no LLM) — used when the critic LLM is unavailable so the
    research→vault funnel keeps flowing instead of rejecting everything. Keeps stubs/echoes/
    ungrounded text out, lets substantive grounded findings through."""
    c = (content or "").strip()
    body = c.split("Source:")[0].strip()
    tl = (title or "").lower()
    grounded = ("Source:" in c) or bool(_CITES.search(c))
    nested = tl.count("hypothesize on:") >= 2 or tl.count("pursue direction:") >= 2
    if nested or len(body) < 140 or not grounded:
        return {"pass": False, "score": 3, "reason": "heuristic: short / ungrounded / stub"}
    if body.strip(". ").lower() == tl.strip(". "):
        return {"pass": False, "score": 3, "reason": "heuristic: restates the title"}
    return {"pass": True, "score": min_score, "reason": "heuristic: substantive + cites a source"}

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

    The strict critic LLM judges when available; when it is unavailable/empty (deepseek-v4-flash
    intermittently returns nothing), we fall back to a DETERMINISTIC heuristic rather than rejecting
    everything — otherwise LLM flakiness silently blocks the entire research→vault funnel.
    """
    user = (f"Title: {title}\n\nNote:\n{(content or '')[:2400]}\n\n"
            "Does this deserve a permanent place in a serious research vault?")
    try:
        out = await asyncio.to_thread(call_llm, _SYSTEM, user, "cheap", 0.2, 200) or ""
        m = re.search(r"\{.*\}", out, re.DOTALL)
        if not m:
            return _heuristic(title, content, min_score)      # LLM empty → heuristic, not reject-all
        d = json.loads(m.group(0))
        score = int(d.get("score", 0))
        passed = (str(d.get("verdict", "")).lower() == "accept") and score >= min_score
        return {"pass": passed, "score": score, "reason": str(d.get("reason", ""))[:140]}
    except Exception:
        return _heuristic(title, content, min_score)          # any error → heuristic, not reject-all
