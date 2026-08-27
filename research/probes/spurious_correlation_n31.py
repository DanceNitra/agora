"""How often do INDEPENDENT short series reach |r| >= 0.985 at n = 31?

WHY THIS EXISTS. A collaboration reported r = 0.985 between two framework trajectories over 31 ordered
steps and assigned it P ~ 1e-6 on the assumption of two independent random sequences. The reflex
objection is "autocorrelated series correlate spuriously, so that p-value is meaningless." This measures
whether the reflex is right, and the answer is: not at 0.985, and the real question is a different one.

Two conditions matter and they give opposite answers:

  * WITHOUT a shared trend, autocorrelation does NOT manufacture 0.985. Random walks reach |r| >= 0.90
    about 1.3% of the time and |r| >= 0.985 about one time in a million. So the reported correlation is
    genuinely extraordinary against that null, and an objection resting on "spurious correlation" alone
    is wrong by roughly five orders of magnitude.
  * WITH a shared per-step drift, the answer moves across five orders of magnitude over a plausible
    range. Drift is therefore the load-bearing quantity, and any claim about the correlation -- for or
    against -- is unsupported until drift is estimated from the data.

The point of publishing this is not the numbers. It is that the numbers are cheap to produce and the
argument cannot be settled without them.

Exit 0 with the tables; the assertions at the end fail loudly if the qualitative conclusions invert.
"""
from __future__ import annotations

import numpy as np

SEED = 20260810
N = 31
TRIALS = 2_000_000
THRESH = 0.985


def _pairwise_abs_r(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    xc = x - x.mean(axis=1, keepdims=True)
    yc = y - y.mean(axis=1, keepdims=True)
    num = (xc * yc).sum(axis=1)
    den = np.sqrt((xc ** 2).sum(axis=1) * (yc ** 2).sum(axis=1))
    return np.abs(num / den)


def p_random_walk(rng, drift=0.0, thresh=THRESH, trials=TRIALS, n=N):
    """Two INDEPENDENT random walks that share a common per-step drift."""
    hits, done = 0, 0
    while done < trials:
        b = min(200_000, trials - done)
        x = np.cumsum(rng.standard_normal((b, n)) + drift, axis=1)
        y = np.cumsum(rng.standard_normal((b, n)) + drift, axis=1)
        hits += int((_pairwise_abs_r(x, y) >= thresh).sum())
        done += b
    return hits / trials, hits


def p_ar1(rng, phi, thresh=THRESH, trials=TRIALS, n=N):
    """Two INDEPENDENT AR(1) series -- stationary autocorrelation, no unit root."""
    hits, done = 0, 0
    while done < trials:
        b = min(200_000, trials - done)
        out = []
        for _ in range(2):
            e = rng.standard_normal((b, n))
            s = np.empty((b, n))
            s[:, 0] = e[:, 0] / np.sqrt(1 - phi ** 2)
            for t in range(1, n):
                s[:, t] = phi * s[:, t - 1] + e[:, t]
            out.append(s)
        hits += int((_pairwise_abs_r(out[0], out[1]) >= thresh).sum())
        done += b
    return hits / trials, hits


def _row(label, p, hits):
    inv = "1 in {:,}".format(int(1 / p)) if p else "1 in > {:,}".format(TRIALS)
    print("  %-34s %-14.8f %-20s (%d hits)" % (label, p, inv, hits))


def main() -> int:
    rng = np.random.default_rng(SEED)
    print("n = %d, %d trials per condition, threshold |r| >= %.3f, seed %d\n"
          % (N, TRIALS, THRESH, SEED))

    print("A. Is autocorrelation ALONE enough to reach 0.985?")
    p_rw0, h_rw0 = p_random_walk(rng, 0.0)
    _row("random walk, no drift", p_rw0, h_rw0)
    p_ar, h_ar = p_ar1(rng, 0.95)
    _row("AR(1), phi = 0.95", p_ar, h_ar)

    p90, _ = p_random_walk(rng, 0.0, thresh=0.90, trials=200_000)
    print("  (same walks reach |r| >= 0.90 with probability %.4f -- the reflex is right THERE)" % p90)

    print("\nB. How much does a SHARED per-step drift change it?")
    curve = {}
    for d in (0.0, 0.1, 0.2, 0.3, 0.5, 0.8):
        p, h = p_random_walk(rng, d)
        curve[d] = p
        _row("random walks, common drift %.1f" % d, p, h)

    print("\nMEASURED: autocorrelation alone does not reach 0.985 (P ~ %.1e)." % p_rw0)
    print("MEASURED: a shared drift of 0.8 makes it ordinary (P ~ %.1e) -- %.0fx the driftless rate."
          % (curve[0.8], curve[0.8] / p_rw0 if p_rw0 else float("inf")))
    print("\nVERDICT: 'spurious correlation' does NOT explain r = 0.985 by itself; the shared TREND does,"
          "\n         and only in proportion to a drift nobody has estimated. Estimate the drift before"
          "\n         arguing about the correlation, in either direction.")

    assert p_rw0 < 1e-4, "driftless walks now reach 0.985 easily; conclusion A has inverted"
    assert curve[0.8] > 100 * p_rw0, "drift no longer moves the answer; conclusion B has inverted"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
