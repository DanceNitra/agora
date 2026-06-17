"""
Consensus lock-in guard — Agora governed by its own minority-tipping / Grounding-Coupling law.

This session validated (Lab 6e363b + real HN data 780388 + the agent-based model) that a coupled
collective tips off truth when one cluster crosses a critical mass UNLESS external grounding stays
high and the cluster is multi-domain. Agora IS such a collective: the seminar + canon form a
consensus. The existing self_improvement monitor measures only AGGREGATE external grounding (phi);
it does not measure CONCENTRATION — the actual minority-tipping risk. This organ adds that.

It automates, by our own law, exactly the bias-check we ran by hand in the criticality retrospective:
a dominant theme is SAFE iff it is externally grounded AND multi-domain (like the criticality cluster
we verified: 51% but 7 domains + external papers => tracking truth, not locked in); it is a LOCK-IN
RISK iff a theme crosses the critical-mass band while grounding or domain-diversity is low.

Read-only over the live consensus stream (.contributions.json). Keyword-based coarse-theming (crude,
flagged) — same methodology, and same honest caveat, as the retrospective.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_CONTRIB = Path(__file__).resolve().parents[2] / ".contributions.json"

# Coarse themes (the retrospective's domains). Keyword-based: crude but consistent with prior method.
_THEMES = {
    "criticality/phase-transition": ["critical", "phase transition", "tipping", "percolation", "universality",
                                      "scaling", "exponent", "threshold", "branching", "bistab", "slowing down"],
    "causal-inference/identification": ["causal", "identification", "instrument", "difference-in-diff", "did ",
                                        "counterfactual", "confound", "selection bias", "rdd", "regression discontinuity"],
    "networks": ["network", "graph", "clique", "scale-free", "centrality", "small-world", "degree distribution"],
    "epidemics/spreading": ["epidemic", "contagion", "spreading", "infection", "sis", "sir", "cascade", "diffusion"],
    "learning/AI": ["model collapse", "self-training", "llm", "neural", "reinforcement", "gradient", "transformer",
                    "ai augmentation", "self-reference", "agent"],
    "finance/markets": ["finance", "market", "volatility", "portfolio", "alpha", "arbitrage", "asset", "trading"],
    "longevity/biology": ["longevity", "aging", "senescence", "biolog", "gene", "cell", "metabol", "neuroscience"],
    "memory/cognition": ["memory", "recall", "forgetting", "spaced repetition", "cognit", "attention", "consolidat"],
    "epistemics/inference": ["bayesian", "frequentist", "calibration", "prior", "evidence", "epistemic", "inference",
                             "falsifi", "prediction"],
    "future-of-work/society": ["future of work", "automation", "displacement", "institution", "economy", "labor",
                               "collective intelligence", "society"],
    "complexity/emergence": ["emergence", "complexity", "self-organ", "nonlinear", "feedback", "attractor"],
}

# Thresholds derived from this session's measurements + the retrospective precedent:
#  - critical-mass band ~20-25% (Lab 6e363b); we treat a single coarse theme above CONCENTRATION_HI as
#    "dominant". The retrospective showed 51% is SAFE when grounded + multi-domain, so dominance alone
#    is NOT the alarm — it must coincide with low grounding OR low diversity (the law's resistance lever).
CONCENTRATION_HI = 0.40
GROUNDING_SAFE = 0.60
DIVERSITY_SAFE = 4          # number of coarse themes carrying >=5% of consensus


def _truthy(x) -> bool:
    return str(x).lower() == "true"


def _theme_of(text: str) -> str:
    t = (text or "").lower()
    best, score = "other", 0
    for name, kws in _THEMES.items():
        s = sum(1 for kw in kws if kw in t)
        if s > score:
            best, score = name, s
    return best if score > 0 else "other"


def measure(hours: float = 14 * 24) -> dict:
    try:
        contribs = json.loads(_CONTRIB.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "no_data"}
    cut = time.time() - hours * 3600
    recent = [c for c in contribs if float(c.get("ts", 0) or 0) >= cut]
    if len(recent) < 20:
        recent = contribs[-200:]            # fall back to the last 200 if the window is thin
    n = len(recent)
    if not n:
        return {"status": "no_data"}
    buckets: dict = {}
    for c in recent:
        text = " ".join(str(c.get(k, "")) for k in ("topic", "claim", "basis"))
        th = _theme_of(text)
        b = buckets.setdefault(th, {"n": 0, "grounded": 0, "verified": 0})
        b["n"] += 1
        if _truthy(c.get("grounded")):
            b["grounded"] += 1
        if _truthy(c.get("verified")):
            b["verified"] += 1
    shares = {k: round(v["n"] / n, 3) for k, v in buckets.items()}
    top = max(buckets, key=lambda k: buckets[k]["n"])
    top_b = buckets[top]
    diversity = sum(1 for k, v in buckets.items() if v["n"] / n >= 0.05)
    return {"status": "ok", "n": n, "themes": len(buckets),
            "top_theme": top, "top_share": round(top_b["n"] / n, 3),
            "top_grounding": round(top_b["grounded"] / top_b["n"], 3),
            "domain_diversity": diversity, "shares": dict(sorted(shares.items(), key=lambda x: -x[1]))}


def assess() -> dict:
    """Apply the minority-tipping / Grounding-Coupling law to Agora's own consensus."""
    m = measure()
    if m.get("status") != "ok":
        return {"status": m.get("status", "no_data")}
    dominant = m["top_share"] >= CONCENTRATION_HI
    grounded = m["top_grounding"] >= GROUNDING_SAFE
    diverse = m["domain_diversity"] >= DIVERSITY_SAFE
    # The law: dominance is only dangerous when grounding OR diversity is low (the resistance levers).
    lock_in_risk = dominant and not (grounded and diverse)
    if not dominant:
        verdict = (f"Healthy — no single theme dominates (top '{m['top_theme']}' = {m['top_share']:.0%}, "
                   f"{m['domain_diversity']} active domains). Consensus is distributed.")
    elif grounded and diverse:
        verdict = (f"Dominant but SAFE — '{m['top_theme']}' is {m['top_share']:.0%} of consensus, but it is "
                   f"well-grounded ({m['top_grounding']:.0%}) and multi-domain ({m['domain_diversity']} domains). "
                   f"Per the law (f_c rises with grounding), high grounding keeps a dominant cluster truth-tracking "
                   f"— the same verdict as the criticality retrospective.")
    else:
        why = "low external grounding" if not grounded else "low domain diversity"
        verdict = (f"LOCK-IN RISK — '{m['top_theme']}' is {m['top_share']:.0%} of consensus with {why} "
                   f"(grounding {m['top_grounding']:.0%}, {m['domain_diversity']} domains). The minority-tipping law "
                   f"says a dominant cluster decouples from truth when grounding/diversity is low — raise external "
                   f"grounding on this theme or widen the gap pool.")
    return {"status": "ok", "lock_in_risk": lock_in_risk, "verdict": verdict, **m}


def format_self_tipping() -> str:
    a = assess()
    if a.get("status") != "ok":
        return "🧭 *Consensus lock-in guard*: insufficient data."
    return "\n".join([
        "🧭 *Consensus lock-in guard* — Agora checked by its own minority-tipping law:",
        f"• top theme: *{a['top_theme']}* = {a['top_share']:.0%}  (grounding {a['top_grounding']:.0%}, "
        f"{a['domain_diversity']} domains, {a['themes']} themes / {a['n']} contributions)",
        f"• {'⚠️ ' if a['lock_in_risk'] else ''}{a['verdict']}",
    ])
