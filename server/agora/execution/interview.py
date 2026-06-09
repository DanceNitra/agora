"""
The Interview — Agora asks its owner.

Information has only flowed TO Rasto; back come only commands. This closes the owner loop:
once a day Agora composes the ONE question whose answer it most needs — an ambiguity in the
user model, a falsifier only human judgment can settle, a clarification about what he is
actually working on right now — and asks it on Telegram. The answer is recorded as a
first-class vault note, so it feeds the user model, semantic search, and every future
synthesis. The cheapest source of the highest-grade signal the system can get.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".interview.json"


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


def open_question() -> dict | None:
    """The most recent asked-but-unanswered question, if any."""
    return next((q for q in reversed(_load()) if q.get("status") == "asked"), None)


async def compose_question(vault_path: str) -> dict:
    """Pick the single highest-value question for the owner, grounded in what Agora actually
    doesn't know: today's activity, open falsifiers needing judgment, the user model."""
    import asyncio
    from agora.execution.llm_client import call_llm
    from agora.execution.senses import sense_today
    from agora.execution.flywheel import open_questions
    from agora.execution.user_model import build_user_model

    today = await asyncio.to_thread(sense_today, vault_path)
    model = await build_user_model(vault_path)
    fws = open_questions(4)
    edits = ", ".join(e["title"] for e in today.get("vault_edits", [])[:4]) or "(none seen)"
    fw_txt = "\n".join(f"- {q['question'][:140]}" for q in fws) or "(none)"

    raw = await asyncio.to_thread(
        call_llm,
        "You are a research assistant who may ask the OWNER one question per day. Compose the "
        "single MOST VALUABLE question: prefer (a) resolving which current activity matters "
        "most and why, (b) a judgment call one of the open research questions needs from a "
        "human, or (c) a real gap in the owner profile. CONCRETE and answerable in 2-3 "
        "sentences, not philosophical. Reply EXACTLY:\nQUESTION: <one question>\nWHY: <one line>",
        f"OWNER DOMAINS: {model.get('domains', '?')}\nTODAY HE TOUCHED: {edits}\n"
        f"OPEN RESEARCH QUESTIONS:\n{fw_txt}", "cheap", 0.6, 250) or ""
    q = w = ""
    for ln in raw.splitlines():
        if ln.upper().startswith("QUESTION:"):
            q = ln.split(":", 1)[1].strip()
        elif ln.upper().startswith("WHY:"):
            w = ln.split(":", 1)[1].strip()
    if len(q) < 15:               # flash flaked — deterministic fallback, still grounded
        q = (f"You recently touched: {edits}. Which of these matters most this week, "
             "and what outcome would make it a win?")
        w = "fallback: anchor the system to your current priority"
    rec = {"id": uuid.uuid4().hex[:6], "ts": time.time(), "question": q[:300],
           "why": w[:160], "status": "asked", "answer": ""}
    items = _load()
    items.append(rec)
    _save(items[-200:])
    return rec


def record_answer(text: str) -> dict | None:
    """Attach the owner's answer to the open question; the caller writes the vault note."""
    items = _load()
    hit = None
    for q in reversed(items):
        if q.get("status") == "asked":
            q["status"] = "answered"
            q["answer"] = (text or "").strip()[:1500]
            q["answer_ts"] = time.time()
            hit = q
            break
    if hit:
        _save(items)
    return hit


def format_interview(n: int = 5) -> str:
    items = _load()[-n:]
    if not items:
        return "💬 _No interview questions yet._"
    lines = ["💬 *The Interview* — Agora ↔ you"]
    for q in items:
        mark = "❓" if q["status"] == "asked" else "✅"
        lines.append(f"{mark} {q['question'][:90]}")
        if q.get("answer"):
            lines.append(f"   ↳ _{q['answer'][:90]}_")
    if any(q["status"] == "asked" for q in items):
        lines.append("_reply with:_ `answer <your answer>`")
    return "\n".join(lines)
