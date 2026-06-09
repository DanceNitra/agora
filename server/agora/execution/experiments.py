"""
Causal Self-Experiments — Agora upgrades itself on evidence, not vibes.

The Learning Loop derives correlational lessons; this adds causation. A process with a
measurable outcome gets two VARIANTS; units (themes, questions) are randomly but STABLY
assigned to a variant; outcomes are recorded as they arrive; once both arms have enough data
and one is clearly better, the experiment auto-decides and the winner becomes the default.
The owner's own discipline — causal inference — applied to the system itself.

First live experiment: `exam_answer_style` — does Agora score better on Claude-graded exams
answering mechanism-first or claim-evidence-structured? Outcome = grade per question (0-2).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".experiments.json"


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


def define(name: str, variants: list[str], desc: str = "") -> dict:
    """Register an experiment (idempotent — an existing one is returned untouched)."""
    d = _load()
    if name not in d:
        d[name] = {"name": name, "desc": desc[:200], "variants": list(variants)[:2],
                   "status": "running", "winner": None, "results": [], "ts": time.time()}
        _save(d)
    return d[name]


def assign(name: str, unit: str) -> str:
    """The unit's variant — DETERMINISTIC (hash), so re-asks get the same arm without storing
    an assignment table. Once decided, everyone gets the winner."""
    d = _load()
    e = d.get(name)
    if not e:
        return ""
    if e.get("winner"):
        return e["winner"]
    h = int(hashlib.sha256(f"{name}:{unit}".encode("utf-8")).hexdigest(), 16)
    return e["variants"][h % len(e["variants"])]


def record(name: str, unit: str, outcome: float) -> None:
    """Record one observed outcome for a unit (the variant is re-derived, so callers can't
    mislabel arms)."""
    d = _load()
    e = d.get(name)
    if not e or e.get("status") != "running":
        return
    e["results"].append({"unit": unit[:80], "variant": assign(name, unit),
                         "outcome": float(outcome), "ts": time.time()})
    e["results"] = e["results"][-400:]
    _save(d)
    _maybe_decide(name)


def _arm_stats(e: dict) -> dict:
    stats = {}
    for v in e["variants"]:
        xs = [r["outcome"] for r in e["results"] if r["variant"] == v]
        stats[v] = {"n": len(xs), "mean": round(sum(xs) / len(xs), 3) if xs else None}
    return stats


def _maybe_decide(name: str, min_n: int = 8, min_lift: float = 0.15) -> None:
    """Auto-decide when both arms have >=min_n outcomes and one mean is >=min_lift better
    (relative). Crude by design — a clear win or keep collecting."""
    d = _load()
    e = d.get(name)
    if not e or e.get("status") != "running":
        return
    s = _arm_stats(e)
    a, b = e["variants"]
    if s[a]["n"] >= min_n and s[b]["n"] >= min_n:
        ma, mb = s[a]["mean"], s[b]["mean"]
        base = max(abs(ma), abs(mb), 1e-9)
        if abs(ma - mb) / base >= min_lift:
            e["winner"] = a if ma > mb else b
            e["status"] = "decided"
            e["decided_ts"] = time.time()
            _save(d)


def winner(name: str) -> str | None:
    return (_load().get(name) or {}).get("winner")


def format_experiments() -> str:
    d = _load()
    if not d:
        return "🧪 _No experiments defined yet._"
    lines = ["🧪 *Causal self-experiments*"]
    for e in d.values():
        s = _arm_stats(e)
        arms = " vs ".join(f"{v} (n={s[v]['n']}, μ={s[v]['mean']})" for v in e["variants"])
        tail = f"→ *winner: {e['winner']}*" if e.get("winner") else "_collecting…_"
        lines.append(f"• `{e['name']}`: {arms} {tail}")
    return "\n".join(lines)
