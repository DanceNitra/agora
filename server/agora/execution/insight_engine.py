"""
Insight Engine — the leap from knowledge COLLECTOR to knowledge CREATOR.

Agora has three independent groundings for any theme: what the user's vault BELIEVES (knowledge_graph),
what the LITERATURE says (research_tool, arXiv/OpenAlex), and what REAL-WORLD DATA shows (Reality
Bridge). This engine gathers all three and synthesizes ONE genuinely NEW insight — a specific,
non-obvious, falsifiable claim that follows from integrating all three but is stated in none of them.
That is original synthesis: knowledge that did not exist in any single source.
"""
from __future__ import annotations

import asyncio
import json
import re


async def synthesize_insight(theme: str, vault_path: str) -> dict:
    """Gather vault notes + literature + real-world data on a theme → one NEW integrated insight."""
    from pathlib import Path
    from agora.execution.llm_client import call_llm
    from agora.execution.semantic_index import SemanticIndex
    from agora.execution.research_tool import research, format_for_prompt
    from agora.execution.data_tool import empirical_test

    # 1) what the VAULT holds — relevant note snippets (semantic search; fast + reliable, no slow
    #    claim-extraction step which timed out/emptied on the flaky LLM).
    si = SemanticIndex()
    hits = si.search(theme, 5) if si.ready else []
    root = Path(vault_path)
    snips = []
    for h in hits:
        try:
            txt = (root / h["path"]).read_text(encoding="utf-8", errors="replace")
            snips.append(f"- [{h['title']}] {txt[:300]}")
        except Exception:
            pass
    vault_view = "\n".join(snips) or "(the vault is thin on this theme)"
    claims = hits
    # 2) the LITERATURE
    papers = await asyncio.to_thread(research, theme, 5)
    lit = format_for_prompt(papers)
    # 3) REAL-WORLD DATA (Reality Bridge)
    try:
        real = await empirical_test(theme)
        real_view = f"{real.get('verdict')} via {real.get('source')}: {real.get('evidence', '')}"
    except Exception:
        real, real_view = {}, "(no real-world data)"

    # Plain LABELED-TEXT output, not JSON: deepseek-v4-flash reliably returns empty on the complex
    # JSON synthesis but handles a simple labeled format well.
    sys_p = (
        "You are a research theorist. Connect the three views below — a person's knowledge vault, the "
        "academic literature, and real-world data — into ONE genuinely NEW, specific, FALSIFIABLE "
        "insight that follows from integrating all three but is stated in none of them (no summary, no "
        "platitudes). Reply in EXACTLY this form, nothing else:\n"
        "INSIGHT: <the new claim, 1-2 sentences>\n"
        "WHY: <how the three sources combine to it, 1 sentence>\n"
        "FALSIFIER: <one observation that would refute it>")
    usr = (f"THEME: {theme}\n\n[VAULT]\n{vault_view[:1400]}\n\n[LITERATURE]\n{lit[:1200]}\n\n"
           f"[REAL-WORLD DATA]\n{real_view[:300]}")

    out = {"theme": theme, "insight": "", "reasoning": "", "confidence": 0.0, "falsifier": "",
           "grounding": {"vault_claims": len(claims), "papers": len(papers), "reality": real_view[:120]}}
    raw = await asyncio.to_thread(call_llm, sys_p, usr, "cheap", 0.5, 600) or ""
    if not raw.strip():
        raw = await asyncio.to_thread(call_llm, sys_p, usr, "cheap", 0.7, 600) or ""

    def _sec(label: str, nxt: str) -> str:
        m = re.search(rf"{label}:\s*(.+?)(?:\n\s*(?:{nxt}):|$)", raw, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""
    out["insight"] = (_sec("INSIGHT", "WHY|FALSIFIER") or raw.strip())[:500]
    out["reasoning"] = _sec("WHY", "FALSIFIER")[:400]
    out["falsifier"] = _sec("FALSIFIER", "")[:300]
    out["confidence"] = 0.6 if out["insight"] else 0.0
    return out


async def gather_insight_inputs(theme: str, vault_path: str) -> dict:
    """Gather the THREE groundings (vault notes + literature + real-world data) for a theme WITHOUT
    synthesizing — the raw evidence for a stronger model (Claude) to synthesize the insight itself."""
    from pathlib import Path
    from agora.execution.semantic_index import SemanticIndex
    from agora.execution.research_tool import research, format_for_prompt
    from agora.execution.data_tool import empirical_test

    si = SemanticIndex()
    hits = si.search(theme, 6) if si.ready else []
    root = Path(vault_path)
    vault = []
    for h in hits:
        try:
            txt = (root / h["path"]).read_text(encoding="utf-8", errors="replace")
            vault.append({"title": h["title"], "snippet": txt[:400]})
        except Exception:
            pass
    papers = await asyncio.to_thread(research, theme, 5)
    try:
        real = await empirical_test(theme)
    except Exception:
        real = {}
    return {"theme": theme, "vault": vault, "literature": format_for_prompt(papers)[:1800],
            "reality": {"verdict": real.get("verdict"), "source": real.get("source"),
                        "evidence": real.get("evidence")}}


def format_insight(r: dict) -> str:
    if not r.get("insight"):
        return f"💡 Couldn't synthesize an insight on _{r.get('theme', '')[:60]}_ (too little to connect)."
    g = r.get("grounding", {})
    return "\n".join([
        f"💡 *New insight* — _{r['theme'][:70]}_\n",
        f"*{r['insight']}*",
        f"\n_Why:_ {r['reasoning']}",
        f"_Confidence:_ {r['confidence']:.0%} · _Falsifier:_ {r['falsifier']}",
        f"_Grounded in:_ {g.get('vault_claims', 0)} vault claims · {g.get('papers', 0)} papers · "
        f"real data ({g.get('reality', '')[:50]})",
    ])
