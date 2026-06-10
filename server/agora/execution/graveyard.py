"""
The Graveyard — dead ideas, their cause of death, and the condition of resurrection.

The skip ledger remembers which THEMES were refused; nothing remembered why IDEAS died. So
agents re-walk dead ends, and — worse — a justified resurrection (new evidence overturning an
old death) can never happen, because the death was never recorded as a falsifiable event.
Every grave holds three things: the claim, the cause of death, and `resurrect_when` — the
observation that would reopen the case. Burials are automatic (belief kills via the Bounty
hook, dead forgings from the Analogy Forge); resurrection is deliberate (Claude, with reason).
A graveyard is not an archive — it is a standing list of conditional bets that stayed honest.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".graveyard.json"


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


def bury(claim: str, cause: str, resurrect_when: str = "", killed_by: str = "") -> dict | None:
    """One grave per claim (deduped on the first 60 chars). Returns the grave or None."""
    c = (claim or "").strip()
    if len(c) < 8:
        return None
    items = _load()
    if any(c[:60].lower() in (g.get("claim", "").lower()) for g in items):
        return None
    rec = {"id": uuid.uuid4().hex[:6], "claim": c[:160], "cause": (cause or "")[:240],
           "resurrect_when": (resurrect_when or "")[:200], "killed_by": (killed_by or "")[:40],
           "status": "dead", "ts": time.time()}
    items.append(rec)
    _save(items[-150:])
    return rec


def resurrect(gid: str, reason: str) -> dict | None:
    """Deliberate resurrection — new evidence overturned the death. Keeps the grave (history)."""
    items = _load()
    for g in items:
        if g.get("id") == gid and g.get("status") == "dead":
            g["status"] = "resurrected"
            g["resurrection_reason"] = (reason or "")[:240]
            g["resurrected_ts"] = time.time()
            _save(items)
            return g
    return None


def epitaphs(n: int = 8) -> list[str]:
    """One-liners for the quest planner: dead ends agents must not re-walk."""
    return [f"{g['claim'][:70]} (died: {g['cause'][:60]})"
            for g in _load() if g.get("status") == "dead"][-n:]


def format_graveyard() -> str:
    items = _load()
    if not items:
        return "🪦 _The graveyard is empty — no idea has died on the record yet._"
    dead = [g for g in items if g.get("status") == "dead"]
    risen = [g for g in items if g.get("status") == "resurrected"]
    lines = [f"🪦 *The Graveyard* — {len(dead)} buried · {len(risen)} resurrected"]
    for g in items[-7:][::-1]:
        icon = "🌅" if g.get("status") == "resurrected" else "🪦"
        lines.append(f"{icon} `{g['id']}` {g['claim'][:60]}")
        lines.append(f"    died: {g['cause'][:70]}")
        if g.get("resurrect_when"):
            lines.append(f"    rises if: {g['resurrect_when'][:70]}")
    return "\n".join(lines)
