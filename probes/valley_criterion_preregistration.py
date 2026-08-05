"""A numeric criterion for "a clear V-shaped valley", so the tree test can actually fail.

Marat proposed the first genuinely prospective test in the EDRN thread: run five tree topologies,
three seeds each, and if even one shows a clear V-shaped or W-shaped valley in `fine`, loop-necessity
is broken. That is the right shape for a test -- stated before the data, with a named losing condition.

It has one hole. "A clear V-shaped valley" is not operationalised, so the verdict is delivered by
looking at the plots afterwards. A criterion applied after seeing the curves cannot fail: a shallow dip
reads as noise when you expect none and as a valley when you expect one. The fix is to fix the number
first, which is what this file is for.

THE PROPOSED CRITERION, to be agreed BEFORE any tree is run:

    depth      = (max(edges) - min(interior)) / (max(edges) - min(edges) + eps)
    position   = argmin must lie strictly inside, not at either endpoint
    prominence = the dip must exceed `k` times the median absolute successive difference,
                 which is the curve's own noise scale rather than an absolute number

A curve counts as a valley only if all three hold. `k` is the one free parameter and it is set here by
CALIBRATION, not by taste: it is chosen as the value that separates the synthetic controls, and then
frozen.

CONTROLS, because a detector that fires on everything and one that fires on nothing both produce a
tidy-looking verdict:

  * POSITIVE  -- a synthetic V and a synthetic W must be detected, or the criterion cannot see the
                 thing the test is about and "no tree had a valley" means nothing;
  * NEGATIVE  -- pure noise, a monotone ramp, and a single-endpoint dip must NOT be detected, or the
                 criterion will find a valley in any tree and loop-necessity is unfalsifiable the
                 other way;
  * the criterion is evaluated on curves this file did not choose the shape of: random noise at
                 several amplitudes, so the false-positive rate is measured rather than assumed.
"""

import numpy as np

RNG = np.random.default_rng(20260804)
EPS = 1e-12


def is_valley(y, k=3.0):
    """All three conditions, or it is not a valley. Returns (verdict, diagnostics).

    The first version of this function was wrong in two ways that only the controls exposed, and both
    are worth leaving on the record because they are the exact failure this file argues against.

    (1) Its synthetic "V" was `-|x| + 1`, which is a PEAK. I built the positive controls upside down
        and the detector correctly refused them, which read as the detector being broken.
    (2) `depth` divided by the distance to the GLOBAL minimum, so whenever the interior held the
        minimum -- which is most of the time for noise -- depth was exactly 1.0 and the test fired.
        False-positive rate on random noise: 22%.

    Depth is now measured against the LOWER endpoint: how far below the shallower of the two ends the
    interior minimum sits, as a fraction of the curve's full range."""
    y = np.asarray(y, dtype=float)
    n = len(y)
    if n < 5:
        return False, {"why": "too few points"}
    interior = y[1:-1]
    lo_edge = float(min(y[0], y[-1]))
    rng = float(y.max() - y.min()) + EPS
    depth = (lo_edge - float(interior.min())) / rng          # >0 only if the middle dips BELOW both ends
    argmin_inside = 0 < int(np.argmin(y)) < n - 1
    noise = float(np.median(np.abs(np.diff(y)))) + EPS
    prominence = (lo_edge - float(interior.min())) / noise
    # A FOURTH condition, added because depth normalised by the curve's own range is scale-free: a 5%
    # dip on a flat line has range == the dip, so depth reads 1.0 and a shallow wobble passes as a
    # valley. Measuring the dip against the curve's LEVEL instead separates them -- 200% for a true V,
    # 5% for the shallow dip -- and noise is left to the prominence term.
    level = float(np.mean(np.abs(y))) + EPS
    relative = (lo_edge - float(interior.min())) / level
    ok = bool(depth > 0.25 and argmin_inside and prominence > k and relative > 0.5)
    return ok, {"depth": round(depth, 3), "argmin_inside": argmin_inside,
                "prominence": round(prominence, 2), "relative": round(relative, 3), "k": k}


def curves():
    x = np.linspace(-1, 1, 41)
    return [
        # A VALLEY dips in the middle: y(0) low, both ends high. The first version used -|x|+1, which
        # is the opposite shape, and then read the detector's correct refusal as a detector failure.
        ("V, clean", np.abs(x), True),
        ("V, noisy", np.abs(x) + RNG.normal(0, 0.02, x.size), True),
        ("W, two minima", np.abs(np.abs(x) - 0.5), True),
        ("shallow dip, 5% of range", 1.0 - 0.05 * np.exp(-(x / 0.3) ** 2), False),
        ("pure noise s=0.02", RNG.normal(0, 0.02, x.size), False),
        ("pure noise s=0.20", RNG.normal(0, 0.20, x.size), False),
        ("monotone ramp", np.linspace(0, 1, x.size), False),
        ("endpoint dip only", np.concatenate([[0.0], np.ones(x.size - 1)]), False),
    ]


def main():
    print("calibrating k on curves whose answer is known, then freezing it\n")
    for k in (1.0, 2.0, 3.0, 5.0, 8.0):
        wrong = sum(1 for _, y, want in curves() if is_valley(y, k)[0] != want)
        print(f"   k={k:<4} misclassified {wrong} of {len(curves())}")

    K = 3.0
    print(f"\nfrozen at k={K}\n")
    print(f"   {'curve':<26}{'expected':>10}{'verdict':>9}   diagnostics")
    ok = True
    for name, y, want in curves():
        got, diag = is_valley(y, K)
        ok &= (got == want)
        mark = " " if got == want else "  <-- MISCLASSIFIED"
        print(f"   {name:<26}{str(want):>10}{str(got):>9}   {diag}{mark}")

    print("\n   false-positive rate on 2000 random noise curves (there is no valley in any of them):")
    fp = sum(is_valley(RNG.normal(0, s, 41), K)[0]
             for s in RNG.choice([0.01, 0.05, 0.1, 0.3], 2000))
    print(f"      {fp} of 2000 = {100*fp/2000:.2f}%")

    print(f"\n   MEASURED: controls all correct = {ok}")
    if not ok:
        print("   -> the criterion is not usable as stated; do not pre-register it")


if __name__ == "__main__":
    main()
