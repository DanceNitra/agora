"""
AGORA 2.0 — Pillar 2: agents as scientists.

Not "summarize a paper" but the scientific method: take what the vault already BELIEVES (Pillar 1),
generate a NEW testable hypothesis that extends or challenges it, TEST it against real literature,
and return a verdict with evidence, a confidence, and an explicit falsifier. A refuted hypothesis is
real knowledge too — high signal either way.
"""
from __future__ import annotations

import asyncio
import json
import re


def _json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


async def hypothesize_and_test(topic: str, vault_path: str) -> dict:
    from agora.execution.knowledge_graph import believe
    from agora.execution.research_tool import research, format_for_prompt
    from agora.execution.llm_client import call_llm

    b = await believe(topic, vault_path, 6)
    known = "\n".join(f"- {c['s']} {c['r']} {c['o']}" for c in b.get("claims", [])[:10]) \
        or "(the vault is thin here)"

    # 1) generate ONE new, specific, testable hypothesis that goes beyond what's already claimed
    sysmsg = (
        "Propose ONE NEW, specific, TESTABLE hypothesis about the topic — a single declarative "
        "sentence a real paper could support or refute. If prior claims are given, extend or "
        "challenge them (don't restate). If little is known, propose a sharp first hypothesis from "
        "the topic itself. Reply ONLY the hypothesis sentence, nothing else.")
    usr = f"Topic: {topic}\nAlready claimed:\n{known}"
    hyp = (await asyncio.to_thread(call_llm, sysmsg, usr, "cheap", 0.5, 160) or "").strip().strip('"')
    if not hyp:                                         # the LLM occasionally returns empty — retry once
        hyp = (await asyncio.to_thread(call_llm, sysmsg, usr, "cheap", 0.7, 200) or "").strip().strip('"')
    if not hyp:
        return {"topic": topic, "hypothesis": "", "verdict": "NONE", "known": b.get("claims", [])}

    # 2) test it against real literature
    papers = await asyncio.to_thread(research, hyp[:100], 5)
    sources = format_for_prompt(papers)
    raw = await asyncio.to_thread(
        call_llm,
        "Test the HYPOTHESIS against the REAL abstracts below. Be strict and evidence-based. The "
        "evidence MUST cite ONE SPECIFIC result from a real paper — a concrete finding, number, or "
        "named mechanism, with author/year — not a vague 'this paper is related'. If no abstract "
        "states such a specific supporting result, the verdict is UNCERTAIN. "
        "Reply ONLY JSON: {\"verdict\":\"SUPPORTED|REFUTED|UNCERTAIN\",\"evidence\":\"<one sentence "
        "with the specific result + author/year>\",\"confidence\":0.0,\"falsifier\":\"<what "
        "observation would prove it wrong>\"}.",
        f"HYPOTHESIS: {hyp}\n\nREAL ABSTRACTS:\n{sources}", "cheap", 0.1, 360)
    d = _json(raw)
    verdict = str(d.get("verdict", "UNCERTAIN")).upper()
    if verdict not in ("SUPPORTED", "REFUTED", "UNCERTAIN"):
        verdict = "UNCERTAIN"
    top = sources.splitlines()[0].lstrip("- ").strip()[:140] if sources and "(no external" not in sources else ""
    return {
        "topic": topic,
        "hypothesis": hyp,
        "verdict": verdict,
        "evidence": str(d.get("evidence", ""))[:300],
        "confidence": float(d.get("confidence", 0.5)) if isinstance(d.get("confidence", 0.5), (int, float)) else 0.5,
        "falsifier": str(d.get("falsifier", ""))[:200],
        "source": top,
        "known_claims": len(b.get("claims", [])),
    }


def format_hypothesis(h: dict) -> str:
    if not h.get("hypothesis"):
        return f"🔬 *{h['topic']}* — not enough in the vault to form a hypothesis yet."
    icon = {"SUPPORTED": "✅", "REFUTED": "❌", "UNCERTAIN": "🟡"}.get(h["verdict"], "🟡")
    return (f"🔬 *Hypothesis — {h['topic'][:50]}*\n\n"
            f"*{h['hypothesis']}*\n\n"
            f"{icon} {h['verdict']} (conf {h['confidence']:.0%})\n"
            f"📎 {h['evidence']}\n"
            f"🧪 _falsifier: {h['falsifier']}_\n"
            f"📚 {h['source']}")
