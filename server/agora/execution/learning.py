"""
The Learning Loop — Agora gets better at being Agora.

The system has a mind, but it does not yet learn from how its judgments turn out. This closes that
loop: it gathers OUTCOMES (which predictions resolved correct/incorrect and at what confidence, how
selective the funnel is, how many claims survived the flywheel) and derives LESSONS — concrete, applied
rules about what works ("FLAT is right for slow metrics; reserve high confidence for small fast-growing
bases"). The lessons are then INJECTED back into the gather endpoints that feed Claude, so the next
prediction / insight / reflection is informed by every past outcome. Outcome → lesson → better behavior.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_LESSONS = Path(__file__).resolve().parents[2] / ".lessons.json"


def get_lessons() -> list:
    try:
        return json.loads(_LESSONS.read_text(encoding="utf-8")).get("lessons", [])
    except Exception:
        return []


def lessons_text() -> str:
    ls = get_lessons()
    return "\n".join(f"- {x}" for x in ls) if ls else ""


def record_lessons(lessons: list) -> dict:
    data = {"lessons": [str(x)[:300] for x in lessons][:12], "ts": time.time()}
    try:
        _LESSONS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
    return data


async def gather_outcomes() -> dict:
    """Collect the measurable outcomes of Agora's own judgments — the raw material for lessons."""
    from agora.execution.prediction_ledger import _load as _preds, calibration
    from agora.execution.flywheel import stats as fw_stats

    preds = _preds()
    resolved = [{"theme": p["theme"][:50], "direction": p["direction"], "metric": p.get("metric"),
                 "confidence": p["confidence"], "outcome": p["status"], "actual": p.get("actual"),
                 "by": p.get("by", "flash"), "why": p.get("why", "")[:120]}
                for p in preds if p.get("status") in ("correct", "incorrect")]
    # calibration of pending calls too: how many are lazy FLAT vs directional, flash vs claude
    flat = sum(1 for p in preds if p.get("direction") == "FLAT")
    claude_made = sum(1 for p in preds if p.get("by") == "claude")
    return {"calibration": calibration(), "resolved": resolved,
            "ledger_shape": {"total": len(preds), "flat_calls": flat, "claude_made": claude_made,
                             "directional": len(preds) - flat},
            "flywheel": fw_stats(), "current_lessons": get_lessons()}


def format_lessons() -> str:
    ls = get_lessons()
    if not ls:
        return "🎓 No lessons learned yet — Agora reflects on its track record ~daily."
    return "🎓 *What Agora has learned about itself*\n" + "\n".join(f"• {x}" for x in ls)
