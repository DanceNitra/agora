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


async def pick_target(db) -> dict | None:
    """A recent sourced finding not yet attempted — the claim plus its citation."""
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
