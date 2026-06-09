"""
Socratic Agora — the second-brain as a TUTOR.

Beyond storing knowledge, Agora teaches the person who owns it: it probes their understanding with
Socratic questions drawn from their own notes (testing depth, exposing assumptions, revealing the
frontier of what they do NOT yet know), and it recommends the highest-value thing to learn next from
the vault's real gaps. The vault stops being a passive store and becomes an active teacher.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path


async def socratic_questions(topic: str, vault_path: str) -> dict:
    """Probing questions drawn from the learner's OWN notes — test depth, expose assumptions, reveal
    the frontier of what they don't yet know."""
    from agora.execution.semantic_index import SemanticIndex
    from agora.execution.llm_client import call_llm

    si = SemanticIndex()
    hits = si.search(topic, 4) if si.ready else []
    root = Path(vault_path)
    snips = []
    for h in hits:
        try:
            txt = (root / h["path"]).read_text(encoding="utf-8", errors="replace")
            snips.append(f"- [{h['title']}] {txt[:280]}")
        except Exception:
            pass
    known = "\n".join(snips) or "(the vault is thin on this topic)"

    raw = await asyncio.to_thread(
        call_llm,
        "You are a Socratic tutor. From what the learner has noted about a topic, ask 4 PROBING "
        "questions that test DEEP understanding, expose a hidden assumption, connect it to something "
        "else, and push to the FRONTIER of what they do not yet know. Not trivia — questions that make "
        "them think hard. Reply as 4 numbered lines, nothing else.",
        f"TOPIC: {topic}\n\nWHAT THEY'VE NOTED:\n{known[:1600]}", "cheap", 0.6, 420) or ""
    qs = [re.sub(r"^\s*\d+[.)]\s*", "", ln).strip() for ln in raw.splitlines()
          if re.match(r"^\s*\d+[.)]", ln)]
    if not qs and raw.strip():
        qs = [ln.strip("-• ").strip() for ln in raw.splitlines() if len(ln.strip()) > 15][:4]
    return {"topic": topic, "questions": qs[:5], "based_on": [h["title"] for h in hits]}


async def what_to_learn_next(vault_path: str) -> dict:
    """Recommend the single highest-value thing to learn next, from the vault's real gaps."""
    from agora.execution.semantic_index import SemanticIndex
    from agora.execution.llm_client import call_llm

    si = SemanticIndex()
    gaps = si.find_gaps(8) if si.ready else []
    titles = [g["title"] for g in gaps]
    if not titles:
        return {"topic": "", "why": "", "gaps": []}
    raw = await asyncio.to_thread(
        call_llm,
        "You are a learning coach. Below are isolated topics in the learner's knowledge vault (their "
        "gaps). Pick the ONE most worth learning next — the one that would best connect and strengthen "
        "the rest — and say why in one sentence. Reply EXACTLY:\nTOPIC: <one of the gaps>\nWHY: <one sentence>",
        "\n".join(f"- {t}" for t in titles), "cheap", 0.4, 200) or ""
    tm = re.search(r"TOPIC:\s*(.+)", raw, re.I)
    wm = re.search(r"WHY:\s*(.+)", raw, re.DOTALL | re.I)
    topic = (tm.group(1).strip() if tm else titles[0])[:90]
    why = (re.sub(r"\s+", " ", wm.group(1)).strip()[:220] if wm else "")
    return {"topic": topic, "why": why, "gaps": titles[:6]}


def format_socratic(d: dict) -> str:
    if not d.get("questions"):
        return f"🎓 Not enough in your vault on _{d.get('topic', '')[:50]}_ to question yet."
    lines = [f"🎓 *Socratic check — {d['topic'][:60]}*\n"]
    for i, q in enumerate(d["questions"], 1):
        lines.append(f"*{i}.* {q}")
    if d.get("based_on"):
        lines.append(f"\n_drawn from your notes: {', '.join(d['based_on'][:3])}_")
    return "\n".join(lines)


def format_learn_next(d: dict) -> str:
    if not d.get("topic"):
        return "🎓 No clear gap to recommend right now."
    return (f"🎓 *Learn next:* {d['topic']}\n_{d.get('why', '')}_\n\n"
            f"_other open gaps: {', '.join(d.get('gaps', [])[1:5])}_")
