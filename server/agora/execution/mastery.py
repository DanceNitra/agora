"""
Agent Mastery — standing follows the truth of one's findings.

The last piece of the reputation puzzle. Cooperation builds trust (ESS), calling the future
right builds forecast accuracy (the Tournament) — and now producing findings that SURVIVE
verification builds mastery. Every verification verdict is attributed to the agent who
contributed the finding: VERIFIED counts fully, OVERSTATED counts as a miss. The dungeon
blends mastery into standing, so curation authority finally tracks all three epistemic
virtues: being honest, being right about tomorrow, and being right about facts.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".mastery.json"


def _load() -> dict:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d: dict) -> None:
    try:
        _STORE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def record(agent: str, verdict: str) -> None:
    """Attribute a verification verdict to the finding's contributor."""
    name = (agent or "").strip()[:40]
    v = (verdict or "").strip().upper()
    if not name or v not in ("VERIFIED", "OVERSTATED", "UNSUPPORTED"):
        return                                  # INCONCLUSIVE teaches nothing about the agent
    d = _load()
    e = d.setdefault(name, {"total": 0, "verified": 0})
    e["total"] += 1
    e["verified"] += 1 if v == "VERIFIED" else 0
    e["ts"] = time.time()
    _save(d)


def scores() -> dict:
    """agent -> {total, verified, rate} (rate None until there's data)."""
    out = {}
    for name, e in _load().items():
        out[name] = {"total": e["total"], "verified": e["verified"],
                     "rate": round(e["verified"] / e["total"], 3) if e["total"] else None}
    return out


def format_mastery() -> str:
    s = scores()
    if not s:
        return "🏅 _No verified findings attributed yet._"
    lines = ["🏅 *Agent mastery* — whose findings survive verification"]
    for name, e in sorted(s.items(), key=lambda kv: -(kv[1]["rate"] or 0)):
        lines.append(f"• {name}: *{e['verified']}/{e['total']}*"
                     + (f" ({e['rate']:.0%})" if e["rate"] is not None else ""))
    return "\n".join(lines)
