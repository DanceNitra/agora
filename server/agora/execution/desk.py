"""
The Desk — Agora sets up the owner's working context.

Everything the system produces has lived NEXT TO the owner's day. The Desk steps into it:
when the senses see what Rasto is actually working on (his freshest vault edit), Agora lays
out the desk — his own relevant notes (including the ones he forgot he had), the freshest
papers on the topic, and the open research questions that touch it. Deterministic by design
(no LLM): gathering, not guessing. Delivered as a Telegram brief and a `Desk:` vault note.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path


async def compose_desk(vault_path: str, topic: str = "") -> dict:
    """Lay out the desk for a topic (default: the owner's freshest vault edit)."""
    from agora.execution.semantic_index import SemanticIndex
    from agora.execution.research_tool import research
    from agora.execution.senses import _vault_recent_edits
    from agora.execution.flywheel import open_questions

    edits = await asyncio.to_thread(_vault_recent_edits, vault_path, 48, 5)
    if not topic:
        topic = edits[0]["title"] if edits else ""
    if not topic:
        return {"topic": "", "reason": "nothing sensed and no topic given"}

    si = SemanticIndex()
    notes = []
    if si.ready:
        hits = await asyncio.to_thread(si.search, topic, 7)
        root = Path(vault_path)
        for h in hits:
            if h.get("score", 0) < 0.45 or h["title"].lower() == topic.lower():
                continue
            snippet = ""
            try:
                body = (root / h["path"]).read_text(encoding="utf-8", errors="replace")
                body = body.split("---", 2)[-1]          # drop frontmatter
                snippet = " ".join(body.split())[:180]
            except Exception:
                pass
            notes.append({"title": h["title"], "score": h["score"], "snippet": snippet})

    papers = await asyncio.to_thread(research, topic[:90], 3)
    papers = [{"title": p.get("title", ""), "url": p.get("url", ""),
               "published": p.get("published", p.get("year", ""))}
              for p in (papers or []) if p.get("title")][:3]

    tw = {w for w in topic.lower().split() if len(w) > 3}
    questions = [q["question"] for q in open_questions(10)
                 if tw & {w for w in q["question"].lower().split() if len(w) > 3}][:3]

    return {"topic": topic, "notes": notes[:6], "papers": papers,
            "questions": questions, "recent_edits": [e["title"] for e in edits],
            "ts": time.time()}


def format_desk(d: dict) -> str:
    if not d.get("topic"):
        return "🗂 _Nothing on the desk — no recent activity sensed._"
    lines = [f"🗂 *Your desk* — {d['topic'][:60]}"]
    if d.get("notes"):
        lines.append("*Your own notes on this:*")
        for n in d["notes"]:
            lines.append(f"  • {n['title'][:56]} _({n['score']:.2f})_")
    if d.get("papers"):
        lines.append("*Fresh literature:*")
        for p in d["papers"]:
            lines.append(f"  📄 {p['title'][:62]} _({p.get('published', '')})_")
    if d.get("questions"):
        lines.append("*Open questions that touch this:*")
        for q in d["questions"]:
            lines.append(f"  ❓ {q[:80]}")
    return "\n".join(lines)


def desk_note(d: dict) -> str:
    """The Desk as a vault note body (wikilinked, so the desk is a navigation hub)."""
    lines = [f"> Working context laid out by Agora — {time.strftime('%Y-%m-%d %H:%M')}.",
             "", "## Your notes"]
    lines += [f"- [[{n['title']}]] — {n['snippet'][:140]}" for n in d.get("notes", [])] or ["- (none found)"]
    lines += ["", "## Fresh literature"]
    lines += [f"- {p['title']} ({p.get('published', '')}) {p.get('url', '')}"
              for p in d.get("papers", [])] or ["- (none)"]
    if d.get("questions"):
        lines += ["", "## Open questions"]
        lines += [f"- {q}" for q in d["questions"]]
    return "\n".join(lines)
