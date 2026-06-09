"""
Research Programs — directed, persistent science toward a goal.

Reactive curation answers whatever wanders by. A research PROGRAM answers a question the user actually
cares about: decompose it into sub-questions, register those as research targets the agents pursue
(reusing the Flywheel queue), and — once findings accumulate — synthesize them into an answer. The leap
from drifting to driving.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".programs.json"


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(ps: list) -> None:
    try:
        _STORE.write_text(json.dumps(ps, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


async def start_program(question: str) -> dict:
    """Decompose a big question into sub-questions and dispatch them to the agents (via the Flywheel)."""
    from agora.execution.llm_client import call_llm
    from agora.execution.flywheel import register_question

    raw = await asyncio.to_thread(
        call_llm,
        "You are a research director. Break the big question into 3-5 sharp, INDEPENDENT, researchable "
        "sub-questions that together would answer it. Reply as numbered lines, nothing else.",
        f"BIG QUESTION: {question}", "cheap", 0.4, 320) or ""
    subs = [re.sub(r"^\s*\d+[.)]\s*", "", ln).strip() for ln in raw.splitlines()
            if re.match(r"^\s*\d+[.)]", ln)][:5]
    if not subs:
        subs = [question]
    for s in subs:
        register_question(s, origin=f"program: {question[:50]}")     # agents will research these
    prog = {"id": uuid.uuid4().hex[:8], "question": question[:200], "subquestions": subs,
            "status": "researching", "ts": time.time()}
    ps = _load()
    ps.append(prog)
    _save(ps[-50:])
    return prog


def programs(n: int = 10) -> list:
    return sorted(_load(), key=lambda p: -p.get("ts", 0))[:n]


def get_program(pid: str) -> dict | None:
    return next((p for p in _load() if p.get("id") == pid), None)


def mark_answered(pid: str, answer: str) -> None:
    ps = _load()
    for p in ps:
        if p.get("id") == pid:
            p["status"] = "answered"
            p["answer"] = answer[:600]
            p["answered_ts"] = time.time()
    _save(ps)


async def gather_program_findings(pid: str, vault_path: str) -> dict:
    """Gather the findings + literature relevant to a program's sub-questions, for Claude to
    synthesize an answer to the main question."""
    from agora.execution.research_tool import research, format_for_prompt
    p = get_program(pid)
    if not p:
        return {"error": "no such program"}
    lit_blocks = []
    for s in p["subquestions"][:4]:
        papers = await asyncio.to_thread(research, s[:90], 3)
        lit_blocks.append(f"[{s[:70]}]\n{format_for_prompt(papers)[:700]}")
    return {"question": p["question"], "subquestions": p["subquestions"],
            "evidence": "\n\n".join(lit_blocks)[:2400]}
