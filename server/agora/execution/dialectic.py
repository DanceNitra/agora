"""
Dialectic Engine — truth through structured opposition.

A single synthesis can be confidently wrong. The dialectic stress-tests a claim: build the strongest
case FOR it (thesis, steelmanned), then the strongest case AGAINST (antithesis, with real evidence),
then a SYNTHESIS that survives both — a sharper, qualified position. Knowledge that has passed through
the fire of its own best counter-argument is more trustworthy than a one-voice take.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path


async def run_dialectic(claim: str, vault_path: str) -> dict:
    """Thesis → antithesis → synthesis on a claim, grounded in the vault + the literature."""
    from agora.execution.semantic_index import SemanticIndex
    from agora.execution.research_tool import research, format_for_prompt
    from agora.execution.llm_client import call_llm

    si = SemanticIndex()
    hits = si.search(claim, 4) if si.ready else []
    root = Path(vault_path)
    snips = []
    for h in hits:
        try:
            txt = (root / h["path"]).read_text(encoding="utf-8", errors="replace")
            snips.append(f"- [{h['title']}] {txt[:240]}")
        except Exception:
            pass
    context = "\n".join(snips) or "(thin vault)"
    papers = await asyncio.to_thread(research, claim[:100], 4)
    lit = format_for_prompt(papers)[:1200]

    raw = await asyncio.to_thread(
        call_llm,
        "You run a DIALECTIC on a claim, using the notes and literature below. Build the strongest "
        "honest case FOR it, then the strongest case AGAINST (cite real evidence/tensions, do not "
        "strawman), then a SYNTHESIS — a sharper, qualified position that survives both. Reply in "
        "EXACTLY this form:\nTHESIS: <strongest case for>\nANTITHESIS: <strongest case against>\n"
        "SYNTHESIS: <the qualified position that holds>",
        f"CLAIM: {claim}\n\n[NOTES]\n{context[:1200]}\n\n[LITERATURE]\n{lit}", "cheap", 0.5, 700) or ""

    def _sec(label, nxt):
        m = re.search(rf"{label}:\s*(.+?)(?:\n\s*(?:{nxt}):|\Z)", raw, re.DOTALL | re.IGNORECASE)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    return {"claim": claim,
            "thesis": _sec("THESIS", "ANTITHESIS|SYNTHESIS")[:600],
            "antithesis": _sec("ANTITHESIS", "SYNTHESIS")[:600],
            "synthesis": (_sec("SYNTHESIS", "$") or raw.strip())[:600],
            "based_on": [h["title"] for h in hits]}


def format_dialectic(d: dict) -> str:
    if not d.get("synthesis"):
        return f"⚖️ Couldn't run the dialectic on _{d.get('claim', '')[:50]}_."
    return "\n".join([
        f"⚖️ *Dialectic — {d['claim'][:70]}*\n",
        f"✅ *Thesis:* {d['thesis']}",
        f"❌ *Antithesis:* {d['antithesis']}",
        f"🔷 *Synthesis:* {d['synthesis']}",
    ])
