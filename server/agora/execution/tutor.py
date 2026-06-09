"""
The Tutor — spaced repetition over the owner's own notes.

The dossier on "does the OS make its owner smarter" recommended exactly this: a daily 1-2
question micro-quiz drawn from the owner's evergreen concepts, scheduled SM-2 style (what you
knew comes back later; what you forgot comes back sooner), answered with one tap
(`got 1` / `forgot 1`). The retention rate feeds the Observatory's vitals — the owner's
memory becomes one of the system's measured organs.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".tutor.json"


def _load() -> dict:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {"cards": [], "outstanding": []}


def _save(d: dict) -> None:
    try:
        _STORE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


async def _make_card(vault_path: str, exclude: set[str]) -> dict | None:
    """One new card from a random evergreen concept (reuses the Exam's syllabus + flash Q)."""
    import asyncio
    from agora.execution.exam import _core_concepts
    from agora.execution.llm_client import call_llm
    pool = [c for c in await asyncio.to_thread(_core_concepts, vault_path, 8)
            if c["title"] not in exclude]
    if not pool:
        return None
    c = pool[0]
    q = await asyncio.to_thread(
        call_llm,
        "Write ONE short recall question a learner should be able to answer from memory if they "
        "understand the note (one concrete fact or mechanism, answerable in a sentence). "
        "Reply with the question only.",
        f"NOTE ({c['title']}):\n{c['snippet'][:1200]}", "cheap", 0.7, 200) or ""
    q = q.strip().splitlines()[0][:200] if q.strip() else ""
    if len(q) < 15:
        q = f"From memory: what is the core idea of your note '{c['title']}'?"
    return {"id": uuid.uuid4().hex[:6], "concept": c["title"], "question": q,
            "ef": 2.5, "interval": 0, "reps": 0, "lapses": 0,
            "due": time.time(), "history": []}


async def daily_quiz(vault_path: str, n: int = 2) -> dict:
    """Pick today's due cards (mint new ones when fewer than n are due). Marks them
    outstanding so `got 1` / `forgot 2` map to the right card."""
    d = _load()
    now = time.time()
    due = sorted([c for c in d["cards"] if c["due"] <= now], key=lambda c: c["due"])[:n]
    have = {c["concept"] for c in d["cards"]}
    while len(due) < n:
        card = await _make_card(vault_path, have)
        if not card:
            break
        d["cards"].append(card)
        have.add(card["concept"])
        due.append(card)
    d["cards"] = d["cards"][-300:]
    d["outstanding"] = [c["id"] for c in due]
    _save(d)
    return {"cards": due}


def grade(idx: int, ok: bool) -> dict:
    """SM-2-lite: got → interval 1d, 4d, then ×EF (EF +0.05, max 2.8); forgot → lapse,
    interval 1d, EF −0.2 (min 1.3)."""
    d = _load()
    out = d.get("outstanding", [])
    if not out or idx < 1 or idx > len(out):
        return {"error": "no such outstanding card"}
    card = next((c for c in d["cards"] if c["id"] == out[idx - 1]), None)
    if not card:
        return {"error": "card vanished"}
    if ok:
        card["reps"] += 1
        card["ef"] = min(2.8, card["ef"] + 0.05)
        card["interval"] = 1 if card["reps"] == 1 else (4 if card["reps"] == 2
                                                        else round(card["interval"] * card["ef"], 1))
    else:
        card["lapses"] += 1
        card["reps"] = 0
        card["ef"] = max(1.3, card["ef"] - 0.2)
        card["interval"] = 1
    card["due"] = time.time() + card["interval"] * 86400
    card["history"].append({"ts": time.time(), "ok": bool(ok)})
    card["history"] = card["history"][-30:]
    _save(d)
    return {"status": "ok", "concept": card["concept"], "ok": ok,
            "next_in_days": card["interval"]}


def retention_rate(last_n: int = 20) -> float | None:
    """Fraction of the most recent reviews the owner got right — the vitals metric."""
    reviews = []
    for c in _load()["cards"]:
        reviews += [(h["ts"], h["ok"]) for h in c.get("history", [])]
    reviews.sort()
    recent = [ok for _, ok in reviews[-last_n:]]
    return round(sum(recent) / len(recent), 3) if recent else None


def format_quiz(cards: list[dict]) -> str:
    if not cards:
        return "🎓 _Nothing due today._"
    lines = ["🎓 *Daily recall* — answer from memory, then check your note:"]
    for i, c in enumerate(cards, 1):
        lines.append(f"*{i}.* [{c['concept'][:34]}] {c['question']}")
    lines.append("_reply:_ `got 1` / `forgot 1` (and 2…)")
    return "\n".join(lines)
