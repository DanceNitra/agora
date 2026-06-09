"""
The Capability Forge — systematic self-extension.

"Upgrade agora infinitely" has been ad-hoc: we build what we happen to notice. The Forge makes
it an organ: DETECTORS scan the system's own failure traces for capability gaps — claims the
Reality Bridge could not test (INSUFFICIENT verdicts cluster), research questions stuck open
for days (the toolset can't answer them) — and the owner can register gaps by hand. The top
open gap is periodically queued for Claude, who designs and implements the smallest organ that
closes it (a new data source, a new sense, a new tool), with tests, like any self-upgrade.
Gap → proposal → implementation → registration, as a loop.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".forge.json"


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(gaps: list) -> None:
    try:
        _STORE.write_text(json.dumps(gaps, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def add_gap(description: str, kind: str = "manual", evidence: str = "") -> dict | None:
    """Register a capability gap (deduped on the first 60 chars)."""
    desc = (description or "").strip()
    if len(desc) < 12:
        return None
    gaps = _load()
    if any(desc[:60].lower() in (g.get("description", "").lower()) for g in gaps):
        return None
    rec = {"id": uuid.uuid4().hex[:6], "kind": kind, "description": desc[:280],
           "evidence": evidence[:300], "status": "open", "ts": time.time()}
    gaps.append(rec)
    _save(gaps[-100:])
    return rec


def set_status(gid: str, status: str) -> dict | None:
    gaps = _load()
    hit = None
    for g in gaps:
        if g.get("id") == gid:
            g["status"] = status
            g[f"{status}_ts"] = time.time()
            hit = g
    _save(gaps)
    return hit


def top_open_gap() -> dict | None:
    """Oldest open gap first — gaps that persist matter most."""
    open_gaps = [g for g in _load() if g.get("status") == "open"]
    return sorted(open_gaps, key=lambda g: g.get("ts", 0))[0] if open_gaps else None


async def detect_gaps(db) -> list[dict]:
    """Scan the system's own failure traces for missing capabilities."""
    found = []

    # (1) Reality Bridge couldn't test claims — INSUFFICIENT verdict cluster in recent findings
    cur = await db.execute(
        "SELECT title, content FROM collective_knowledge WHERE knowledge_type='discovery' "
        "AND title LIKE 'Reality:%' ORDER BY created_at DESC LIMIT 40")
    rows = await cur.fetchall()
    insufficient = [(r["title"] or "")[9:70] for r in rows
                    if "INSUFFICIENT" in (r["content"] or "")]
    if len(insufficient) >= 3:
        g = add_gap(f"Reality Bridge lacks a data source for claims like: "
                    f"{'; '.join(insufficient[:3])}",
                    kind="reality_bridge",
                    evidence=f"{len(insufficient)} INSUFFICIENT verdicts in the last 40 reality checks")
        if g:
            found.append(g)

    # (2) Flywheel questions stuck open for over a week — the research toolset can't answer them
    from agora.execution.flywheel import _load as fw_load
    now = time.time()
    stuck = [q for q in fw_load() if q.get("status") == "open"
             and now - q.get("ts", now) > 7 * 86400]
    if len(stuck) >= 4:
        g = add_gap(f"{len(stuck)} research questions stuck open >7 days — the agents' current "
                    f"tools can't close them (e.g.: {stuck[0]['question'][:90]})",
                    kind="stuck_research",
                    evidence="flywheel closure latency exceeded a week at scale")
        if g:
            found.append(g)
    return found


def format_forge() -> str:
    gaps = _load()
    if not gaps:
        return "🔨 _No capability gaps on record — the Forge is cold._"
    icon = {"open": "🕳", "queued": "⏳", "built": "✅", "dismissed": "🚫"}
    lines = ["🔨 *Capability Forge* — what Agora knows it can't do yet"]
    for g in sorted(gaps, key=lambda x: -x.get("ts", 0))[:8]:
        lines.append(f"{icon.get(g['status'], '•')} `{g['id']}` [{g['kind']}] {g['description'][:70]}")
    return "\n".join(lines)
