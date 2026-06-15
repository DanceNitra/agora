"""
selfref — is your AI quietly training on itself?  (a mnemo sibling)

A self-reference GOVERNOR. Any system that consumes its own output — a model retrained on synthetic
data, an agent whose memory is its own past generations, a RAG store indexing the system's prior
answers, a recommender fed by the clicks it shaped — is a STRANGE LOOP. Strange loops have two
documented failure modes, and this measures both at YOUR settings (zero dependencies, deterministic):

  1) COLLAPSE (the data-mix law). Retrain recursively on your own outputs and diversity drains away
     (the "curse of recursion" / model collapse — a 2026 production concern, not just research). The
     cure is a floor of real/external data. We MEASURED the floor: with none, 94% of runs collapse;
     a ~5% external anchor pulls that to ~10%, and >=20% to 0%.

        collapse_risk(external_fraction)   -> collapse rate + verdict at your mix
        min_external_anchor()              -> the smallest real-data fraction that stays safe

  2) LOCK (the self-trust law). If a system weights its OWN prior belief faster than new evidence can
     correct it (self-trust exponent p>1), a fixed fraction of any initial bias is NEVER washed out,
     no matter how much data arrives. We have the closed form: p=1 is the safe boundary; p=1.5 locks
     17.7% of the bias, p=2 locks 50%, p=3 locks 81%.

        lock_fraction(p)                   -> permanent locked-bias fraction (analytic)
        lock_risk(p)                       -> verdict for a self-trust exponent

  audit(external_fraction, self_trust_p)   -> one combined SAFE/WATCH/COLLAPSE verdict + the fix

Grounding (reproduced this cycle): Agora Lab 75db49 (strange-loop attractor) — recursive self-training
collapse + the p>1 permanent-lock. `python selfref.py` reruns both so you can see the numbers yourself.
"""
from __future__ import annotations

import random
import statistics


# --------------------------------------------------------------------------- collapse (data-mix law)
def collapse_risk(external_fraction: float, *, generations: int = 120, samples_per_gen: int = 20,
                  trials: int = 200, true_std: float = 1.0, collapse_at: float = 0.5,
                  seed: int = 0) -> dict:
    """Simulate recursive self-training at a given external/real-data fraction f.

    Each generation fits a Gaussian to `samples_per_gen` samples = f*n drawn from the TRUE
    distribution + (1-f)*n drawn from the PREVIOUS generation's fit. With too little real data the
    fitted std drifts to ~0 (all diversity lost). Returns the fraction of independent runs that
    collapsed (final std < collapse_at * true_std) and a plain verdict.
    """
    f = max(0.0, min(1.0, external_fraction))
    n = samples_per_gen
    n_real = int(round(f * n))
    n_syn = n - n_real
    finals = []
    for s in range(trials):
        r = random.Random(seed * 100000 + s)
        mu, sig = 0.0, true_std
        for _ in range(generations):
            data = [r.gauss(0.0, true_std) for _ in range(n_real)] + \
                   [r.gauss(mu, max(sig, 1e-9)) for _ in range(n_syn)]
            mu = statistics.fmean(data)
            sig = statistics.stdev(data) if len(data) > 1 else 0.0
        finals.append(sig)
    collapse_rate = sum(1 for x in finals if x < collapse_at * true_std) / len(finals)
    return {"external_fraction": round(f, 4),
            "mean_final_diversity": round(statistics.fmean(finals), 3),
            "median_final_diversity": round(statistics.median(finals), 3),
            "collapse_rate": round(collapse_rate, 3),
            "verdict": _verdict_collapse(collapse_rate)}


def min_external_anchor(*, max_collapse_rate: float = 0.05, grid=(0.0, 0.02, 0.05, 0.10, 0.20, 0.50),
                        **kw) -> dict:
    """The smallest external/real-data fraction whose collapse rate stays <= max_collapse_rate.
    Answers the operational question: 'how much human/real data must I keep mixing in?'"""
    scan = []
    safe = None
    for f in grid:
        cr = collapse_risk(f, **kw)["collapse_rate"]
        scan.append({"f": f, "collapse_rate": cr})
        if safe is None and cr <= max_collapse_rate:
            safe = f
    return {"min_external_fraction": safe, "max_collapse_rate": max_collapse_rate, "scan": scan,
            "advice": (f"Keep >= {safe:.0%} of inputs real/external" if safe is not None
                       else "No tested fraction was safe — raise the real-data share or the budget")}


def _verdict_collapse(rate: float) -> str:
    if rate >= 0.5:
        return "COLLAPSE — most runs lose their diversity (curse of recursion); add a real-data anchor"
    if rate >= 0.1:
        return "WATCH — a meaningful share of runs collapse; raise the external fraction"
    return "SAFE — diversity holds across runs at this mix"


# ------------------------------------------------------------------------- lock (self-trust law, p)
def lock_fraction(self_trust_p: float, terms: int = 100000) -> float:
    """Permanent locked-bias fraction = prod_{n>=1} (1 - 1/(n+1)^p), the share of an initial bias that
    is NEVER washed out by unbiased evidence under self-trust schedule rho_n = 1 - 1/(n+1)^p.
    p<=1 -> 0 (bias washes out); p>1 -> a positive constant (permanent self-confirmation lock)."""
    prod = 1.0
    for n in range(1, terms):
        prod *= (1.0 - 1.0 / (n + 1.0) ** self_trust_p)
        if prod < 1e-12:
            return 0.0
    return prod


def lock_risk(self_trust_p: float) -> dict:
    """Verdict for a self-trust exponent p: how much of an initial bias gets permanently locked in."""
    frac = lock_fraction(self_trust_p)
    return {"self_trust_p": self_trust_p, "locked_bias_fraction": round(frac, 4),
            "verdict": _verdict_lock(frac, self_trust_p)}


def _verdict_lock(frac: float, p: float) -> str:
    if frac < 0.01:
        return f"SAFE — at p={p:g} bias washes out (evidence wins); p<=1 is the safe boundary"
    if frac < 0.2:
        return f"WATCH — p={p:g} locks {frac:.0%} of any bias permanently; pull self-trust toward p<=1"
    return f"LOCK — p={p:g} permanently locks {frac:.0%} of any bias; no amount of data corrects it"


# --------------------------------------------------------------------------------------- combined
def audit(external_fraction: float, self_trust_p: float = 1.0, **kw) -> dict:
    """One call, both laws: the data-mix collapse risk AND the self-trust lock risk, with a combined
    verdict (worst of the two) and the concrete fix."""
    c = collapse_risk(external_fraction, **{k: v for k, v in kw.items()
                                            if k in ("generations", "samples_per_gen", "trials",
                                                     "true_std", "collapse_at", "seed")})
    l = lock_risk(self_trust_p)
    order = {"SAFE": 0, "WATCH": 1, "COLLAPSE": 2, "LOCK": 2}
    cw = c["verdict"].split(" ")[0]
    lw = l["verdict"].split(" ")[0]
    worst = cw if order[cw] >= order[lw] else lw
    fixes = []
    if order[cw] >= 1:
        fixes.append("raise the real/external data fraction (>= ~5% is the measured knee, >= 20% is clean)")
    if order[lw] >= 1:
        fixes.append("cap self-trust so the prior never out-weights fresh evidence (keep p <= 1)")
    return {"collapse": c, "lock": l, "overall_verdict": worst,
            "fix": fixes or ["none — both laws are in the safe regime"]}


if __name__ == "__main__":
    print("selfref — self-reference governor (measured demo; reproduces Agora Lab 75db49)\n")
    print("1) COLLAPSE law — recursive self-training at varying real-data fraction f:")
    print(f"   {'real fraction f':>16}{'mean diversity':>16}{'collapse rate':>16}")
    for f in (0.0, 0.02, 0.05, 0.10, 0.20, 0.50):
        c = collapse_risk(f)
        print(f"   {f:>16.2f}{c['mean_final_diversity']:>16.3f}{c['collapse_rate']:>15.0%}")
    print("   ->", min_external_anchor()["advice"])

    print("\n2) LOCK law — permanent self-confirmation bias by self-trust exponent p:")
    for p in (0.5, 1.0, 1.5, 2.0, 3.0):
        l = lock_risk(p)
        print(f"   p={p:>3}: locked bias fraction = {l['locked_bias_fraction']:.4f}  ({l['verdict'].split(' ')[0]})")

    print("\n3) audit() — one combined verdict:")
    a = audit(external_fraction=0.0, self_trust_p=2.0)
    print("   pure self-training + p=2 :", a["overall_verdict"], "->", "; ".join(a["fix"]))
    a = audit(external_fraction=0.20, self_trust_p=1.0)
    print("   20% real + p=1           :", a["overall_verdict"])
