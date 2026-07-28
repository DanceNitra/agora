"""The identifiable three-way test for odd chains, with its own can-fail controls.

Companion to tat_odd_chain_design.py, which showed (arithmetically, before any data) that of the three
variables Marat asked us to separate, two are the same column and one is chain length relabelled. What is
left is a genuine and answerable question:

    among odd N > 3, does the metric differ between PRIME, DIVISIBLE-BY-3, and NEITHER,
    once the trend in N itself is removed?

The N covariate is not optional. Every odd family is spread over different N ranges -- the "neither" group
starts at 25 -- so a metric that simply drifts with chain length will manufacture a group difference out of
nothing. Removing the trend first is what makes the comparison about the label rather than about size.

USAGE with real data (his or ours):
    python research/probes/tat_odd_chain_test.py path/to/data.csv     # columns: N,metric

With no argument it runs SELF-VALIDATION: four synthetic datasets with a KNOWN planted effect. An
instrument that reports the same verdict on all four is not measuring anything, so it must find the
mod-3 effect, find the primality effect, find the pure-N trend as no group effect, and find nothing in
noise. This is the check that was missing when a probe of mine returned identical arms for a dissenting
and a consenting target: two arms agreeing is evidence only once they are known to differ.
"""
from __future__ import annotations

import sys

import numpy as np


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    return all(n % d for d in range(2, int(n**0.5) + 1))


def label(n: int) -> str:
    if n == 3:
        return "N=3 (unidentifiable)"
    if is_prime(n):
        return "prime"
    if n % 3 == 0:
        return "div3"
    return "neither"


def analyse(N, y, verbose=True):
    """Detrend in N, then compare the three identifiable groups. Returns {group: (n, mean_resid)}."""
    N = np.asarray(N, float)
    y = np.asarray(y, float)
    ok = np.isfinite(N) & np.isfinite(y)
    N, y = N[ok], y[ok]

    groups = np.array([label(int(n)) for n in N])
    keep = groups != "N=3 (unidentifiable)"          # reported separately; it cannot separate the factors

    # Detrend on the KEPT points only, so the one collinear point cannot tilt the baseline it is
    # then compared against.
    A = np.vstack([np.ones(keep.sum()), N[keep]]).T
    coef, *_ = np.linalg.lstsq(A, y[keep], rcond=None)
    resid = y - (coef[0] + coef[1] * N)

    out = {}
    for g in ("prime", "div3", "neither"):
        sel = groups == g
        if sel.sum():
            out[g] = (int(sel.sum()), float(resid[sel].mean()), float(resid[sel].std(ddof=1))
                      if sel.sum() > 1 else float("nan"))
    spread = max(v[1] for v in out.values()) - min(v[1] for v in out.values()) if out else float("nan")
    pooled = float(np.std(resid[keep], ddof=1)) if keep.sum() > 1 else float("nan")

    if verbose:
        print(f"   trend removed: y ~ {coef[0]:+.4f} {coef[1]:+.4f}*N")
        for g, (n, m, s) in out.items():
            print(f"     {g:8s} n={n:2d}  mean residual {m:+.4f}  sd {s:.4f}")
        n3 = groups == "N=3 (unidentifiable)"
        if n3.any():
            print(f"     N=3      reported alone: residual {resid[n3][0]:+.4f} "
                  f"(prime AND div3 -- the design cannot attribute it)")
        print(f"   group spread {spread:+.4f} vs pooled sd {pooled:.4f} "
              f"-> ratio {spread / pooled if pooled else float('nan'):.2f}")
    return out, spread, pooled


def _f_stat(resid, groups):
    """One-way F on the residuals. Unlike a spread-of-means, it weights each group by its SIZE."""
    gs = [resid[groups == g] for g in sorted(set(groups.tolist()))]
    gs = [g for g in gs if g.size]
    if len(gs) < 2:
        return float("nan")
    allv = np.concatenate(gs)
    grand = allv.mean()
    between = sum(g.size * (g.mean() - grand) ** 2 for g in gs) / (len(gs) - 1)
    within = sum(((g - g.mean()) ** 2).sum() for g in gs)
    dfw = allv.size - len(gs)
    if dfw <= 0 or within <= 0:
        return float("nan")
    return float(between / (within / dfw))


def permutation_p(N, y, n_perm=20000, seed=0, degree=2, partition=None):
    """PERMUTE THE LABELS, keep the data. Distribution-free, and it makes no assumption the small
    unequal groups would violate.

    The first version of this function thresholded (spread of group means)/(pooled sd) at a hand-picked
    0.75 and reported a GROUP EFFECT on pure noise -- a constant gate on a relative score, and the group
    means it compared were computed from as few as 4 points, so their scatter was mostly standard error.
    Never gate a relative score with a constant; ask instead how often chance alone does this well.

    `degree` is the order of the trend removed, and it defaults to 2 rather than 1 for a measured reason:
    the groups occupy different N ranges (the 'neither' group starts at 25), so ANY trend the detrender
    fails to capture reappears as a group difference. With a linear detrender and a purely quadratic
    metric carrying zero group structure, the residual group means spread by 0.13 -- a finding
    manufactured entirely by chain length.

    `partition` overrides the grouping, so an alternative reading of "arm length" (k mod 2, which is
    N mod 4, or k mod 5, which is N mod 5) can be tested with the same machinery. Those are genuinely
    different columns from divisibility-by-3 and deserve their own run, not an assumption.
    """
    N = np.asarray(N, float)
    y = np.asarray(y, float)
    ok = np.isfinite(N) & np.isfinite(y)
    N, y = N[ok], y[ok]
    groups = np.array([(partition or label)(int(n)) for n in N])
    keep = groups != "N=3 (unidentifiable)"
    A = np.vander(N[keep], degree + 1)
    coef, *_ = np.linalg.lstsq(A, y[keep], rcond=None)
    resid = y[keep] - A @ coef
    lab = groups[keep]

    obs = _f_stat(resid, lab)
    if not np.isfinite(obs):
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for i in range(n_perm):
        null[i] = _f_stat(resid, rng.permutation(lab))
    # +1 in both places: an observed value can never be reported as impossible under its own null.
    p = (1.0 + np.sum(null >= obs)) / (n_perm + 1.0)
    return obs, float(p)


def verdict(p, alpha=0.05):
    if not np.isfinite(p):
        return "NOT COMPUTABLE"
    return "GROUP EFFECT" if p < alpha else "no group effect"


def _self_validate():
    rng = np.random.default_rng(0)
    ODD = np.array([n for n in range(3, 60, 2)], float)

    def run(name, y, expected):
        print(f"\n-- {name}")
        analyse(ODD, y)
        f, p = permutation_p(ODD, y)
        got = verdict(p)
        ok = "OK" if got == expected else "FAILED"
        print(f"   F={f:.3f}  permutation p={p:.4f}  ->  {got}   (expected {expected})  [{ok}]")
        return got == expected

    print("SELF-VALIDATION -- an instrument that says the same thing to every input measures nothing.\n")
    results = [
        run("planted MOD-3 effect (+1.0 on N divisible by 3)",
            0.01 * ODD + np.where(ODD % 3 == 0, 1.0, 0.0) + 0.1 * rng.normal(size=ODD.size),
            "GROUP EFFECT"),
        run("planted PRIMALITY effect (+1.0 on primes)",
            0.01 * ODD + np.array([1.0 if is_prime(int(n)) else 0.0 for n in ODD])
            + 0.1 * rng.normal(size=ODD.size),
            "GROUP EFFECT"),
        run("pure TREND in N, no group structure",
            0.05 * ODD + 0.1 * rng.normal(size=ODD.size),
            "no group effect"),
        # The arm the red-team added. With a LINEAR detrender this curve alone produced a residual group
        # spread of 0.13 with no group structure planted, purely because the groups sit at different N.
        run("pure QUADRATIC trend, no group structure",
            0.002 * ODD**2 + 0.1 * rng.normal(size=ODD.size),
            "no group effect"),
    ]

    # NOT a pass/fail arm. A single noise draw cannot gate a test calibrated at alpha=0.05, because such
    # a test MUST fire on 1 draw in 20 -- that is what calibration means, and demanding it never fire
    # would only select for a dead test. (The first version of this file did exactly that, called the
    # instrument broken, and the instrument was fine.) The honest control is the RATE, measured below.
    print("\n-- one noise draw, illustrative only (a calibrated test fires here 1 time in 20)")
    _, p_noise = permutation_p(ODD, rng.normal(size=ODD.size))
    print(f"   permutation p={p_noise:.4f} -> {verdict(p_noise)}")
    print(f"\n{sum(results)}/4 named controls behaved as required.")

    # A single noise draw proves nothing about a FALSE-POSITIVE RATE. Measure it: many independent
    # noise datasets, and count how often the test cries effect. It must land near alpha, not below it
    # (a test that never fires is not conservative, it is dead) and not above.
    print("\n-- false-positive rate over 300 independent noise datasets (target ~= alpha = 0.05)")
    from concurrent.futures import ProcessPoolExecutor
    import os as _os
    trials = 300
    with ProcessPoolExecutor(max_workers=max(1, (_os.cpu_count() or 4) - 2)) as ex:
        ps = list(ex.map(_noise_p, range(trials)))
    fired = sum(1 for p in ps if np.isfinite(p) and p < 0.05)
    rate = fired / trials
    print(f"   fired {fired}/{trials} = {rate:.3f}")
    rate_ok = 0.01 <= rate <= 0.11
    print(f"   [{'OK' if rate_ok else 'FAILED'}] a test that fires far above alpha manufactures findings;")
    print("   one that never fires cannot find a real one either.")

    if not all(results) or not rate_ok:
        print("\nThe instrument is not trustworthy on real data until every control passes.")
        return 1
    print("\nThe trend arm is the load-bearing one: without detrending, a metric that merely grows with N")
    print("would be reported as a group difference, because the groups sit at different N.")
    return 0


def _noise_p(seed):
    """One noise dataset -> one p-value. Top-level so it can be sent to a worker process."""
    odd = np.array([n for n in range(3, 60, 2)], float)
    y = np.random.default_rng(1000 + seed).normal(size=odd.size)
    return permutation_p(odd, y, n_perm=2000, seed=seed)[1]


def main(argv):
    if len(argv) < 2:
        return _self_validate()
    import csv
    N, y = [], []
    with open(argv[1], newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                N.append(float(row["N"]))
                y.append(float(row["metric"]))
            except (KeyError, TypeError, ValueError):
                continue
    if len(N) < 6:
        print(f"only {len(N)} usable rows -- too few for a three-group comparison")
        return 1
    print(f"{len(N)} rows from {argv[1]}")
    _, spread, pooled = analyse(N, y)
    print(f"   verdict: {verdict(spread, pooled)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
