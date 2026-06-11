"""
The Replication Unit — Artificer Rooke re-runs other people's science.

Reading literature grounds beliefs in what was CLAIMED; replication grounds them in what
actually COMPUTES. The unit picks a sourced finding from the collective knowledge, and Claude
builds the smallest computational model of the claim in the Lab: REPRODUCED (the mechanism
holds in a minimal model), FAILED (it doesn't — which is a publishable result, science's
rarest export), or NOT_COMPUTABLE (an honest pass). The ledger is Rooke's track record — the
first dungeon agent whose standing rests on re-running the work of others, not producing more.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".replications.json"
_OUTCOMES = ("REPRODUCED", "FAILED", "NOT_COMPUTABLE")


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    try:
        _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


# Computational/methods topics where a published claim has a SIMULABLE core (a number, an
# exponent, a threshold, a rate) — the regime where replication can actually REPRODUCE or FAIL,
# instead of NOT_COMPUTABLE on a descriptive claim. Rotated so Rooke covers fresh ground.
_REPLICABLE_TOPICS = [
    "branching process critical exponent survival probability",
    "random graph percolation threshold giant component",
    "epidemic threshold network SIR basic reproduction number",
    "stochastic gradient descent convergence rate convex",
    "multi-armed bandit regret bound logarithmic",
    "directed percolation absorbing state phase transition exponent",
    "preferential attachment power-law degree exponent",
    "reinforcement learning sample complexity bound",
    "Kuramoto model synchronization critical coupling",
    "contagion cascade threshold fraction network",
]
# a sentence carries a REPLICABLE result if it has a number AND a result-signal word
_RESULT = re.compile(
    r"(\d+(?:\.\d+)?\s*%|\bexponent\b|\bthreshold\b|\bcritical\b|\bscal\w+\b|\brate\b|"
    r"\bbound\b|\bprobabilit\w+\b|\bconverge\w*\b|\bregret\b|\bpower[- ]law\b|"
    r"\d+(?:\.\d+)?\s*(?:times|x|fold)|=\s*\d|\bproportional to\b)", re.IGNORECASE)
_NUM = re.compile(r"\d")


def _best_claim(summ: str) -> tuple[str, int]:
    """The abstract sentence with the strongest measurable-result signal, and its score."""
    best, score = "", 0
    for s in re.split(r"(?<=[.!?])\s", summ):
        if len(s) < 50:
            continue
        sc = len(_RESULT.findall(s)) * 2 + (1 if _NUM.search(s) else 0)
        if sc > score:
            best, score = s[:240], sc
    return best, score


def pick_paper_target() -> dict | None:
    """A REAL arXiv paper with a quantitative, simulable claim — the input Rooke needs to produce
    a genuine REPRODUCED/FAILED (not NOT_COMPUTABLE on an internal/descriptive finding). Picks the
    paper whose abstract carries the strongest measurable result, deduped against what's attempted."""
    from agora.execution.research_tool import openalex_search, arxiv_search
    attempted = {(r.get("claim") or "")[:60].lower() for r in _load()}
    rot = int(time.time() // 3600) % len(_REPLICABLE_TOPICS)
    topic = _REPLICABLE_TOPICS[rot]
    papers = [p for p in (arxiv_search(topic, 6) + openalex_search(topic, 4)) if not p.get("error")]
    best = None
    for p in papers:
        claim, score = _best_claim((p.get("summary") or "").strip())
        if score < 2 or len(claim) < 40 or claim[:60].lower() in attempted:   # need a real result-signal
            continue
        if best is None or score > best["score"]:
            src = f"{p.get('title','')[:90]} ({p.get('authors','')[:50]}, {p.get('published','')[:10]})"
            best = {"claim": claim, "source": src[:160], "title": (p.get("title") or "")[:90],
                    "url": p.get("url", ""), "topic": topic, "score": score}
    return best


async def pick_target(db) -> dict | None:
    """The replication target. PREFER a real arXiv paper with a simulable quantitative claim
    (Aldric's roadmap: feed Rooke real papers); fall back to a recent sourced internal finding."""
    import asyncio as _aio
    paper = await _aio.to_thread(pick_paper_target)
    if paper:
        return paper
    attempted = {(r.get("claim") or "")[:60].lower() for r in _load()}
    cur = await db.execute(
        "SELECT title, content FROM collective_knowledge WHERE knowledge_type='discovery' "
        "AND content LIKE '%Source:%' ORDER BY created_at DESC LIMIT 60")
    rows = await cur.fetchall()
    for r in rows:
        content = (r["content"] or "").strip()
        claim = re.split(r"(?<=[.!?])\s", content)[0][:200]
        if len(claim) < 40 or claim[:60].lower() in attempted:
            continue
        m = re.search(r"Source:\s*(.+)$", content, re.MULTILINE)
        source = (m.group(1).strip() if m else "")[:160]
        if not source:
            continue
        return {"claim": claim, "source": source, "title": (r["title"] or "")[:90]}
    return None


def record(claim: str, source: str, outcome: str, lab_id: str = "", note: str = "") -> dict | None:
    o = (outcome or "").strip().upper()
    if o not in _OUTCOMES or len((claim or "").strip()) < 10:
        return None
    rec = {"claim": (claim or "")[:200], "source": (source or "")[:160], "outcome": o,
           "lab_id": (lab_id or "")[:12], "note": (note or "")[:240], "ts": time.time()}
    items = _load()
    items.append(rec)
    _save(items[-120:])
    return rec


def format_replications() -> str:
    items = _load()
    if not items:
        return "⚗️ _No replication has been attempted yet — Rooke's bench is clean._"
    by = {o: sum(1 for x in items if x["outcome"] == o) for o in _OUTCOMES}
    lines = [f"⚗️ *The Replication Unit* — {by['REPRODUCED']} reproduced · "
             f"{by['FAILED']} failed · {by['NOT_COMPUTABLE']} passed"]
    icon = {"REPRODUCED": "✅", "FAILED": "💥", "NOT_COMPUTABLE": "⏭"}
    for r in items[-6:][::-1]:
        lines.append(f"{icon[r['outcome']]} {r['claim'][:64]}")
        if r.get("note"):
            lines.append(f"    {r['note'][:76]}")
    return "\n".join(lines)
