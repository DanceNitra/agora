"""
Compounding Flywheel — knowledge that DEEPENS, not just widens.

Agora's outputs become its next inputs. Every insight ships with a FALSIFIER (a testable weak point);
the flywheel registers those falsifiers (and vault contradictions) as OPEN QUESTIONS, feeds them to the
agents as high-priority research targets, and then DEEPENS the insight with the evidence that comes
back. Each turn of the wheel makes a claim sharper and better-tested. Over time the vault converges
toward a coherent, stress-tested worldview instead of a growing pile of one-shot notes.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".flywheel.json"


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(qs: list) -> None:
    try:
        _STORE.write_text(json.dumps(qs, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def extract_falsifier(insight_content: str) -> str:
    """Pull the falsifier (the testable weak point) out of an insight note."""
    m = re.search(r"(?:^|\n)\s*#*\s*Falsifier[:\s]*\n?(.+?)(?:\n##|\Z)", insight_content,
                  re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:260] if m else ""


def register_question(question: str, origin: str = "") -> dict | None:
    """Register an open research question (an insight's falsifier or a contradiction) for the agents."""
    q = re.sub(r"\s+", " ", question or "").strip()
    if len(q) < 20:
        return None
    qs = _load()
    if any(q[:80].lower() in (x.get("question", "").lower()) for x in qs):   # dedup
        return None
    rec = {"id": uuid.uuid4().hex[:8], "question": q[:280], "origin": origin[:120],
           "status": "open", "ts": time.time()}
    qs.append(rec)
    _save(qs[-200:])
    return rec


def open_questions(n: int = 6) -> list:
    return [q for q in sorted(_load(), key=lambda x: -x.get("ts", 0)) if q.get("status") == "open"][:n]


def mark_deepened(qid: str) -> None:
    qs = _load()
    for q in qs:
        if q.get("id") == qid:
            q["status"] = "deepened"
            q["deepened_ts"] = time.time()
    _save(qs)


def stats() -> dict:
    qs = _load()
    return {"total": len(qs), "open": sum(1 for q in qs if q.get("status") == "open"),
            "deepened": sum(1 for q in qs if q.get("status") == "deepened")}


async def gather_deepening_inputs(insight_title: str, falsifier: str, vault_path: str) -> dict:
    """Test an insight's FALSIFIER against fresh research + real-world data — the evidence a stronger
    model (Claude) uses to DEEPEN the insight (does the weak point hold up?)."""
    from agora.execution.research_tool import research, format_for_prompt
    from agora.execution.data_tool import empirical_test
    probe = falsifier or insight_title
    papers = await asyncio.to_thread(research, probe[:100], 5)
    try:
        real = await empirical_test(probe[:120])
        real_view = f"{real.get('verdict')} via {real.get('source')}: {real.get('evidence', '')}"
    except Exception:
        real_view = "(no real-world data)"
    return {"insight_title": insight_title, "falsifier": falsifier,
            "literature": format_for_prompt(papers)[:1800], "reality": real_view[:200]}
