"""
The Bounty Ledger — science pays for kills, not just production.

Every other reward stream in the organism pays for OUTPUT (notes shipped, findings verified,
forecasts landed). Nothing paid for DESTRUCTION — yet a research system without a funded
adversary is a blog. This ledger records the outcome of every belief challenge: a kill
(belief revised or retired) earns the challenger full credit, a survival earns a quarter
(running a severe test is real scientific work even when the belief holds — that is what
makes the survivor stronger). The resulting kill-authority feeds the dungeon's standing
blend, giving Sergeant Voss an income stream from rigor.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".bounty.json"
_KILL_VERDICTS = ("revised", "retired")


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


def record_challenge(verdict: str, target: str, by_agent: str = "Sergeant Voss") -> dict | None:
    """Ledger one resolved belief challenge. verdict: survived | revised | retired."""
    v = (verdict or "").strip().lower()
    if v not in ("survived", "revised", "retired"):
        return None
    rec = {"verdict": v, "kill": v in _KILL_VERDICTS, "target": (target or "")[:120],
           "by": (by_agent or "Sergeant Voss")[:40], "ts": time.time()}
    items = _load()
    items.append(rec)
    _save(items[-200:])
    return rec


def scores() -> dict:
    """Kill-authority per agent (0..1): (kills + 0.25*survivals) / attempts.
    All kills -> 1.0; all survivals -> 0.25 (severe testing still pays); needs >=2 attempts
    before it counts, so one lucky kill doesn't mint authority."""
    by: dict[str, dict] = {}
    for r in _load():
        a = by.setdefault(r.get("by", "?"), {"attempts": 0, "kills": 0})
        a["attempts"] += 1
        a["kills"] += 1 if r.get("kill") else 0
    out = {}
    for name, a in by.items():
        if a["attempts"] >= 2:
            survived = a["attempts"] - a["kills"]
            out[name] = round((a["kills"] + 0.25 * survived) / a["attempts"], 3)
    return out


def format_bounty() -> str:
    items = _load()
    if not items:
        return "🗡 _The bounty board is empty — no belief has been challenged to resolution._"
    kills = sum(1 for x in items if x.get("kill"))
    lines = [f"🗡 *The Bounty Ledger* — {kills} kills / {len(items)} challenges"]
    for r in items[-6:][::-1]:
        icon = "💀" if r.get("kill") else "🛡"
        lines.append(f"{icon} [{r['verdict']}] {r['target'][:60]} — {r['by']}")
    sc = scores()
    if sc:
        lines.append("authority: " + ", ".join(f"{k} {v}" for k, v in sc.items()))
    return "\n".join(lines)
