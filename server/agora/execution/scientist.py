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
import os
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
    # Orin rebuild: a hypothesis must name a concrete MECHANISM + a predicted DIRECTION/quantity a minimal
    # computational model could measure — so it is genuinely severe-testable AND maps to a Methods template
    # (raises Rooke's match + the quality of what gets tested), not a vague sentence.
    # RAISED BAR (owner 2026-07-16, "the mill re-derives textbook"): the old prompt listed textbook
    # claim-shapes (power-law, tipping, regression-to-mean...) — the very reason the output re-derived
    # Albert-Barabasi / Staiger-Stock. Steer instead to an OPEN question at the edge of the given claims
    # that is still computationally settleable, then GATE out anything a domain expert already knows.
    sysmsg = (
        "Propose ONE hypothesis about the topic — a single declarative sentence naming a concrete MECHANISM "
        "and a predicted DIRECTION or quantity a minimal computational model could measure. HARD REQUIREMENT: "
        "it must be a GENUINELY OPEN question at the frontier of the given claims — something a domain expert "
        "would NOT already know the answer to. Do NOT restate a known named law or textbook result (e.g. "
        "hubs-fail-worse-than-random, weak-instrument-bias, regression-to-the-mean, power-law-tails); those "
        "are already established and are WORTHLESS to us. Find the specific UNSETTLED edge: a boundary "
        "condition, an interaction nobody has isolated, a regime where the known rule might break. If prior "
        "claims are given, extend or challenge them, never restate. Reply ONLY the hypothesis sentence.")
    usr = f"Topic: {topic}\nAlready claimed:\n{known}"
    hyp = (await asyncio.to_thread(call_llm, sysmsg, usr, "cheap", 0.6, 160) or "").strip().strip('"')
    if not hyp:                                         # the LLM occasionally returns empty — retry once
        hyp = (await asyncio.to_thread(call_llm, sysmsg, usr, "cheap", 0.7, 200) or "").strip().strip('"')
    if not hyp:
        return {"topic": topic, "hypothesis": "", "verdict": "NONE", "known": b.get("claims", [])}

    # NOVELTY GATE (owner's RAISED BAR; flag AGORA_NOVELTY_GATE, default ON — set "0" to revert). Kill
    # textbook re-derivations at generation: ask whether the hypothesis is an already-established known
    # result; if so, regenerate ONCE told exactly what known result it echoed; if still textbook, produce
    # NOTHING (verdict NONE) — a genuinely-open miss beats a textbook hit.
    if os.getenv("AGORA_NOVELTY_GATE", "1") != "0":
        async def _is_textbook(h):
            raw = await asyncio.to_thread(
                call_llm,
                "You are a strict domain expert. Is the HYPOTHESIS an already-established, textbook / "
                "named-law result that a specialist would recognize as known (the answer is settled)? "
                "Reply ONLY JSON: {\"known\":true|false,\"result\":\"<the established result/law it "
                "matches, or empty>\"}.", f"HYPOTHESIS: {h}", "cheap", 0.0, 200)
            d = _json(raw)
            return bool(d.get("known")), str(d.get("result", ""))[:200]
        known_tb, named = await _is_textbook(hyp)
        if known_tb:
            hyp2 = (await asyncio.to_thread(
                call_llm, sysmsg + f"\n\nYour previous attempt was TEXTBOOK — it just restates the known "
                f"result: {named}. Propose instead a genuinely OPEN question that is NOT this.",
                usr, "cheap", 0.8, 200) or "").strip().strip('"')
            still_tb, _ = await _is_textbook(hyp2) if hyp2 else (True, "")
            if hyp2 and not still_tb:
                hyp = hyp2
            else:
                return {"topic": topic, "hypothesis": "", "verdict": "NONE",
                        "known": b.get("claims", []), "skipped": f"textbook: {named}"}

    # SEVERE-TEST PATH (AGORA_SCIENTIST_LAB=1): a REAL Lab run via the Methods Library + a pre-commitment,
    # instead of the LLM-vibe-check below. No measured number -> verdict NONE, NOT recorded. (proof step;
    # flag off = old behavior, instant revert.)
    if os.getenv("AGORA_SCIENTIST_LAB") == "1":
        return await _severe_test(topic, hyp, b)

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
        "with the specific result + author/year>\",\"confidence\":<your calibrated 0..1 probability "
        "the hypothesis is TRUE given the evidence>,\"falsifier\":\"<what "
        "observation would prove it wrong>\"}.",
        f"HYPOTHESIS: {hyp}\n\nREAL ABSTRACTS:\n{sources}", "cheap", 0.1, 360)
    d = _json(raw)
    verdict = str(d.get("verdict", "UNCERTAIN")).upper()
    if verdict not in ("SUPPORTED", "REFUTED", "UNCERTAIN"):
        verdict = "UNCERTAIN"
    # Calibrated confidence = P(hypothesis is true). The old test prompt templated "confidence":0.0,
    # so the cheap model echoed 0.0 back on UNCERTAIN verdicts — reporting hypotheses it had NOT
    # refuted as "conf 0%" (self-contradictory, and 0% reads as 'certainly false'). Fall back to a
    # verdict-anchored prior when the returned value is missing or the echoed ~0 placeholder.
    # UNCERTAIN = the literature is SILENT, a genuine ~50% prior, not disconfirmation.
    rc = d.get("confidence")
    rc = float(rc) if isinstance(rc, (int, float)) and 0.0 <= float(rc) <= 1.0 else None
    prior = {"SUPPORTED": 0.7, "REFUTED": 0.15, "UNCERTAIN": 0.5}[verdict]
    conf = prior if (rc is None or rc < 0.05) else rc
    if verdict == "UNCERTAIN":
        conf = min(max(conf, 0.35), 0.6)          # keep "we don't know" away from the extremes
    top = sources.splitlines()[0].lstrip("- ").strip()[:140] if sources and "(no external" not in sources else ""
    return {
        "topic": topic,
        "hypothesis": hyp,
        "verdict": verdict,
        "evidence": str(d.get("evidence", ""))[:300],
        "confidence": conf,
        "falsifier": str(d.get("falsifier", ""))[:200],
        "source": top,
        "known_claims": len(b.get("claims", [])),
    }


async def _precommit(hyp: str) -> dict:
    """Pre-registration BEFORE any run (no HARKing): the predicted measured direction + a decision rule."""
    from agora.execution.llm_client import call_llm
    raw = (await asyncio.to_thread(
        call_llm,
        "For the hypothesis, state a PRE-COMMITMENT to be written BEFORE any experiment runs: the expected "
        "measured direction/sign and a one-line decision rule for SUPPORTED vs REFUTED. Reply ONLY JSON: "
        '{"direction":"<expected sign/direction of the measured effect>",'
        '"decision_rule":"<SUPPORTED if ...; REFUTED if ...>"}.',
        f"HYPOTHESIS: {hyp}", "cheap", 0.2, 220) or "")
    return _json(raw)


async def _severe_test(topic: str, hyp: str, b: dict) -> dict:
    """Severe-test path: run a REAL minimal model via the Methods Library, compare the MEASURED number to a
    pre-commitment. No template fit OR no measured number -> verdict NONE (not a test, not recorded)."""
    from agora.execution.methods import match_and_run
    from agora.execution.llm_client import call_llm
    precommit = await _precommit(hyp)
    res = await match_and_run(hyp, requester="scientist")
    measured = (res.get("measured") or "").replace("MEASURED:", "").strip()
    if res.get("status") != "ok" or not res.get("ok") or not measured:
        return {"topic": topic, "hypothesis": hyp, "verdict": "NONE",
                "reason": ("no_lab_template_match" if res.get("status") != "ok" else "no_measured_number"),
                "precommit": precommit, "lab_backed": True, "known_claims": len(b.get("claims", []))}
    tpl_verdict = (res.get("verdict") or "").replace("VERDICT:", "").strip()
    # compare MEASURED vs pre-commitment AND flag whether the measured quantity actually bears on the claim
    raw = (await asyncio.to_thread(
        call_llm,
        "A hypothesis was severely tested by running a computational model. Compare the MEASURED result to "
        "the PRE-COMMITMENT. Reply ONLY JSON: {\"verdict\":\"SUPPORTED|REFUTED|UNCERTAIN\","
        "\"relevant\":<true if the measured quantity actually bears on the hypothesis, else false>,"
        "\"confidence\":<0..1 probability the hypothesis is true given the measurement>}.",
        f"HYPOTHESIS: {hyp}\nPRE-COMMITMENT: {json.dumps(precommit)[:300]}\n"
        f"MEASURED: {measured[:200]}\nMODEL VERDICT: {tpl_verdict[:120]}", "cheap", 0.1, 220) or "")
    d = _json(raw)
    # RELEVANCE GATE: a template can match loosely and measure the wrong thing (the test-relevance seam).
    # If the measured quantity does not bear on the hypothesis, it is NOT a test of it -> do not record.
    if not bool(d.get("relevant", False)):
        return {"topic": topic, "hypothesis": hyp, "verdict": "NONE", "reason": "lab_result_irrelevant",
                "lab_id": res.get("lab_id", ""), "measured": measured[:200], "lab_backed": True,
                "known_claims": len(b.get("claims", []))}
    verdict = str(d.get("verdict", "UNCERTAIN")).upper()
    if verdict not in ("SUPPORTED", "REFUTED", "UNCERTAIN"):
        verdict = "UNCERTAIN"
    rc = d.get("confidence")
    conf = float(rc) if isinstance(rc, (int, float)) and 0.0 <= float(rc) <= 1.0 else \
        {"SUPPORTED": 0.7, "REFUTED": 0.2, "UNCERTAIN": 0.5}[verdict]
    return {
        "topic": topic, "hypothesis": hyp, "verdict": verdict,
        "evidence": f"Lab[{res.get('template', '')}] {measured}"[:300],
        "confidence": conf,
        "falsifier": (precommit.get("decision_rule") or tpl_verdict)[:200],
        "source": f"lab:{res.get('lab_id', '')} ({res.get('template', '')})",
        "lab_id": res.get("lab_id", ""), "measured": measured[:200],
        "lab_relevant": bool(d.get("relevant", False)), "lab_backed": True,
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
