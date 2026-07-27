"""
Fact-check agent findings against REAL sources before they are trusted/incorporated.

For a claim, re-fetch real papers on its topic and ask a strict critic LLM whether the abstracts
actually support it: VERIFIED / OVERSTATED / UNSUPPORTED. This is the gate between "an agent said
it" and "we incorporate it into the vault as knowledge".

A verdict is only as honest as the literature it judges against. When the corpus has nothing on
the claim's subject, the fetch returns *unrelated* papers — and a "synthesis counts" reviewer
rubber-stamps VERIFIED with an irrelevant Source: attached (observed live: a 2023
software-architecture claim "verified" against a 2010 Faà di Bruno combinatorics paper). So
before any LLM sees them, papers pass a deterministic RELEVANCE GATE (content-word overlap with
the claim); with no relevant literature the verdict is INCONCLUSIVE and nothing is incorporated —
a fake ✓ is worse than no ✓.
"""
from __future__ import annotations

import asyncio
import json
import re

_WORD = re.compile(r"[A-Za-z][A-Za-z\-]{3,}")

# An INTERNAL citation: "Lab 89ffff", "lab_id 89ffff", "(Lab be8da5)". Our own experiment ledger.
_LAB_CITE = re.compile(r"\blab[_\s-]*(?:id\s*)?[:#]?\s*([0-9a-f]{6})\b", re.I)


def _lab_run(claim: str) -> tuple[str, dict | None]:
    """Resolve an internal `Lab <id>` citation against the experiment ledger.

    Returns (cited_id, run_or_None). `("", None)` when the claim cites no Lab at all.
    """
    m = _LAB_CITE.search(claim or "")
    if not m:
        return "", None
    cid = m.group(1).lower()
    try:
        from agora.execution.lab import _load as _lab_load
        for r in _lab_load():
            if str(r.get("id", "")).lower() == cid:
                return cid, r
    except Exception:
        pass
    return cid, None


def _content_words(text: str) -> set[str]:
    from agora.execution.research_tool import _STOP
    return {w.lower() for w in _WORD.findall(text or "") if w.lower() not in _STOP}


def _relevant_papers(topic: str, body: str, papers: list[dict]) -> list[tuple[float, dict]]:
    """Papers that actually share vocabulary with the claim, best first.
    Relevant = >=3 distinctive claim words appear in the paper's title+abstract AND they cover
    >=10% of the claim's vocabulary — unrelated fields (the Faà di Bruno case) score ~0."""
    cw = _content_words(topic + " " + body[:600])
    scored = []
    for p in papers:
        if p.get("error"):
            continue
        pw = _content_words((p.get("title") or "") + " " + (p.get("summary") or ""))
        shared = len(cw & pw)
        share = shared / max(len(cw), 8)
        if shared >= 3 and share >= 0.10:
            scored.append((share, p))
    return sorted(scored, key=lambda x: -x[0])


async def verify_finding(title: str, claim: str) -> dict:
    """Re-fetch real sources for the claim's topic and strictly check whether they support it."""
    from agora.execution.research_tool import research, format_for_prompt
    from agora.execution.llm_client import call_llm

    # Re-fetch by the TOPIC the claim is ABOUT (the title minus quest prefixes), NOT the cited paper
    # title. Findings sometimes mis-cite (e.g. a particle-physics paper attached to an unrelated
    # claim); re-fetching that wrong paper guaranteed a false UNSUPPORTED. The topic gives literature
    # actually relevant to the claim, so the reviewer judges the claim, not a citation accident.
    body = re.sub(r"\bSource:.*$", "", claim, flags=re.DOTALL).strip()

    # INTERNAL EVIDENCE FIRST — a claim whose evidence is OUR OWN Lab run is not a literature claim,
    # and asking the literature about it is a category error the reviewer cannot detect. It cost six
    # days: Lab 89ffff measured `deltaG(q=0.6)-deltaG(0) = 0.077 N (SE 0.009, t=8.6)` in a simulation
    # on 2026-07-19, and every agent that met the claim re-fetched papers, found (correctly) that no
    # paper states it, and filed "the provided sources do not support ΔG = 0.077 N or the Lab 89ffff
    # reference" as a FINDING. Five-plus times, across agents, one of them reaching the vault. The
    # verifier was answering about evidence it had no way to look at -- it never opened the ledger.
    #
    # So the citation is resolved before any fetch, and the two branches are different verdicts:
    #   the run EXISTS      -> LAB_SOURCED. Internally evidenced; literature neither confirms nor
    #                          refutes it, and the honest next step is a re-run, not a search.
    #   the run DOES NOT    -> UNSUPPORTED, and FINAL. A citation to an experiment we never ran is
    #                          fabricated, and "not in the ledger" is decidable, so it must never
    #                          come back as INCONCLUSIVE to be re-judged forever.
    cited, run = _lab_run(claim)
    if cited and run is not None:
        out = " ".join((run.get("output") or "").split())[:180]
        return {"verdict": "LAB_SOURCED",
                "reason": f"evidence is internal: Lab {cited} ({run.get('source') or 'simulation'}, "
                          f"{'ok' if run.get('ok') else 'FAILED'}) measured this — literature cannot "
                          f"confirm a simulation of ours; re-run the experiment to test it",
                "source": f"Lab {cited}: {out}"}
    if cited and run is None:
        return {"verdict": "UNSUPPORTED",
                "reason": f"cites Lab {cited}, which is not in the experiment ledger — a fabricated "
                          f"internal citation, not a claim to be checked against papers",
                "source": ""}

    topic = title
    for _ in range(4):                       # peel any stacked quest/finding prefixes to the real topic
        new = re.sub(r"^(?:Hypothesize on|Pursue direction|Deepen|Develop the gap|Connect|Frontier|"
                     r"Hypothesis|Pipeline)\s*:?\s*", "", topic, flags=re.I).strip()
        if new == topic:
            break
        topic = new
    topic = re.sub(r"\s*<->\s*", " and ", topic)         # bridge titles "A <-> B" -> "A and B"
    query = topic[:90] if len(topic) > 10 else " ".join(body.split()[:12])
    papers = await asyncio.to_thread(research, query, 5)

    # RELEVANCE GATE — only literature that is actually about the claim's subject may judge it.
    relevant = _relevant_papers(topic, body, papers)
    if not relevant:
        return {"verdict": "INCONCLUSIVE",
                "reason": "no relevant literature retrieved for this claim's subject "
                          "(corpus gap) — refusing to judge against unrelated papers",
                "source": ""}
    sources = format_for_prompt([p for _, p in relevant])

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
