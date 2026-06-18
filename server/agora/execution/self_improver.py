"""
Self-improving scientist v3 — the recursive improver's control logic (read-only / advisory).

v1/v2 made ONE self-tuning lever falsifiable (the self-experiment). v3 generalises to a SEARCH over a
space of candidate policy levers, where each self-modification is adopted ONLY via a falsifiable A/B —
and the adoption BAR is set by the COST / IRREVERSIBILITY of a bad change (Lab 39baec): reversible knobs
explore leniently, irreversible/catastrophic changes gate strictly.

This organ is deliberately ADVISORY (read-only): it reads the live self-experiment verdict and RECOMMENDS
the next falsifiable self-modification (adopt/reject the current lever + propose the next candidate). An
unsupervised self-modifier is exactly the lock-in risk our own laws warn about, so v3 proposes; the loop
(with the owner in the loop) disposes. The yield metric stays externally grounded (lock-in guard) so the
improver optimises truth, not a proxy it could game.
"""
from __future__ import annotations

# Ordered registry of candidate levers the recursive improver can test. reversible=True -> explore
# leniently (revert by deleting a file); reversible=False -> would require a strict gate.
CANDIDATE_LEVERS = [
    {"name": "grounding_floor", "reversible": True,
     "desc": "min external-grounding score for a seminar contribution to count (Anchor-Law lever)"},
    {"name": "dedup_threshold", "reversible": True,
     "desc": "cross-topic similarity cutoff that drops near-duplicate contributions"},
    {"name": "verifier_strictness", "reversible": True,
     "desc": "bar for promoting a grounded contribution to the higher-trust VERIFIED tier"},
    {"name": "topic_diversity_floor", "reversible": True,
     "desc": "min cross-domain spread required of a seminar round (anti-herding / anti-lock-in lever)"},
]

# adoption t-threshold by downside (from Lab 39baec: reversible -> lenient; irreversible -> strict)
LENIENT_T = 1.0
STRICT_T = 2.5


def cost_aware_threshold(reversible: bool) -> float:
    return LENIENT_T if reversible else STRICT_T


def _experiment_state():
    try:
        from agora.execution import self_experiment as se
        return se.readout()
    except Exception:
        return {"status": "unavailable"}


def recommend() -> dict:
    """Read the live self-experiment and recommend the next falsifiable self-modification."""
    r = _experiment_state()
    # the lever currently under test is the first in the registry (grounding_floor/dedup pairing)
    current = CANDIDATE_LEVERS[0]["name"]
    nxt = CANDIDATE_LEVERS[2]  # next untested candidate to queue after the current verdict
    thr = cost_aware_threshold(current_reversible := CANDIDATE_LEVERS[0]["reversible"])

    if r.get("status") != "ok":
        return {"status": "ok", "phase": "no-experiment", "current_lever": current,
                "next_candidate": nxt["name"], "adoption_threshold": thr,
                "note": "No live self-experiment readout; engine idle. When one runs, v3 will adopt/reject "
                        "on its verdict and queue the next candidate lever."}

    iv = r.get("intervention", {}); ct = r.get("control", {})
    enough = r.get("enough_data")
    eff = r.get("effect") or {}
    if not enough:
        return {"status": "ok", "phase": "experiment-running", "current_lever": current,
                "intervention_yph": iv.get("yield_per_hr"), "control_yph": ct.get("yield_per_hr"),
                "next_candidate": nxt["name"], "adoption_threshold": thr,
                "note": f"Current lever '{current}' under A/B (reversible -> lenient bar t>{thr}). Verdict pending "
                        f"(needs >=2 epochs + >=15 contribs/regime). On verdict: adopt iff it clears the bar, "
                        f"then queue '{nxt['name']}'."}

    # verdict in: decide adopt/reject with the cost-aware bar
    ratio = eff.get("yield_per_hr_ratio")
    adopt = bool(ratio and ratio > 1.0 + 0.10) if current_reversible else bool(ratio and ratio > 1.0 + 0.25)
    return {"status": "ok", "phase": "verdict-ready",
            "current_lever": current, "effect_ratio": ratio, "adoption_threshold": thr,
            "recommendation": ("ADOPT " + current + " as default") if adopt else ("REJECT/revert " + current),
            "next_candidate": nxt["name"],
            "note": f"Self-experiment verdict in (ratio {ratio}); reversible lever -> lenient bar. "
                    f"Recommend {'adopt' if adopt else 'reject'}, then A/B the next candidate '{nxt['name']}'. "
                    f"Advisory only — the loop/owner confirms before any mutation."}


def format_self_improver() -> str:
    a = recommend()
    if a.get("status") != "ok":
        return "🧬 *Self-improver v3*: unavailable."
    return "\n".join([
        "🧬 *Self-improving scientist v3* (recursive, cost-aware, advisory):",
        f"• phase: {a.get('phase')} | current lever: *{a.get('current_lever')}* (bar t>{a.get('adoption_threshold')})",
        f"• next candidate queued: {a.get('next_candidate')}",
        (f"• recommendation: *{a.get('recommendation')}*" if a.get("recommendation") else "• verdict pending"),
        f"• {a.get('note')}",
    ])
