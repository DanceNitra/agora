"""
AGORA 2.0 — Pillar 1: the vault that thinks.

Turns the user's notes from searchable text into a reasoned belief: extract atomic CLAIMS
(subject, relation, object, confidence, source) from the topic-relevant notes, then surface what
the vault collectively BELIEVES, how firmly, and where it CONTRADICTS itself. On-demand per topic
(cheap) — the substrate for the full Epistemic Dependency Graph.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path


def _parse_json(raw: str, key: str) -> list:
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(0)).get(key, []) or []
    except Exception:
        return []


async def extract_claims(notes: list[tuple[str, str]]) -> list[dict]:
    """notes: [(title, content)] → atomic claims [{s, r, o, conf, src}]."""
    from agora.execution.llm_client import call_llm
    block = "\n\n".join(f"[{t}]\n{c[:700]}" for t, c in notes if c)
    raw = await asyncio.to_thread(
        call_llm,
        "Extract the atomic factual CLAIMS these notes assert. For each: subject (s), relation (r), "
        "object (o), a confidence 0-1 (conf — how firmly the note asserts it; lower if hedged or "
        "speculative), and the source note title (src). Reply ONLY JSON: "
        '{"claims":[{"s":"","r":"","o":"","conf":0.0,"src":""}]}. Max 14. Skip meta/structure/todos.',
        block, "cheap", 0.1, 1000)
    out = []
    for c in _parse_json(raw, "claims"):
        if c.get("s") and c.get("r") and c.get("o"):
            out.append({"s": str(c["s"])[:80], "r": str(c["r"])[:60], "o": str(c["o"])[:120],
                        "conf": float(c.get("conf", 0.5)), "src": str(c.get("src", ""))[:80]})
    return out


async def find_contradictions(claims: list[dict]) -> list[dict]:
    """Pairs of claims that cannot both be true."""
    from agora.execution.llm_client import call_llm
    if len(claims) < 2:
        return []
    lst = "\n".join(f"{i}. {c['s']} — {c['r']} — {c['o']}  (src: {c['src']})"
                    for i, c in enumerate(claims))
    raw = await asyncio.to_thread(
        call_llm,
        "Below are claims extracted from a person's notes. Find pairs that genuinely CONTRADICT (they "
        "cannot both be true) — not merely different topics. Reply ONLY JSON: "
        '{"contradictions":[{"a":"<claim a>","b":"<claim b>","why":"<one sentence>"}]}. Empty list if none.',
        lst, "cheap", 0.1, 600)
    return _parse_json(raw, "contradictions")


async def believe(topic: str, vault_path: str, k: int = 8) -> dict:
    """What does the vault believe about a topic? Claims + confidence + contradictions + sources."""
    from agora.execution.semantic_index import SemanticIndex
    si = SemanticIndex()
    hits = si.search(topic, k) if si.ready else []
    notes, sources = [], []
    root = Path(vault_path)
    for h in hits:
        try:
            txt = (root / h["path"]).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        notes.append((h["title"], txt))
        sources.append(h["title"])
    if not notes:
        return {"topic": topic, "claims": [], "contradictions": [], "sources": []}
    claims = await extract_claims(notes)
    contradictions = await find_contradictions(claims)
    return {"topic": topic, "claims": claims, "contradictions": contradictions, "sources": sources}


def format_belief(b: dict) -> str:
    """Compact markdown — what the vault believes about the topic."""
    claims = sorted(b.get("claims", []), key=lambda c: -c.get("conf", 0))
    if not claims:
        return f"🧠 *{b['topic']}* — your vault has no clear claims here (a gap)."
    lines = [f"🧠 *What your vault believes about {b['topic'][:60]}*\n"]
    for c in claims[:8]:
        mark = "🟢" if c["conf"] >= 0.7 else ("🟡" if c["conf"] >= 0.45 else "🟠")
        lines.append(f"{mark} {c['s']} **{c['r']}** {c['o']}  _[[{c['src']}]]_")
    cons = b.get("contradictions", [])
    if cons:
        lines.append("\n⚔️ *Contradictions:*")
        for c in cons[:4]:
            lines.append(f"• {c.get('a', '')[:60]} ↔ {c.get('b', '')[:60]} — _{c.get('why', '')[:80]}_")
    return "\n".join(lines)
