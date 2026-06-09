"""
The Agora Mind — metacognition: the layer that turns a toolbox into a mind.

Agora has many capabilities (insight, prediction, dialectic, flywheel, teaching) but they fire on
timers, independently. This is the layer above them: it gathers EVERYTHING Agora currently knows —
its insights, its prediction track record, its dialectics, its open questions, its gaps — so Claude can
synthesize a coherent, evolving WORLDVIEW (what Agora believes, its strongest vs weakest beliefs, its
open tensions and uncertainties) AND decide what Agora should think about NEXT to become more coherent.
The output's NEXT MOVES are enqueued as real tasks, so Agora's cognition becomes self-directed instead
of timer-random.
"""
from __future__ import annotations

import asyncio
import glob
import re
from pathlib import Path

_WORLDVIEW = Path(__file__).resolve().parents[2] / ".worldview.md"


def _claim_of(text: str, title: str) -> str:
    """Pull the headline claim out of an insight/dialectic note."""
    for marker in (r"##+\s*The insight\s*\n+(.+?)(?:\n##|\Z)",
                   r"##+\s*Synthesis[^\n]*\n+(.+?)(?:\n##|\Z)",
                   r"\*\*(.+?)\*\*"):
        m = re.search(marker, text, re.DOTALL | re.IGNORECASE)
        if m:
            return re.sub(r"\s+", " ", re.sub(r"[*>#]", "", m.group(1))).strip()[:220]
    return title[:120]


async def gather_mind_state(vault_path: str) -> dict:
    """Collect Agora's entire current cognitive state for Claude to synthesize a worldview from."""
    from agora.execution.prediction_ledger import _load as _preds, calibration
    from agora.execution.flywheel import open_questions, stats as fw_stats
    from agora.execution.research_program import programs
    from agora.execution.user_model import get_model
    from agora.execution.semantic_index import SemanticIndex

    agora_dir = Path(vault_path) / "04 Resources" / "Concepts" / "Agora Agents"
    beliefs = []
    for pat in ("insight-*.md", "dialectic-*.md", "brief-*.md"):
        for f in sorted(glob.glob(str(agora_dir / "**" / pat), recursive=True))[-12:]:
            try:
                c = Path(f).read_text(encoding="utf-8", errors="replace")
                title = (re.search(r'title:\s*"?(.+?)"?\n', c) or [None, Path(f).stem])[1]
                beliefs.append({"title": title[:90], "claim": _claim_of(c, title)})
            except Exception:
                pass

    preds = _preds()
    cal = calibration()
    pred_view = [f"{p['direction']} {p.get('metric_label', '')} for {p['theme'][:40]} "
                 f"({p['confidence']:.0%}, {p['status']})" for p in preds[-8:]]
    si = SemanticIndex()
    gaps = [g["title"] for g in si.find_gaps(8)] if si.ready else []
    return {"beliefs": beliefs[-12:], "predictions": pred_view, "calibration": cal,
            "open_questions": [q["question"] for q in open_questions(8)], "flywheel": fw_stats(),
            "gaps": gaps, "programs": [p["question"] for p in programs(5)], "user": get_model()}


def record_worldview(content: str) -> str:
    try:
        _WORLDVIEW.write_text(content, encoding="utf-8")
    except Exception:
        pass
    return str(_WORLDVIEW)


def get_worldview() -> str:
    try:
        return _WORLDVIEW.read_text(encoding="utf-8")
    except Exception:
        return ""
