"""The Folklore Assayer -- King Aldric's organ.

REPLACES the Oracle (prediction-market betting) as Aldric's income/capability stream. The Oracle was
retired for three measured reasons, not for taste: its only reachable real-money book sits behind a
DNS content filter (Whalebone serves its block page for polymarket.com while api.github.com gets a
genuine certificate on the same interpreter); its forecasts mature on a 21-120 day horizon, so a daily
acceptance bar reads the organ as idle exactly when it is doing its job; and the ledger it fed measures
ANTI-skill -- 177 tournament forecasts hit 0.147 against 0.345 expected under this forecaster's own
call marginals, z = -6.64.

WHAT IT DOES INSTEAD. The field runs on folklore: "you need bi-temporal memory", "consolidation /
dreaming", "decision-trace memory", "forgetting aids creativity", "multi-agent beats single", "RAG
needs reranking", "more context is better". Most of it was measured once, on a weak or older model,
behind an LLM judge. Nobody systematically asks whether the advantage SURVIVES on a capable model or
is a weak-model crutch. Each claim gets a contrarian, judge-free, cloud-free test run across a
capability gradient, and a verdict: REAL / WEAK_MODEL_ARTIFACT / REGIME_SPECIFIC / INCONCLUSIVE.

Method and backlog are the owner's, set 2026-06-24 in
`agora_output/strategy/20260624_measuring-folklore-positioning.md`. Exhibit #1 is already measured
(decision-trace "why" memory: mean advantage +0.24 across 2B-30B, +0.00 at the frontier ->
WEAK_MODEL_ARTIFACT). That document has had no organ behind it for five weeks; this is the organ.

WHY ALDRIC STAYS A FORECASTER. The assay is PRE-REGISTERED: he records P(REAL) / P(WEAK_MODEL_ARTIFACT)
/ P(REGIME_SPECIFIC) BEFORE the gradient runs, and the verdict resolves it. The forecast ledger, the
Brier scoring and the resolver survive the rework unchanged -- only the question changes, from "what
will the market do" to "will this mechanism survive capability". That second question is on-frontier
(it is how an intelligence validates an idea), it resolves in hours rather than months, and being
badly calibrated on it is itself a publishable result.

TWO RULES THIS FILE EXISTS TO ENFORCE, both bought with real mistakes:

  * THE VERDICT IS COMPUTED FROM THE NUMBERS, NEVER WRITTEN AHEAD OF THEM. A Lab model shipped here
    once whose prose asserted "a small fraction" while its own MEASURED line said recall 1.000 -- the
    verdict had been written before the number. `classify()` below takes only floats and returns only
    a label; it cannot see any prose, so it cannot agree with one.

  * A VERDICT THAT CANNOT SAY "I DO NOT KNOW" IS DECORATION. INCONCLUSIVE is reachable and is the
    default when the intervals do not separate. A three-way forced choice over a noisy gradient would
    manufacture a verdict from noise at whatever rate the noise allows.
"""
from __future__ import annotations

import json
import math
import os
import time
from typing import Callable, Iterable, Sequence

LEDGER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".folklore.json")

#: Verdict vocabulary. INCONCLUSIVE is not a failure state -- it is the honest cell.
REAL = "REAL"
WEAK_MODEL_ARTIFACT = "WEAK_MODEL_ARTIFACT"
REGIME_SPECIFIC = "REGIME_SPECIFIC"
INCONCLUSIVE = "INCONCLUSIVE"
VERDICTS = (REAL, WEAK_MODEL_ARTIFACT, REGIME_SPECIFIC, INCONCLUSIVE)

#: The owner's backlog, verbatim from the 2026-06-24 positioning document. Each entry is one
#: capability-gradient verdict. `prior_note` records what is already known so a pre-registration is
#: made against the evidence that exists, not against a blank page.
BACKLOG = [
    {"id": "bitemporal-consolidation",
     "claim": "Bi-temporal consolidation improves recall.",
     "prior_note": "Partial result already: REGIME_SPECIFIC (matters only without in-text recency cues). "
                   "The gradient run is to confirm the advantage shrinks with capability."},
    {"id": "forgetting-aids-creativity",
     "claim": "Forgetting aids creativity / novelty.",
     "prior_note": "Refuted for a capable collective. The gradient run is to show whether WEAK models do benefit."},
    {"id": "multi-agent-beats-single",
     "claim": "Multi-agent beats single-agent at fixed cost.",
     "prior_note": "The standing RAMR flagship probe. The positioning doc calls this the most provocative "
                   "and most on-brand of the backlog."},
    {"id": "rag-needs-reranking",
     "claim": "RAG needs reranking / hybrid search.",
     "prior_note": "Untested here. Our own hybrid/RRF work found no win with a good embedder, which is a "
                   "corpus-level result and not a capability-gradient one."},
    {"id": "chain-of-thought-helps",
     "claim": "Chain-of-thought / scratchpad helps.",
     "prior_note": "Known capability-dependent in the literature; the contribution is quantifying the decay, "
                   "not discovering the direction. Cite the prior art or do not run it."},
    {"id": "more-context-is-better",
     "claim": "More context is better (vs lost-in-the-middle).",
     "prior_note": "Untested here."},
]


# ---------------------------------------------------------------------------------------------
# ledger
# ---------------------------------------------------------------------------------------------

def _load() -> list:
    try:
        with open(LEDGER, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save(items: list) -> None:
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, LEDGER)


#: Whose organ this is. Written onto every record, because the swarm acceptance bar credits work by
#: ACTOR and an unattributed row is either dropped or, worse, credited to whoever the ledger is
#: rostered to. That second failure already happened once here: rostering a shared ledger to Aldric
#: made him read as having produced forty records that another writer had made. A ledger with one
#: writer still has to say so.
ACTOR = "King Aldric"


def preregister(claim_id: str, probs: dict, rationale: str, task: str, actor: str = ACTOR) -> dict:
    """Record the forecast BEFORE the gradient runs. Returns the stored record.

    `probs` must carry a probability for each of REAL / WEAK_MODEL_ARTIFACT / REGIME_SPECIFIC and sum
    to 1 within a small tolerance. It is REJECTED otherwise rather than normalised: silently rescaling
    a forecaster's numbers destroys the thing the ledger exists to measure, and a forecaster who cannot
    produce a coherent distribution should fail loudly at write time.

    INCONCLUSIVE deliberately takes no prior mass. It is a statement about the EXPERIMENT's resolving
    power, not about the world, so scoring a forecaster on it would score them on our sample size.
    """
    missing = [k for k in (REAL, WEAK_MODEL_ARTIFACT, REGIME_SPECIFIC) if k not in probs]
    if missing:
        raise ValueError("pre-registration is missing a probability for: %s" % ", ".join(missing))
    total = sum(float(probs[k]) for k in (REAL, WEAK_MODEL_ARTIFACT, REGIME_SPECIFIC))
    if abs(total - 1.0) > 1e-6:
        raise ValueError("pre-registered probabilities sum to %.6f, not 1.0" % total)
    if not rationale.strip():
        raise ValueError("a pre-registration with no rationale is a number with no forecast behind it")

    rec = {
        "id": "%s-%d" % (claim_id, int(time.time())),
        "claim_id": claim_id,
        "task": task,
        "forecast": {k: round(float(probs[k]), 4) for k in (REAL, WEAK_MODEL_ARTIFACT, REGIME_SPECIFIC)},
        "rationale": rationale.strip(),
        "status": "open",
        "by": actor,
        "ts": time.time(),
    }
    items = _load()
    items.append(rec)
    _save(items)
    return rec


# ---------------------------------------------------------------------------------------------
# the verdict rule
# ---------------------------------------------------------------------------------------------

def _mean_sd(xs: Sequence[float]) -> tuple:
    n = len(xs)
    if n == 0:
        return 0.0, 0.0, 0
    m = sum(xs) / n
    if n < 2:
        return m, 0.0, n
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, math.sqrt(var), n


def _ci95(xs: Sequence[float]) -> tuple:
    """Normal-approximation 95% interval on the mean. Returns (mean, lo, hi, n).

    A t quantile would be the correct small-sample choice and 1.96 is deliberately NOT used blind
    here: `_TCRIT` carries the two-sided 0.975 Student-t values, because a normal cutoff applied to a
    t statistic on few degrees of freedom is exactly the error that put a spurious "~12% false
    positives at nominal 5%" into one of our own published posts before an adversarial re-audit
    caught it. At 4 df the correct cutoff is 2.776 and 1.96 gives a 12.2% size.
    """
    m, sd, n = _mean_sd(xs)
    if n < 2 or sd == 0.0:
        return m, m, m, n
    crit = _TCRIT.get(n - 1, 1.96)
    half = crit * sd / math.sqrt(n)
    return m, m - half, m + half, n


#: Two-sided 0.975 Student-t critical values by degrees of freedom; falls back to the normal quantile
#: only once df is large enough that the difference is below the noise we can resolve anyway.
_TCRIT = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
          9: 2.262, 10: 2.228, 12: 2.179, 15: 2.131, 20: 2.086, 30: 2.042, 60: 2.000}


def classify(frontier_adv: Sequence[float], weak_adv: Sequence[float],
             regime_split: dict = None, min_effect: float = 0.05) -> dict:
    """Compute the verdict from the measured advantages. Takes numbers, returns a label.

    `frontier_adv` / `weak_adv` are per-sample mechanism advantages (score WITH the mechanism minus
    score WITHOUT) at the frontier anchor and pooled across the sub-frontier tiers. `regime_split`, if
    given, maps a regime label to its own advantage samples.

    This function is given no prose and no claim text on purpose. It cannot be talked into agreeing
    with a conclusion that was written first, because it cannot see one.

    `min_effect` is the smallest advantage worth calling real. Without it, a large enough n turns any
    non-zero difference into a verdict, and "statistically distinguishable from zero" is not the same
    claim as "the mechanism matters".
    """
    f_m, f_lo, f_hi, f_n = _ci95(list(frontier_adv))
    w_m, w_lo, w_hi, w_n = _ci95(list(weak_adv))

    detail = {"frontier": {"mean": round(f_m, 4), "ci95": [round(f_lo, 4), round(f_hi, 4)], "n": f_n},
              "weak": {"mean": round(w_m, 4), "ci95": [round(w_lo, 4), round(w_hi, 4)], "n": w_n},
              "min_effect": min_effect}

    # Too little evidence to separate anything. Checked FIRST so a thin run can never reach a verdict.
    if f_n < 2 or w_n < 2:
        detail["why"] = "fewer than 2 samples on one side; the intervals do not exist"
        return {"verdict": INCONCLUSIVE, "detail": detail}

    frontier_real = f_lo > min_effect          # advantage survives capability
    frontier_null = f_hi < min_effect          # advantage is bounded BELOW the threshold, not merely unproven
    weak_real = w_lo > min_effect

    if regime_split:
        margins = {}
        for label, samples in regime_split.items():
            m, lo, hi, n = _ci95(list(samples))
            margins[label] = {"mean": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)], "n": n}
        detail["regimes"] = margins
        positives = [k for k, v in margins.items() if v["ci95"][0] > min_effect]
        nulls = [k for k, v in margins.items() if v["ci95"][1] < min_effect]
        if positives and nulls:
            detail["why"] = ("advantage present in %s and bounded below threshold in %s"
                             % (", ".join(sorted(positives)), ", ".join(sorted(nulls))))
            return {"verdict": REGIME_SPECIFIC, "detail": detail}

    if frontier_real:
        detail["why"] = "frontier advantage lower bound %.4f exceeds %.4f" % (f_lo, min_effect)
        return {"verdict": REAL, "detail": detail}

    if weak_real and frontier_null:
        detail["why"] = ("weak-tier advantage lower bound %.4f exceeds %.4f while the frontier upper "
                         "bound %.4f falls below it" % (w_lo, min_effect, f_hi))
        return {"verdict": WEAK_MODEL_ARTIFACT, "detail": detail}

    detail["why"] = ("no separation: frontier ci [%.4f, %.4f], weak ci [%.4f, %.4f] against threshold "
                     "%.4f" % (f_lo, f_hi, w_lo, w_hi, min_effect))
    return {"verdict": INCONCLUSIVE, "detail": detail}


# ---------------------------------------------------------------------------------------------
# scoring the pre-registration
# ---------------------------------------------------------------------------------------------

def brier(forecast: dict, verdict: str) -> float:
    """Multi-class Brier score: mean squared error over the three forecastable outcomes.

    Lower is better; 0.0 is a perfect call and 2/3 is what a uniform guess scores. Returns -1.0 for an
    INCONCLUSIVE verdict, which carries no prior mass and therefore cannot score a forecaster -- an
    experiment that failed to resolve is a fact about the experiment.
    """
    if verdict == INCONCLUSIVE:
        return -1.0
    total = 0.0
    for k in (REAL, WEAK_MODEL_ARTIFACT, REGIME_SPECIFIC):
        outcome = 1.0 if k == verdict else 0.0
        total += (float(forecast.get(k, 0.0)) - outcome) ** 2
    return round(total, 4)


def resolve(record_id: str, verdict: str, detail: dict, lab_id: str = "") -> dict:
    """Close an open pre-registration with a computed verdict. Refuses to invent one."""
    if verdict not in VERDICTS:
        raise ValueError("unknown verdict %r; expected one of %s" % (verdict, ", ".join(VERDICTS)))
    items = _load()
    for rec in items:
        if rec.get("id") == record_id and rec.get("status") == "open":
            rec["status"] = "resolved"
            rec["verdict"] = verdict
            rec["detail"] = detail
            rec["lab_id"] = lab_id
            rec["brier"] = brier(rec.get("forecast") or {}, verdict)
            rec["resolved_ts"] = time.time()
            _save(items)
            return rec
    raise LookupError("no open pre-registration with id %r" % record_id)


def status() -> dict:
    """What the organ has done. Read by the swarm acceptance bar.

    Reports `decisive` -- pre-registrations closed with a verdict that is not INCONCLUSIVE -- and
    `open`, so a run that is in flight reads as work in progress rather than as silence. This is the
    field the daily bar should count: unlike the Oracle's 21-120 day horizons, a gradient assay
    resolves within hours, so a daily criterion measures it honestly.
    """
    items = _load()
    resolved = [r for r in items if r.get("status") == "resolved"]
    scored = [r for r in resolved if isinstance(r.get("brier"), (int, float)) and r["brier"] >= 0]
    counts = {}
    for r in resolved:
        counts[r.get("verdict", "?")] = counts.get(r.get("verdict", "?"), 0) + 1
    done = {r.get("claim_id") for r in resolved}
    return {
        "total": len(items),
        "open": len([r for r in items if r.get("status") == "open"]),
        "decisive": len([r for r in resolved if r.get("verdict") != INCONCLUSIVE]),
        "inconclusive": counts.get(INCONCLUSIVE, 0),
        "by_verdict": counts,
        "mean_brier": round(sum(r["brier"] for r in scored) / len(scored), 4) if scored else None,
        "backlog_remaining": [b["id"] for b in BACKLOG if b["id"] not in done],
    }
