"""
The Attention Economy — compute follows value.

Cognitive triggers fire on fixed cadences regardless of yield: an insight queue that keeps
finding every theme already covered burns the same attention as one striking gold. This tracks
each trigger's recent YIELD (did a run actually produce something?) and converts it into a
run-probability the dungeon consults before firing — bounded to [0.4, 1.0], so a cold streak
slows a trigger down by at most 2.5×, never kills it (it must keep sampling to notice the
world changed). The Custodian Principle applied to the system's own compute.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".attention.json"
_WINDOW = 10          # yield memory per trigger
_P_MIN, _P_MAX = 0.4, 1.0


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


def report(trigger: str, yielded: bool) -> None:
    """Record whether a trigger run produced something (queued a task, posted a finding…)."""
    d = _load()
    t = d.setdefault(trigger, {"runs": [], "ts": 0})
    t["runs"] = (t["runs"] + [1 if yielded else 0])[-_WINDOW:]
    t["ts"] = time.time()
    _save(d)


def policy() -> dict:
    """trigger -> run probability. Fewer than 3 samples = full attention (explore first)."""
    out = {}
    for name, t in _load().items():
        runs = t.get("runs", [])
        if len(runs) < 3:
            out[name] = _P_MAX
        else:
            out[name] = round(min(_P_MAX, max(_P_MIN, 0.4 + 0.6 * (sum(runs) / len(runs)))), 2)
    return out


def format_attention() -> str:
    d = _load()
    if not d:
        return "🧮 _No attention data yet — every trigger at full rate._"
    pol = policy()
    lines = ["🧮 *Attention economy* — run-probability by recent yield"]
    for name in sorted(d):
        runs = d[name].get("runs", [])
        rate = f"{sum(runs)}/{len(runs)}" if runs else "0/0"
        lines.append(f"• `{name}`: yield {rate} → p={pol.get(name, 1.0)}")
    return "\n".join(lines)
