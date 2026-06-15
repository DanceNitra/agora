"""
nullcheck — is this number real, or just what noise would produce anyway?  (a mnemo sibling)

The one-line idea: a result is evidence of a real effect only if a model containing NO effect can't
reproduce it. So instead of trusting a p-value formula (and its assumptions), we SIMULATE the null —
the world where there is no true difference — using your actual sample sizes, and ask how often that
null produces a result as big as yours. If it does so often, your number is noise.

Built for the 2026 pain everyone has: teams "awash in data, can't tell signal from noise", A/B tools
that say 'significant' on a fluke, dashboards that move and nobody knows if it's real. Three things:

    ab_test(conv_a, n_a, conv_b, n_b)   conversion A/B by null simulation -> empirical p + verdict
    permutation_test(a_values, b_values) any two samples, assumption-free (shuffle the labels)
    peeking_false_positive_rate(...)     how badly 'checking the test early' inflates false positives

Zero dependencies (stdlib only), deterministic (fixed seeds). The verdict is plain language, and the
benchmark (`python nullcheck.py`) is one command so you can see the null reproduce a "win" yourself.
"""
from __future__ import annotations

import math
import random
import statistics


def _verdict(p: float) -> str:
    if p < 0.01:
        return "REAL — a no-effect null almost never reproduces this"
    if p < 0.05:
        return "LIKELY REAL — null reproduces it < 5% of the time"
    if p < 0.15:
        return "SUSPECT — could be noise; collect more before acting"
    return "NOISE — a no-effect null reproduces this routinely"


def ab_test(conv_a: int, n_a: int, conv_b: int, n_b: int, sims: int = 50000, seed: int = 7) -> dict:
    """A/B conversion test by NULL SIMULATION (no normality/large-sample assumption baked in).
    Observed lift = rate_b - rate_a. Null: both arms draw from the POOLED rate (no true difference).
    Empirical two-sided p = fraction of null draws with |lift| >= |observed|."""
    rng = random.Random(seed)
    ra, rb = conv_a / n_a, conv_b / n_b
    obs = rb - ra
    p0 = (conv_a + conv_b) / (n_a + n_b)
    sd_a = math.sqrt(max(1e-15, p0 * (1 - p0) / n_a))
    sd_b = math.sqrt(max(1e-15, p0 * (1 - p0) / n_b))
    hits = sum(1 for _ in range(sims) if abs(rng.gauss(0, sd_b) - rng.gauss(0, sd_a)) >= abs(obs))
    p = hits / sims
    return {"rate_a": round(ra, 4), "rate_b": round(rb, 4), "lift": round(obs, 4),
            "rel_lift": (round(obs / ra, 3) if ra else None), "p_empirical": round(p, 4),
            "verdict": _verdict(p)}


def permutation_test(a_values, b_values, sims: int = 20000, seed: int = 7) -> dict:
    """Assumption-free test for ANY two samples (revenue per user, latency, score…): if the label
    'A vs B' carried no signal, shuffling it should produce a mean-gap as big as yours just as often.
    Empirical two-sided p = fraction of label shuffles with |mean diff| >= |observed|."""
    rng = random.Random(seed)
    a, b = list(a_values), list(b_values)
    obs = statistics.mean(b) - statistics.mean(a)
    pool = a + b
    na = len(a)
    hits = 0
    for _ in range(sims):
        rng.shuffle(pool)
        d = statistics.fmean(pool[:na]) - statistics.fmean(pool[na:])
        if abs(d) >= abs(obs):
            hits += 1
    p = hits / sims
    return {"mean_a": round(statistics.fmean(a), 4), "mean_b": round(statistics.fmean(b), 4),
            "diff": round(obs, 4), "p_empirical": round(p, 4), "verdict": _verdict(p)}


def peeking_false_positive_rate(n_per_look: int = 400, peeks: int = 5, true_rate: float = 0.10,
                                experiments: int = 4000, alpha: float = 0.05, seed: int = 1) -> dict:
    """Quantify the most common way teams fool themselves: 'peeking' — re-running the test as data
    arrives and stopping when it first looks significant. Under a TRUE NULL (both arms identical),
    one honest look is wrong ~alpha of the time; `peeks` looks is much worse. Returns both rates."""
    rng = random.Random(seed)

    def z_p(ca, na, cb, nb):
        ra, rb = ca / na, cb / nb
        p0 = (ca + cb) / (na + nb)
        se = math.sqrt(max(1e-15, p0 * (1 - p0) * (1 / na + 1 / nb)))
        z = abs(rb - ra) / se
        return math.erfc(z / math.sqrt(2))                  # two-sided p

    single_fp = ever_fp = 0
    for _ in range(experiments):
        ca = na = cb = nb = 0
        ever = False
        for look in range(peeks):
            for _ in range(n_per_look):
                ca += rng.random() < true_rate; na += 1
                cb += rng.random() < true_rate; nb += 1
            p = z_p(ca, na, cb, nb)
            if look == 0 and p < alpha:
                single_fp += 1
            if p < alpha:
                ever = True
        ever_fp += ever
    return {"alpha": alpha, "peeks": peeks,
            "false_positive_one_look": round(single_fp / experiments, 3),
            "false_positive_with_peeking": round(ever_fp / experiments, 3),
            "inflation_x": round((ever_fp / max(1, single_fp)), 2)}


if __name__ == "__main__":
    print("nullcheck — measured demo\n")
    # 1) a fluke: 10.0% vs 11.5% on 1,000 each looks like a +15% lift, but is it real?
    print("A/B, 100/1000 vs 115/1000 (looks like +15% lift):")
    print("  ", ab_test(100, 1000, 115, 1000))
    # 2) a real effect at adequate n
    print("A/B, 1000/10000 vs 1180/10000 (+18% lift, big n):")
    print("  ", ab_test(1000, 10000, 1180, 10000))
    # 3) continuous (revenue/user), assumption-free
    rng = random.Random(0)
    a = [rng.gauss(20, 8) for _ in range(300)]
    b = [rng.gauss(20, 8) for _ in range(300)]        # SAME distribution -> a true null
    print("Permutation, two SAME-distribution samples (should read NOISE):")
    print("  ", permutation_test(a, b))
    # 4) the peeking trap, quantified
    print("Peeking trap (true null; 5 looks vs 1):")
    print("  ", peeking_false_positive_rate())
