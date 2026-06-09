"""
The Exam — is Agora (and its owner) actually getting smarter?

A measurable benchmark loop: periodically Agora generates a fixed-size Socratic exam from the
vault's core (evergreen) concepts, ANSWERS it itself with the light model, and queues the answer
sheet for Claude to grade against the source notes. Scores land in a ledger, so capability growth
becomes a NUMBER with a time series instead of a feeling. The same questions can be sent to the
owner via Telegram (`exam`) — free spaced repetition over their own knowledge.
"""
from __future__ import annotations

import asyncio
import json
import random
import re
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".exams.json"
_SKIP_DIRS = (".obsidian", ".git", "Agora Agents", ".trash")


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(exams: list) -> None:
    try:
        _STORE.write_text(json.dumps(exams, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _core_concepts(vault_path: str, n: int) -> list[dict]:
    """Sample n evergreen concept notes (the owner's settled knowledge — the exam syllabus)."""
    root = Path(vault_path)
    pool = []
    try:
        for p in root.rglob("*.md"):
            sp = str(p)
            if any(s in sp for s in _SKIP_DIRS):
                continue
            try:
                head = p.read_text(encoding="utf-8", errors="replace")[:2200]
            except Exception:
                continue
            if "status: evergreen" in head and len(head) > 700:
                pool.append({"title": p.stem, "snippet": head})
    except Exception:
        pass
    return random.sample(pool, min(n, len(pool)))


async def generate_exam(vault_path: str, n: int = 6) -> dict:
    """Draw one probing question per core concept, then have Agora (flash) answer open-book.
    The answer sheet is stored ungraded — Claude grades it against the snippets (inbox task)."""
    from agora.execution.llm_client import call_llm
    concepts = await asyncio.to_thread(_core_concepts, vault_path, n)
    if not concepts:
        return {"status": "empty", "reason": "no evergreen concepts found"}

    def _q_and_a(c: dict) -> dict | None:
        q = call_llm(
            "Write ONE probing exam question that tests real UNDERSTANDING of the concept in the "
            "note below (not recall of a definition — a why/what-breaks/connect question). "
            "Reply with the question only.",
            f"NOTE ({c['title']}):\n{c['snippet'][:1500]}", "cheap", 0.7, 200) or ""
        q = q.strip().splitlines()[0][:240] if q.strip() else ""
        if len(q) < 15:
            return None
        a = call_llm(
            "Answer the exam question in 3-5 sentences using the note as your source. Be precise; "
            "state mechanisms, not platitudes.",
            f"NOTE ({c['title']}):\n{c['snippet'][:1500]}\n\nQUESTION: {q}", "cheap", 0.4, 400) or ""
        if len(a.strip()) < 30:
            return None
        return {"concept": c["title"], "question": q, "agora_answer": a.strip()[:900],
                "snippet": c["snippet"][:900]}

    # sequential on purpose: concurrent flash calls get rate-limited into empty outputs
    questions = []
    for c in concepts:
        r = await asyncio.to_thread(_q_and_a, c)
        if r:
            questions.append(r)
    if len(questions) < 3:
        return {"status": "empty", "reason": "flash produced too few usable Q&A"}
    exam = {"id": uuid.uuid4().hex[:8], "ts": time.time(), "questions": questions,
            "status": "answered", "score": None, "max": 2 * len(questions)}
    exams = _load()
    exams.append(exam)
    _save(exams[-40:])
    return {"status": "ok", **exam}


def grade_exam(exam_id: str, scores: list, feedback: str = "") -> dict:
    """Record Claude's grading: one 0-2 score per question. Total becomes the ledger point."""
    exams = _load()
    for e in exams:
        if e.get("id") == exam_id and e.get("status") == "answered":
            qs = e.get("questions", [])
            clean = [max(0, min(2, int(s))) for s in scores][:len(qs)]
            for q, s in zip(qs, clean):
                q["score"] = s
            e["score"] = sum(clean)
            e["max"] = 2 * len(qs)
            e["feedback"] = (feedback or "")[:600]
            e["status"] = "graded"
            e["graded_ts"] = time.time()
            _save(exams)
            return {"status": "ok", "score": e["score"], "max": e["max"]}
    return {"status": "not_found"}


def exam_history(limit: int = 12) -> dict:
    """The capability time series + the latest exam (full sheet for grading/inspection)."""
    exams = _load()
    series = [{"id": e["id"], "ts": e["ts"], "score": e.get("score"), "max": e.get("max"),
               "status": e.get("status")} for e in exams][-limit:]
    return {"series": series, "latest": exams[-1] if exams else None}


def format_exam_questions(exam: dict) -> str:
    """The questions only (no Agora answers) — for the owner to self-test on Telegram."""
    qs = exam.get("questions", [])
    if not qs:
        return "_No exam available._"
    lines = ["📝 *Exam over your own knowledge* — answer mentally, then check your notes:\n"]
    for i, q in enumerate(qs, 1):
        lines.append(f"*{i}. [{q['concept'][:36]}]* {q['question']}")
    return "\n".join(lines)
