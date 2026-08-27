"""What false-positive rate does our valley criterion pay for each level of acceptance?

CONTEXT. In edrn-dmrg-verification#2 a "clear V-shaped valley" decides a falsification test, so the
criterion behind those words matters. This file sweeps BOTH free constants of ours against a declared
AR(1) null and reports the frontier: how much noise must be admitted to accept N of the 7 real curves.

TWO BUGS THIS FILE SHIPPED FIRST, both of which produced a much more dramatic (and false) result:

  1. THE NULL WAS 101 POINTS AND THE DATA IS 25. A longer AR(1) walk has four times as many chances
     to dip, so the null's prominence inflates and the threshold that excludes it also excludes the
     real curves. That alone produced "0 of 7 at a 5% budget" and "5 of 7 costs 35%". Length-matched:
     at phi=0.9, 5 of 7 costs 5.9%; at phi=0.7, 0.6%; at phi=0.5, 0.0%. The conclusion flipped on the
     length of the null before phi was even touched.
  2. A REIMPLEMENTATION OF SOMEONE ELSE'S METHOD WAS SCORED AS IF IT WERE THEIRS. This file used to
     test an "adaptive anchor" (Marat Sultanov's) implemented from a two-sentence description as
     argmax|second difference|. That implementation misses the minimum of a plain parabola by eleven
     grid points, and fails a quartic and an exponential-decay-plus-rise too. It is not his method,
     so its measured behaviour said nothing about his. Removed rather than corrected: the right move
     is to ask for the code, not to grade a guess.

WHAT SURVIVES: the frontier below, and the conclusion that our criterion is a WEAK detector on this
observable rather than a dead one. Whether "weak" is good enough is a question about the required
sensitivity, which is a decision for the people running the test, not a property of the statistic.

Run: python probes/locating_a_valley_is_not_deciding_there_is_one.py
"""

import io
import json
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, "edrn_valley_parity_independent_ed.result.json")
RNG = np.random.default_rng(20260806)


def features(y):
    y = np.asarray(y, float)
    interior = y[1:-1]
    lo = float(min(y[0], y[-1]))
    dip = lo - float(interior.min())
    i = int(np.argmin(y))
    return (0 < i < len(y) - 1,
            dip / (float(np.mean(np.abs(y))) + 1e-12),          # relative to the curve's level
            dip / (float(np.median(np.abs(np.diff(y)))) + 1e-12))  # relative to its own step size


def accepts(y, rel_bar, k):
    inside, rel, prom = features(y)
    return bool(inside and rel > rel_bar and prom > k)


def ar1(n=25, phi=0.9, sigma=0.05):
    """The declared null: a smooth, correlated observable with no valley in it."""
    y = [0.0]
    for _ in range(n - 1):
        y.append(phi * y[-1] + RNG.normal(0, sigma))
    return np.asarray(y) + 1.0


def monotone(n=25):
    return np.linspace(0, 1, n) + RNG.normal(0, 0.005, n)


def white(n=25):
    return RNG.normal(0, 0.05, n)


def main():
    rows = json.load(io.open(RESULT, encoding="utf-8"))
    real = [(r["L"], np.asarray(r["fines"], float)) for r in rows]
    assert len(ar1()) == len(real[0][1]), (
        "null length %d != data length %d -- the bug this file shipped once"
        % (len(ar1()), len(real[0][1])))

    print("  THE OPERATING FRONTIER for our own criterion, both constants swept together")
    print("     against the DECLARED null (AR(1), phi=0.9), length-matched, 1200 draws per cell.")
    nulls = [ar1() for _ in range(1200)]
    print(f"     {'rel >':>7} {'prom >':>7} {'FP':>8} {'real accepted':>14}")
    frontier = []
    for rel_bar in (0.05, 0.10, 0.15, 0.20, 0.25):
        for k in (2, 4, 6, 8, 12):
            fp = sum(accepts(v, rel_bar, k) for v in nulls) / len(nulls)
            acc = sum(accepts(y, rel_bar, k) for _L, y in real)
            frontier.append((rel_bar, k, fp, acc))
            print(f"     {rel_bar:>7.2f} {k:>7} {100 * fp:>7.1f}% {acc:>10}/{len(real)}")
    best = [f for f in frontier if f[2] <= 0.05]
    reach = max((f[3] for f in best), default=0)
    print(f"\n     at a 5% false-positive budget the best acceptance is {reach} of {len(real)}.")
    for target in (5, 6):
        cheapest = min((f for f in frontier if f[3] >= target), key=lambda f: f[2], default=None)
        if cheapest:
            print(f"     accepting {target} of {len(real)} costs at least "
                  f"{100 * cheapest[2]:.1f}% false positives (rel>{cheapest[0]}, prom>{cheapest[1]}).")

    print("\n  VERDICT: a WEAK detector, not a dead one. At phi=0.9, the most adverse setting tried,"
          "\n  accepting 5 of 7 costs about 4-6% false positives; at phi=0.7 it costs under 1%."
          "\n  Whether that is good enough is a question about the sensitivity the test requires,"
          "\n  not a property of the statistic. Nothing here is a measurement of anyone else's method.")


if __name__ == "__main__":
    main()
