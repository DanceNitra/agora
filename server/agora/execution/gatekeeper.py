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


def _skip_words(t: str) -> set:
    """The theme's content words, split the way the dungeon's consumer splits them.

    `agent_worker` filters a lead when >= 50% of a stored theme's words appear in it, so dedup has
    to reason in the same units. Comparing raw substrings instead is what let a one-word theme be
    absorbed by an unrelated slug that merely contained it.
    """
    import re as _re
    return {w for w in _re.split(r"[^a-z0-9]+", (t or "").lower()) if len(w) > 2}


def record_skip(theme: str, reason: str = "") -> dict:
    """One editorial skip = one ledger entry.

    DEDUP IS DIRECTIONAL, and it used to run the wrong way. The old rule bumped an existing entry
    whenever the new theme appeared anywhere inside it as a substring, so a GENERAL theme was
    swallowed by any longer SPECIFIC entry that happened to contain it. Measured 2026-09-06: the
    board calls reranking a dead end, `record_skip("reranking")` reported nothing recorded, and the
    entry it had merged into was a Reddit slug,
    `xWhX61651H8_n8n_just_leveled_up_rag_agents_reranking_metadat`. The consumer needs >= 50% of a
    theme's words to fire, so that slug filters no lead about reranking, and the skip I had just
    performed did nothing at all. A hole in the EXCLUDING direction, which is the expensive one.

    Now two themes are the same theme only when their word sets match, or when the smaller set is
    contained in the larger AND has at least two words. One word is never enough to be absorbed.

    Returns a dict carrying `status`: `recorded`, `deduped` or `refused`. It used to return None for
    both `refused` and `deduped`, so the caller could not tell a rejected theme from a merged one.
    """
    t = (theme or "").strip()
    if len(t) < 6:
        return {"status": "refused", "theme": t, "why": "under six characters"}
    items = _load()
    tw = _skip_words(t)
    for x in items:
        xw = _skip_words(x.get("theme", ""))
        if not tw or not xw:
            continue
        same = (tw == xw) or (tw < xw and len(tw) >= 2) or (xw < tw and len(xw) >= 2)
        if same:
            x["count"] = x.get("count", 1) + 1
            x["ts"] = time.time()
            _save(items)
            return {"status": "deduped", "theme": t, "merged_into": x.get("theme", "")[:160]}
    rec = {"theme": t[:160], "reason": (reason or "")[:200], "count": 1, "ts": time.time()}
    items.append(rec)
    _save(items[-200:])
    return dict(rec, status="recorded")


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
