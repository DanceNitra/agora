"""
Claim Auditor — "is this number real, or what would a matched null / proper identification produce?"

The engine behind Agora's claim-diligence service. It scores a quantitative claim on the two ways a
reported effect is usually wrong:

  1) MATCHED NULL  — is the effect bigger than what a properly randomised (placebo) baseline would
     produce by chance / by selection alone? (credit only effect minus its own null)
  2) IDENTIFICATION QUALITY — does the effect SURVIVE across the defensible analytic choices, or does
     it swing with the specification? An effect that flips sign / collapses across reasonable
     specifications is attribution, not a causal claim (a control is a claim about the graph;
     cf. our measured result that alt-data alpha is an *identification* premium — Lab 11c99e).

Verdict logic:
  - above its own null AND stable across specs            -> REAL (identified)
  - above null but unstable across specs                  -> NOT IDENTIFIED (spec-dependent)
  - not above its own null                                -> OVERSTATED / NOISE

This file is dependency-light (numpy only) and runnable as a demo:  python claim_auditor.py
"""
from __future__ import annotations

import numpy as np


# ───────────────────────── core engine ─────────────────────────

def matched_null(observed_effect: float, effect_under_permutation, n_perm: int = 2000,
                 rng=None) -> dict:
    """Permutation/placebo null: how extreme is the observed effect vs a randomised baseline?
    `effect_under_permutation()` must return one effect computed on relabelled/placebo data."""
    rng = rng or np.random.default_rng(0)
    null = np.array([effect_under_permutation(rng) for _ in range(n_perm)])
    # one-sided p: fraction of null effects at least as large as observed (sign-aware)
    if observed_effect >= 0:
        p = float((null >= observed_effect).mean())
    else:
        p = float((null <= observed_effect).mean())
    null_band = (float(np.percentile(null, 2.5)), float(np.percentile(null, 97.5)))
    # the portion of the observed effect that exceeds the null's central tendency
    net = observed_effect - float(np.median(null))
    return {"p_value": p, "null_median": float(np.median(null)),
            "null_95band": null_band, "net_of_null": net,
            "above_null": p < 0.05}


def identification_quality(spec_effects: list[float]) -> dict:
    """Specification-curve dispersion. spec_effects = the same effect under each DEFENSIBLE analytic
    choice (controls, window, model). Identified iff the effect is stable and sign-consistent.
    Score in [0,1]: 1 = every defensible spec agrees; 0 = it's whatever you choose."""
    e = np.array([x for x in spec_effects if np.isfinite(x)], dtype=float)
    if len(e) < 2:
        return {"score": float("nan"), "sign_consistency": float("nan"),
                "dispersion_ratio": float("nan"), "n_specs": len(e)}
    med = float(np.median(e))
    sign_consistency = float(max((e > 0).mean(), (e < 0).mean()))   # 1 = all same sign
    # dispersion of specs relative to the typical effect size (robust)
    mad = float(np.median(np.abs(e - med))) * 1.4826
    scale = max(abs(med), 1e-9)
    dispersion_ratio = mad / scale
    # identified when sign is consistent AND the spread is small relative to the effect
    score = float(np.clip(sign_consistency - dispersion_ratio, 0.0, 1.0))
    return {"score": round(score, 3), "sign_consistency": round(sign_consistency, 3),
            "dispersion_ratio": round(dispersion_ratio, 3), "median_effect": round(med, 4),
            "spec_min": round(float(e.min()), 4), "spec_max": round(float(e.max()), 4),
            "n_specs": len(e)}


def audit(claim_label: str, claimed_effect: float, units: str,
          permutation_fn, spec_effects: list[float], identified_effect: float | None = None,
          n_perm: int = 2000, seed: int = 0) -> dict:
    """Run both checks and render a one-page verdict."""
    mn = matched_null(claimed_effect, permutation_fn, n_perm=n_perm, rng=np.random.default_rng(seed))
    iq = identification_quality(spec_effects)
    above = mn["above_null"]
    identified = (iq["score"] >= 0.5) if np.isfinite(iq["score"]) else False
    overcount = None
    if identified_effect is not None and abs(identified_effect) > 1e-9:
        overcount = (claimed_effect - identified_effect) / abs(identified_effect)
    big_overcount = (overcount is not None and abs(overcount) >= 0.25)
    # Verdict order: no real effect > claim inflates a real effect > spec-dependent > clean.
    if not above:
        verdict = "OVERSTATED / NOISE (not above its own null)"
    elif big_overcount:
        verdict = (f"OVERSTATED — a real effect exists (~{identified_effect:+.3g}) but the claim "
                   f"inflates it by {overcount*100:+.0f}%")
    elif not identified:
        verdict = "NOT IDENTIFIED (specification-dependent)"
    else:
        verdict = "REAL (identified)"
    return {"claim": claim_label, "claimed_effect": claimed_effect, "units": units,
            "matched_null": mn, "identification": iq,
            "identified_effect": identified_effect, "overcount_fraction": overcount,
            "verdict": verdict}


def one_pager(a: dict) -> str:
    mn, iq = a["matched_null"], a["identification"]
    L = []
    L.append("=" * 64)
    L.append(f"CLAIM AUDIT — {a['claim']}")
    L.append("=" * 64)
    L.append(f"Claimed effect: {a['claimed_effect']:+.3g} {a['units']}")
    L.append("")
    L.append("1) MATCHED NULL (is it above its own placebo baseline?)")
    L.append(f"   null median {mn['null_median']:+.3g}  | 95% null band "
             f"[{mn['null_95band'][0]:+.3g}, {mn['null_95band'][1]:+.3g}]")
    L.append(f"   p(effect vs null) = {mn['p_value']:.3f}  -> "
             f"{'ABOVE null' if mn['above_null'] else 'WITHIN null (not distinguishable)'}")
    L.append(f"   net of null: {mn['net_of_null']:+.3g} {a['units']}")
    L.append("")
    L.append("2) IDENTIFICATION QUALITY (does it survive defensible specifications?)")
    L.append(f"   score {iq['score']}  (sign-consistency {iq['sign_consistency']}, "
             f"dispersion/effect {iq['dispersion_ratio']})")
    L.append(f"   effect across {iq['n_specs']} specs: [{iq['spec_min']:+.3g} .. {iq['spec_max']:+.3g}] "
             f"(median {iq['median_effect']:+.3g})")
    if a.get("identified_effect") is not None:
        L.append("")
        L.append(f"   identified (causal) effect: {a['identified_effect']:+.3g} {a['units']}")
        if a.get("overcount_fraction") is not None:
            L.append(f"   >>> the claim OVERSTATES the identified effect by "
                     f"{a['overcount_fraction']*100:+.0f}%")
    L.append("")
    L.append(f"VERDICT: {a['verdict']}")
    L.append("=" * 64)
    return "\n".join(L)


# ───────────────────────── demo: marketing attribution with a selection confound ─────────────────────────
# Naive last-touch attribution credits ALL post-ad conversions to the ad. But ads are TARGETED at
# high-propensity users (selection), so much of the "attributed" lift would have happened anyway.
# Ground truth here is KNOWN, so the auditor can be validated: it should recover the true incremental
# lift and flag the overcount that real teams report (attribution overcounts ad impact 20-40%).

def _simulate(n=20000, seed=1):
    rng = np.random.default_rng(seed)
    propensity = rng.beta(2, 5, n)                       # latent organic buy-propensity
    # ad EXPOSURE is targeted at high-propensity users (the confound)
    exposed = rng.random(n) < (0.2 + 0.6 * propensity)
    TRUE_LIFT = 0.04                                     # ground-truth causal lift from being exposed
    p_buy = np.clip(propensity + TRUE_LIFT * exposed, 0, 1)
    bought = rng.random(n) < p_buy
    return propensity, exposed, bought, TRUE_LIFT


def run_demo():
    propensity, exposed, bought, TRUE_LIFT = _simulate()
    base = bought[~exposed].mean()
    # NAIVE last-touch attribution: conversion rate among exposed minus unexposed (confounded by targeting)
    naive_lift = bought[exposed].mean() - bought[~exposed].mean()

    # IDENTIFIED effect: adjust for propensity (stratify) — the causal lift after controlling the confound
    bins = np.quantile(propensity, np.linspace(0, 1, 11))
    strata = np.clip(np.digitize(propensity, bins[1:-1]), 0, 9)
    diffs = []
    for s in range(10):
        m = strata == s
        if (exposed[m].sum() > 30) and ((~exposed[m]).sum() > 30):
            diffs.append(bought[m & exposed].mean() - bought[m & ~exposed].mean())
    identified_lift = float(np.mean(diffs))

    # MATCHED NULL: randomly relabel exposure (placebo) — what "lift" appears with no real targeting link?
    def perm(rng):
        sh = rng.permutation(exposed)
        return bought[sh].mean() - bought[~sh].mean()

    # SPECIFICATION CURVE: the lift under several defensible analytic choices
    specs = [naive_lift, identified_lift]
    # raw logit-style adjusted (coarse), top-half vs bottom-half propensity, trimmed, etc.
    for q in (0.25, 0.5, 0.75):
        hi = propensity >= np.quantile(propensity, q)
        if exposed[hi].sum() > 30 and (~exposed[hi]).sum() > 30:
            specs.append(bought[hi & exposed].mean() - bought[hi & ~exposed].mean())
    specs.append(identified_lift)  # weight the identified spec

    a = audit("Marketing: 'ad exposure lifts conversion' (last-touch claim)",
              claimed_effect=naive_lift, units="abs conversion rate",
              permutation_fn=perm, spec_effects=specs, identified_effect=identified_lift)
    print(one_pager(a))
    print(f"\n[ground truth lift = {TRUE_LIFT:+.3f} | identified ~= {identified_lift:+.3f} | "
          f"naive claim = {naive_lift:+.3f}]")
    return a


if __name__ == "__main__":
    run_demo()
