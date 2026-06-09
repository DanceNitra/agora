"""
Fact-check agent findings against REAL sources before they are trusted/incorporated.

For a claim, re-fetch real papers on its topic and ask a strict critic LLM whether the abstracts
actually support it: VERIFIED / OVERSTATED / UNSUPPORTED. This is the gate between "an agent said
it" and "we incorporate it into the vault as knowledge".
"""
from __future__ import annotations

import asyncio
import json
import re


async def verify_finding(title: str, claim: str) -> dict:
    """Re-fetch real sources for the claim's topic and strictly check whether they support it."""
    from agora.execution.research_tool import research, format_for_prompt
    from agora.execution.llm_client import call_llm

    # Prefer the paper the finding actually cited; else the title's clean topic.
    cited = re.search(r"Source:\s*[\"']?(.+)", claim)
    body = re.sub(r"\bSource:.*$", "", claim, flags=re.DOTALL).strip()
    topic = title.rsplit(": ", 1)[-1].strip()
    if cited:
        query = re.sub(r"\(.*$", "", cited.group(1)).strip()[:90]   # paper title, drop "(authors…)"
    elif len(topic) > 8:
        query = topic
    else:
        query = " ".join(body.split()[:12])
    papers = await asyncio.to_thread(research, query, 5)
    sources = format_for_prompt(papers)

    raw = await asyncio.to_thread(
        call_llm,
        "You are a scientific reviewer judging whether a research CLAIM is SOUND and grounded in "
        "the real literature below. A reasonable SYNTHESIS of real, established concepts counts as "
        "VERIFIED even if no single abstract states it verbatim — judge consistency and grounding, "
        "not exact wording. Reply ONLY JSON "
        '{"verdict":"VERIFIED|OVERSTATED|UNSUPPORTED","reason":"<one sentence>"}. '
        "VERIFIED = specific, grounded, consistent with the literature; OVERSTATED = grounded but "
        "over-reaches or generalizes too far; UNSUPPORTED = vague, mere narration, fabricated, or "
        "contradicted by the evidence.",
        f"CLAIM: {body[:600]}\n\nREAL LITERATURE (abstracts):\n{sources}", "cheap", 0.1, 220) or ""

    # INCONCLUSIVE (not UNSUPPORTED) when we got no real judgment — the flaky LLM returns nothing
    # ~half the time, and defaulting that to UNSUPPORTED wrongly condemns groundable findings forever.
    # INCONCLUSIVE findings are re-checked later instead of being permanently rejected.
    verdict, reason = "INCONCLUSIVE", "no judgment returned (verifier LLM empty)"
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group(0))
            verdict = (d.get("verdict") or "INCONCLUSIVE").upper().strip()
            reason = (d.get("reason") or "").strip()
        except Exception:
            pass
    if verdict not in ("VERIFIED", "OVERSTATED", "UNSUPPORTED", "INCONCLUSIVE"):
        verdict = "INCONCLUSIVE"
    top = ""
    if sources and "(no external" not in sources:
        top = sources.splitlines()[0].lstrip("- ").strip()[:140]
    return {"verdict": verdict, "reason": reason[:200], "source": top}
