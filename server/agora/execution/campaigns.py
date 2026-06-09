"""
Campaigns — sustained, multi-day research toward one goal.

A research program decomposes a question once and answers it once. A CAMPAIGN runs for DAYS:
its sub-questions become standing priorities, and on each tick it HARVESTS the findings that
have accumulated for each sub-question (semantic match against the live collective knowledge),
tracking coverage per sub-question over time. When every sub-question has enough evidence — or
the campaign's horizon passes — Claude writes the final dossier with a confidence per
sub-question. This is the one thing the organism couldn't do: hold a single goal longer than a
cycle.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".campaigns.json"


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(cs: list) -> None:
    try:
        _STORE.write_text(json.dumps(cs, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def get_campaign(cid: str) -> dict | None:
    return next((c for c in _load() if c.get("id") == cid), None)


def list_campaigns(n: int = 10) -> list:
    return sorted(_load(), key=lambda c: -c.get("ts", 0))[:n]


async def start_campaign(question: str, horizon_days: int = 5) -> dict:
    """Decompose the goal into sub-questions (reusing the program decomposer), register them as
    standing research priorities, and open a multi-day campaign that harvests over time."""
    from agora.execution.research_program import start_program
    prog = await start_program(question)          # decompose + register on the flywheel
    camp = {"id": uuid.uuid4().hex[:8], "question": question[:200],
            "subquestions": prog["subquestions"],
            "coverage": {s: 0 for s in prog["subquestions"]},
            "status": "running", "ts": time.time(),
            "deadline": time.time() + horizon_days * 86400, "ticks": 0}
    cs = _load()
    cs.append(camp)
    _save(cs[-40:])
    return camp


async def harvest_tick(cid: str, db) -> dict:
    """One day's harvest: for each sub-question, count the supporting findings that have
    accumulated in the collective knowledge (semantic match), updating coverage."""
    from agora.execution.semantic_index import _embed_batch
    import numpy as np
    c = get_campaign(cid)
    if not c or c.get("status") != "running":
        return {"error": "no running campaign"}

    cur = await db.execute(
        "SELECT title, content FROM collective_knowledge WHERE knowledge_type='discovery' "
        "ORDER BY created_at DESC LIMIT 200")
    rows = await cur.fetchall()
    finds = [f"{(r['title'] or '')}. {(r['content'] or '')[:200]}" for r in rows if r["title"]]
    subs = c["subquestions"]
    if finds and subs:
        embs = await asyncio.to_thread(_embed_batch, subs + finds)
        if embs and len(embs) == len(subs) + len(finds):
            m = np.array(embs, dtype=np.float32)
            m /= (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
            sq, fd = m[:len(subs)], m[len(subs):]
            sims = sq @ fd.T                      # sub-question × finding cosine
            for i, s in enumerate(subs):
                c["coverage"][s] = int((sims[i] > 0.62).sum())
    c["ticks"] = c.get("ticks", 0) + 1
    enough = all(v >= 3 for v in c["coverage"].values())
    due = time.time() >= c.get("deadline", 0)
    c["ready"] = bool(enough or (due and any(v > 0 for v in c["coverage"].values())))
    _save([c if x["id"] == cid else x for x in _load()])
    return {"id": cid, "coverage": c["coverage"], "ready": c["ready"],
            "enough": enough, "due": due, "ticks": c["ticks"]}


async def gather_dossier_inputs(cid: str) -> dict:
    """All evidence for the final dossier: per sub-question, the literature plus the campaign's
    accumulated coverage — for Claude to synthesize a graded answer."""
    from agora.execution.research_tool import research, format_for_prompt
    c = get_campaign(cid)
    if not c:
        return {"error": "no such campaign"}
    blocks = []
    for s in c["subquestions"][:5]:
        papers = await asyncio.to_thread(research, s[:90], 3)
        blocks.append(f"### {s}\n(findings gathered: {c['coverage'].get(s, 0)})\n"
                      f"{format_for_prompt(papers)[:650]}")
    return {"question": c["question"], "subquestions": c["subquestions"],
            "coverage": c["coverage"], "evidence": "\n\n".join(blocks)[:3200]}


def mark_complete(cid: str, dossier_path: str = "") -> None:
    cs = _load()
    for c in cs:
        if c.get("id") == cid:
            c["status"] = "complete"
            c["dossier"] = dossier_path
            c["completed_ts"] = time.time()
    _save(cs)


def format_campaigns(n: int = 6) -> str:
    cs = list_campaigns(n)
    if not cs:
        return "🎯 _No campaigns running._"
    lines = ["🎯 *Research campaigns*"]
    for c in cs:
        cov = c.get("coverage", {})
        done = sum(1 for v in cov.values() if v >= 3)
        flag = {"running": "▶️", "complete": "✅"}.get(c["status"], "•")
        lines.append(f"{flag} `{c['id']}` {c['question'][:54]}")
        lines.append(f"    {done}/{len(cov)} sub-questions covered · day {c.get('ticks', 0)}"
                     + (" · ready" if c.get("ready") and c["status"] == "running" else ""))
    return "\n".join(lines)
