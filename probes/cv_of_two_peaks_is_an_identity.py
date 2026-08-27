"""A coefficient of variation over ONE spacing is zero by construction, not by discovery.

CONTEXT. On luoxuejian000/edrn-dmrg-verification#2, a moire-interference test on a 301-point curve
reported "exactly two peaks with perfectly constant spacing (CV = 0.000)" and read that as evidence
of a hidden microstructure that FFT, an adaptive filter and two TAT monitors all missed. The
accompanying white-noise control reported CV between 0.69 and 2.18.

THE POINT THIS FILE MAKES, and its whole scope: two peaks give ONE inter-peak spacing, the standard
deviation of a single number is zero, so CV is 0.000 identically -- on signal, on noise, on anything.
The reported noise control is therefore not matched: it returned MANY peaks, and comparing CV across
different peak counts compares the peak count, not the regularity.

WHAT THIS FILE DOES NOT DO. It does not reimplement moire interference and it makes no claim about
that method. We do not have their code, and grading a reimplementation of someone else's method is a
mistake this project has already made once in this same collaboration (an "adaptive anchor" rebuilt
from a two-sentence description behaved nothing like the real one, so its measured behaviour said
nothing about theirs). The subject here is the STATISTIC read off the method, and the conclusion is
conditional on CV having been computed over the spacings of the two reported peaks.

CONTROLS CARRIED:
  * the null must FAIL to be flat at k>2 -- otherwise this file would be reporting that CV is always
    zero, which would make it useless as a discriminator rather than making k=2 special;
  * a genuinely periodic signal at k=2 must ALSO score 0.000, showing the statistic cannot separate
    the two cases at that k;
  * an explicit count of how many random trials reach exactly 0.000 at each k.

Run: python probes/cv_of_two_peaks_is_an_identity.py
"""

import json
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cv_of_two_peaks_is_an_identity.result.json")

N_POINTS = 301          # the curve length reported in the thread
TRIALS = 2000
SEED = 20260806


def cv_of_spacings(peaks):
    """Coefficient of variation of the gaps between sorted peak positions."""
    d = np.diff(np.sort(np.asarray(peaks, float)))
    if d.size == 0:
        return float("nan")
    m = float(np.mean(d))
    return float(np.std(d) / m) if m else float("nan")


def main():
    rng = np.random.default_rng(SEED)
    rows = {}
    for k in (2, 3, 4, 6, 11):
        cvs = np.array([cv_of_spacings(rng.choice(N_POINTS, size=k, replace=False))
                        for _ in range(TRIALS)])
        rows[k] = {"mean_cv": round(float(np.mean(cvs)), 4),
                   "max_cv": round(float(np.max(cvs)), 4),
                   "trials_at_exactly_zero": int(np.sum(cvs < 1e-12)),
                   "trials": TRIALS}

    print(f"  CV of inter-peak spacing on PURE NOISE (uniform peak positions, n={N_POINTS}, "
          f"{TRIALS} trials)\n")
    print(f"  {'k peaks':>9}{'mean CV':>12}{'max CV':>12}{'CV exactly 0.000':>20}")
    for k, r in rows.items():
        at_zero = f"{r['trials_at_exactly_zero']}/{TRIALS}"
        print(f"  {k:>9}{r['mean_cv']:>12.4f}{r['max_cv']:>12.4f}{at_zero:>20}")

    # CONTROL 1: the statistic must NOT be degenerate above k=2, or this file proves nothing about k=2.
    discriminates = all(rows[k]["trials_at_exactly_zero"] < TRIALS * 0.02 for k in (4, 6, 11))
    # CONTROL 2: a genuinely periodic arrangement at k=2 scores the same 0.000 as noise does.
    periodic_k2 = cv_of_spacings([100, 200])
    noise_k2_all_zero = rows[2]["trials_at_exactly_zero"] == TRIALS

    print(f"\n  CONTROL, the statistic is not degenerate everywhere: at k>=4 it reaches exactly zero "
          f"in under 2% of trials -> {discriminates}")
    print(f"  CONTROL, a truly periodic pair scores: {periodic_k2:.4f}  (identical to noise at k=2)")
    print(f"  At k=2, noise reaches exactly 0.000 in {rows[2]['trials_at_exactly_zero']}/{TRIALS} trials.")

    verdict = ("At two peaks the coefficient of variation carries no information: noise and a periodic "
               "signal score the same 0.000, necessarily. A control that returned MANY peaks and scored "
               "0.69-2.18 is not matched to it -- that comparison varies k, not regularity."
               if (noise_k2_all_zero and discriminates and periodic_k2 == 0.0)
               else "INCONCLUSIVE: a control did not behave as required; do not use this file as evidence.")
    print(f"\n  {verdict}")

    payload = {"probe": "cv_of_two_peaks_is_an_identity", "n_points": N_POINTS, "trials": TRIALS,
               "seed": SEED, "by_k": {str(k): v for k, v in rows.items()},
               "control_not_degenerate_above_k2": discriminates,
               "control_periodic_pair_cv": periodic_k2,
               "noise_k2_all_exactly_zero": noise_k2_all_zero,
               "scope": "tests the STATISTIC only; does not reimplement or evaluate moire interference",
               "verdict": verdict}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    print(f"\nwrote {OUT}")
    return 0 if (noise_k2_all_zero and discriminates) else 2


if __name__ == "__main__":
    raise SystemExit(main())
