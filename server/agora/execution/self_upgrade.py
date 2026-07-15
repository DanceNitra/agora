"""
Self-upgrade — Agora reflects on its OWN mechanisms and proposes concrete upgrades to itself.

The harvest turns findings into research directions; this turns the OS's own output + metrics into
SYSTEM upgrades (how to raise the verified-rate, reduce repetition, deepen reasoning, compound
better). Claude Code reads these, judges which are genuinely breakthrough, and implements them —
closing the recursive self-improvement loop.
"""
from __future__ import annotations

import asyncio
import json
import re


async def agora_metrics(db) -> dict:
    """The OS's vital signs — so it (and Claude) can see whether it is improving."""
    async def _count(q, args=()):
        cur = await db.execute(q, args)
        r = await cur.fetchone()
        return (r[0] if r else 0) or 0
    findings = await _count("SELECT COUNT(*) FROM collective_knowledge WHERE knowledge_type='discovery'")
    # BUG FIX (2026-07-15): hypotheses are stored as knowledge_type='hypothesis', NOT as discoveries whose
    # title starts with 'Hypothesis'. The old query matched ~3 rows (essentially none), so the architect prompt
    # saw "10k findings, 3 hypotheses" and hallucinated a "severe hypothesis bottleneck" that does not exist
    # (the loop actually records ~15/day, 318 total). Count the real type, and add a recent-window signal so a
    # genuine stall (loop dead) is distinguishable from a healthy backlog.
    hypos = await _count("SELECT COUNT(*) FROM collective_knowledge WHERE knowledge_type='hypothesis'")
    hypos_7d = await _count("SELECT COUNT(*) FROM collective_knowledge WHERE knowledge_type='hypothesis' "
                            "AND created_at > datetime('now','-7 days')")
    return {"findings_total": findings, "hypotheses_total": hypos, "hypotheses_last_7d": hypos_7d}


async def propose_self_upgrades(db) -> dict:
    """LLM (as Agora's systems architect) proposes concrete upgrades to AGORA'S OWN mechanisms."""
    from agora.execution.llm_client import call_llm
    cur = await db.execute(
        "SELECT content FROM collective_knowledge WHERE knowledge_type='discovery' "
        "ORDER BY created_at DESC LIMIT 14")
    findings = [(r[0] or "")[:150] for r in await cur.fetchall() if r and r[0]]
    metrics = await agora_metrics(db)
    sample = "\n".join(f"- {f}" for f in findings[:12])
    # Gatekeeper: tell the architect what ALREADY EXISTS so it stops proposing built organs.
    built = ("ALREADY BUILT (never propose these): hypothesis induction from finding clusters; "
             "prediction ledger + forecasting tournament + per-agent mastery; exam + A/B "
             "self-experiments; observatory vitals; belief revision (challenge sweeps); canon; "
             "tutor (SM-2); interview; desk; campaigns/dossiers; full-paper library; contradiction "
             "sweep; source reliability; salon feeds; sandboxed compute lab; annals; board "
             "priorities; attention economy; nightly index rebuild; watchdogs; memory-economy "
             "curation; public digest publishing; capability forge.")
    raw = await asyncio.to_thread(
        call_llm,
        "You are the systems architect of AGORA — an autonomous research OS: 6 agents research the "
        "user's Obsidian vault, ground findings in real papers (OpenAlex/arXiv), fact-check them, form "
        "and test hypotheses, and harvest directions. Looking at the agents' RECENT OUTPUT and metrics "
        "below, propose 2-3 CONCRETE upgrades to AGORA'S OWN MECHANISMS that would most improve it — "
        "e.g. raise how many findings survive fact-checking, cut repetition, deepen reasoning, make the "
        "loop compound. These must be upgrades to the SYSTEM (prompts, pipeline, verification, quests, "
        "graph), NOT research topics, and NOT anything on the already-built list. Reply ONLY JSON: "
        '{"upgrades":[{"title":"<short>","why":"<the system weakness it fixes>","how":"<concrete change>"}]}.',
        f"{built}\n\nMetrics: {metrics}\n\nRecent agent findings:\n{sample}", "cheap", 0.4, 1100) or ""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    ups = []
    if m:
        try:
            for x in (json.loads(m.group(0)).get("upgrades") or [])[:3]:
                if x.get("title"):
                    ups.append({"title": str(x["title"])[:90], "why": str(x.get("why", ""))[:200],
                                "how": str(x.get("how", ""))[:240]})
        except Exception:
            pass
    return {"metrics": metrics, "upgrades": ups}
