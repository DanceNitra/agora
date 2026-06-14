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


# Board-aligned topics for the CORPORATION's lead hunt — tuned to our actual Crucible content
# (the Operating-Point thesis: cognitive biases, statistical artifacts, finance, replication crisis),
# not just the physics-heavy replication rotation. These are where FAMOUS, contested, FAILED-likely
# claims live — the highest-value Crucible candidates.
_CORP_TOPICS = [
    "cognitive bias overconfidence calibration measured effect size",
    "replication crisis effect size psychology meta-analysis",
    "regression to the mean statistical artifact measurement",
    "behavioral finance anomaly return predictability out-of-sample",
    "heuristics and biases reasoning experiment quantitative",
    "wisdom of crowds aggregation accuracy correlation",
    "publication bias p-hacking effect size inflation",
    "forecasting calibration expert prediction accuracy",
    "nudge intervention effect size field experiment",
    "growth mindset intervention effect size meta-analysis",
    "power posing ego depletion replication effect",
    "diversification tail risk portfolio number of stocks",
]


# methods-boilerplate that scores on a bare number but carries NO testable result
_METHODS_NOISE = re.compile(
    r"\b(participants?|we identif\w+|literature search|studies for inclusion|sample of|"
    r"systematic review|inclusion criteria|we (?:perform|conduct|search))\b", re.IGNORECASE)
# a genuine RESULT signal (effect size / direction), not just any digit
_RESULT_STRONG = re.compile(
    r"(\bd\s*=\s*[-\d.]|\br\s*=\s*[-\d.]|\beffect size\b|\bincreas\w+ by\b|\breduc\w+ by\b|"
    r"\bcohen'?s d\b|\bodds ratio\b|\bcorrelat\w+ of\b|\d+(?:\.\d+)?\s*%|\bbeta\s*=|"
    r"\bexponent\b|\bthreshold\b|\bscal\w+\b|\bvanish\w+\b|\bdiverg\w+\b)", re.IGNORECASE)


def _scan_topic(topic: str, attempted: set) -> dict | None:
    """Best fresh measurable-RESULT paper for one topic, or None. Prefers a real effect/exponent
    over a methods sentence that merely contains a number (e.g. 'n = 28 participants')."""
    from agora.execution.research_tool import openalex_search, arxiv_search
    papers = [p for p in (arxiv_search(topic, 6) + openalex_search(topic, 4)) if not p.get("error")]
    best = None
    for p in papers:
        claim, score = _best_claim((p.get("summary") or "").strip())
        if score < 2 or len(claim) < 40 or claim[:60].lower() in attempted:
            continue
        if _METHODS_NOISE.search(claim) and not _RESULT_STRONG.search(claim):
            continue                                   # a methods sentence, not a testable result
        if _RESULT_STRONG.search(claim):
            score += 3                                 # prefer real effect/exponent claims
        if best is None or score > best["score"]:
            src = f"{p.get('title','')[:90]} ({p.get('authors','')[:50]}, {p.get('published','')[:10]})"
            best = {"claim": claim, "source": src[:160], "title": (p.get("title") or "")[:90],
                    "url": p.get("url", ""), "topic": topic, "score": score}
    return best


def pick_paper_target() -> dict | None:
    """A REAL arXiv paper with a quantitative, simulable claim — the input Rooke needs to produce
    a genuine REPRODUCED/FAILED. Tries the hour's physics-replication topic first, then the
    board-aligned corp topics in a rotated order, returning the first fresh measurable claim — so a
    single exhausted topic can no longer starve the pipeline (the corp 'exhausted sources' bug)."""
    attempted = {(r.get("claim") or "")[:60].lower() for r in _load()}
    pool = [_REPLICABLE_TOPICS[int(time.time() // 3600) % len(_REPLICABLE_TOPICS)]]
    r = int(time.time() // 1800) % len(_CORP_TOPICS)
    pool += _CORP_TOPICS[r:] + _CORP_TOPICS[:r]
    for topic in pool:
        hit = _scan_topic(topic, attempted)
        if hit:
            return hit
    return None


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
    # Stage 3 (accuracy loop): a hard external verdict credits the brain-memories about this claim —
    # REPRODUCED rewards knowledge consistent with verified results, FAILED debits knowledge tied to a
    # debunked claim. NOT_COMPUTABLE carries no signal (skip).
    if o in ("REPRODUCED", "FAILED"):
        try:
            from agora.execution.mnemo_bridge import credit_outcome
            credit_outcome(claim, good=(o == "REPRODUCED"))
        except Exception:
            pass
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
