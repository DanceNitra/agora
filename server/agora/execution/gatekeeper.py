"""
The Gatekeeper — priority routing moves upstream.

One night of autonomous operation produced the evidence: themes the editorial layer rejects
(off-priority, already-skipped, zero-baseline internal names) kept being queued — SOC
Operations three times, Serotonin, vacuous project names — each skip burning a full Claude
cycle downstream. The fix is architectural: the SKIP LEDGER and the BOARD PRIORITIES belong
inside the queue generators, not behind them. Claude records every editorial skip here; the
dungeon consults the ledger (and the board) BEFORE queueing.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".skip_ledger.json"


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


def record_skip(theme: str, reason: str = "") -> dict | None:
    """One editorial skip = one ledger entry (deduped on the first 60 chars)."""
    t = (theme or "").strip()
    if len(t) < 6:
        return None
    items = _load()
    if any(t[:60].lower() in (x.get("theme", "").lower()) for x in items):
        for x in items:
            if t[:60].lower() in x.get("theme", "").lower():
                x["count"] = x.get("count", 1) + 1
                x["ts"] = time.time()
        _save(items)
        return None
    rec = {"theme": t[:160], "reason": (reason or "")[:200], "count": 1, "ts": time.time()}
    items.append(rec)
    _save(items[-200:])
    return rec


def skipped_themes(max_age_days: int = 30) -> list[str]:
    """Themes Claude editorially refused recently — the queue generators must not re-offer them."""
    cutoff = time.time() - max_age_days * 86400
    return [x["theme"] for x in _load() if x.get("ts", 0) >= cutoff]


def format_skips(n: int = 10) -> str:
    items = sorted(_load(), key=lambda x: -x.get("ts", 0))[:n]
    if not items:
        return "🚪 _The skip ledger is empty._"
    lines = ["🚪 *Skip ledger* — themes the editor refused (queue generators avoid these)"]
    for x in items:
        c = f" ×{x['count']}" if x.get("count", 1) > 1 else ""
        lines.append(f"• {x['theme'][:64]}{c}")
    return "\n".join(lines)
