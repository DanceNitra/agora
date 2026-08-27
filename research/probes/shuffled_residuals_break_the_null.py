"""Shuffling residuals destroys the autocorrelation that MAKES spurious correlation. Measure the cost.

WHY THIS EXISTS. A collaborator defended an observed correlation between two 31-step trajectories by
permuting residuals around a common drift: 10,000 trials, none reached the observed r, reported as
p = 0.0000. The protocol is the right shape and the conclusion may well be right. But an i.i.d.
shuffle of residuals removes their SERIAL DEPENDENCE, and serial dependence is the entire mechanism by
which independent series correlate spuriously (Yule 1926). The null it builds is therefore
"shared drift + white noise", not "shared drift + residuals like the ones we have".

So this does not argue. It measures the FALSE POSITIVE RATE of each null under conditions where the
answer is known: two series that are INDEPENDENT by construction. A valid test rejects about alpha of
the time. Anything much above that is a test that manufactures its own significance.

  * method A -- i.i.d. permutation of residuals (the protocol under review)
  * method B -- CIRCULAR BLOCK permutation of residuals, which keeps local dependence intact

CONTROL, and the run is void without it: at phi = 0 the residuals have no autocorrelation to destroy,
so both methods must sit near alpha. If A over-rejects there too, the harness is broken and nothing
below is about autocorrelation.

Exit 0 with the table. The assertions fail loudly if either conclusion inverts.
"""
from __future__ import annotations

import concurrent.futures as cf
import os

import numpy as np

N = 31                     # the series length under discussion
DRIFT = 0.1404             # the drift the collaborator estimated
PHIS = (0.0, 0.5, 0.8, 0.95)
DATASETS = 400             # independent (x, y) pairs per condition
B = 400                    # permutations per test
ALPHA = 0.05
SEED = 20260810


def _ar1(rng, n, phi, size):
    """AR(1) residuals with unit stationary variance (phi = 0 gives white noise)."""
    if phi == 0.0:
        return rng.standard_normal((size, n))
    e = rng.standard_normal((size, n))
    s = np.empty((size, n))
    s[:, 0] = e[:, 0] / np.sqrt(1 - phi ** 2)
    for t in range(1, n):
        s[:, t] = phi * s[:, t - 1] + e[:, t]
    return s


def _r(a, b):
    ac = a - a.mean(axis=-1, keepdims=True)
    bc = b - b.mean(axis=-1, keepdims=True)
    num = (ac * bc).sum(axis=-1)
    den = np.sqrt((ac ** 2).sum(axis=-1) * (bc ** 2).sum(axis=-1))
    return num / np.where(den == 0, np.nan, den)


def _detrend(series, t):
    """Remove the common linear trend, exactly as 'preserving the drift' requires."""
    slope = ((t - t.mean()) * (series - series.mean(axis=-1, keepdims=True))).sum(axis=-1) \
        / ((t - t.mean()) ** 2).sum()
    fitted = series.mean(axis=-1, keepdims=True) + slope[:, None] * (t - t.mean())
    return series - fitted, fitted


def _iid_perm(rng, resid, B):
    idx = np.argsort(rng.random((B, resid.shape[0])), axis=1)
    return resid[idx]


def _block_perm(rng, resid, B, block):
    """Circular block permutation: keeps runs of length `block` intact, so local dependence survives."""
    n = resid.shape[0]
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(B, nb))
    offs = np.arange(block)
    idx = (starts[:, :, None] + offs[None, None, :]).reshape(B, -1)[:, :n] % n
    return resid[idx]


def _one_condition(phi: float) -> dict:
    rng = np.random.default_rng(SEED + int(phi * 1000))
    t = np.arange(N, dtype=float)
    block = max(2, int(round(N ** (1 / 3))))
    rej_a = rej_b = 0
    # AND THE NUMBER THAT ACTUALLY SPEAKS TO THE CASE UNDER REVIEW. Rejecting too often at alpha=0.05
    # says the test is miscalibrated; it does NOT by itself justify doubting a result that beat EVERY
    # permutation. So count that event directly: under a TRUE null, how often does the observed r
    # exceed all B permuted values -- the "none of 10,000 reached it" outcome?
    beat_all_a = beat_all_b = 0
    for _ in range(DATASETS):
        # TWO INDEPENDENT SERIES. Any rejection below is a FALSE positive, by construction.
        x = DRIFT * t + _ar1(rng, N, phi, 1)[0]
        y = DRIFT * t + _ar1(rng, N, phi, 1)[0]
        obs = _r(x, y)
        rx, fx = _detrend(x[None, :], t)
        ry, fy = _detrend(y[None, :], t)
        rx, ry = rx[0], ry[0]

        na = _r(fx + _iid_perm(rng, rx, B), fy + _iid_perm(rng, ry, B))
        nb_ = _r(fx + _block_perm(rng, rx, B, block), fy + _block_perm(rng, ry, B, block))
        # one-sided, Phipson & Smyth (2010): (exceedances + 1) / (B + 1), never zero
        pa = (np.sum(na >= obs) + 1) / (B + 1)
        pb = (np.sum(nb_ >= obs) + 1) / (B + 1)
        rej_a += int(pa <= ALPHA)
        rej_b += int(pb <= ALPHA)
        beat_all_a += int(np.sum(na >= obs) == 0)
        beat_all_b += int(np.sum(nb_ >= obs) == 0)
    return {"phi": phi, "A": rej_a / DATASETS, "B": rej_b / DATASETS, "block": block,
            "beatA": beat_all_a / DATASETS, "beatB": beat_all_b / DATASETS}


def main() -> int:
    print("n = %d, drift = %.4f, %d independent (x,y) pairs per phi, %d permutations, alpha = %.2f"
          % (N, DRIFT, DATASETS, B, ALPHA))
    print("both series are INDEPENDENT by construction, so every rejection below is a FALSE positive\n")
    print("  %-6s %-14s %-14s  %-14s %-14s"
          % ("phi", "A reject@.05", "B reject@.05", "A beat ALL", "B beat ALL"))

    with cf.ProcessPoolExecutor(max_workers=min(len(PHIS), (os.cpu_count() or 4))) as pool:
        rows = sorted(pool.map(_one_condition, PHIS), key=lambda r: r["phi"])
    for r in rows:
        print("  %-6.2f %-14.3f %-14.3f  %-14.3f %-14.3f"
              % (r["phi"], r["A"], r["B"], r["beatA"], r["beatB"]))

    ctrl = next(r for r in rows if r["phi"] == 0.0)
    worst = max(rows, key=lambda r: r["A"])
    hi = max(rows, key=lambda r: r["beatA"])
    print("\nMEASURED (control): with NO autocorrelation to destroy, the i.i.d. shuffle rejects %.3f"
          " at nominal %.2f, and beats ALL %d permutations %.3f of the time"
          % (ctrl["A"], ALPHA, B, ctrl["beatA"]))
    print("MEASURED: at phi = %.2f it rejects %.3f, i.e. %.1fx the nominal rate, while the block"
          " version stays at %.3f" % (worst["phi"], worst["A"], worst["A"] / ALPHA, worst["B"]))
    print("MEASURED: at phi = %.2f an observed r beats EVERY one of %d permutations %.3f of the time"
          " under a TRUE null\n          (block version %.3f) -- that is the 'none of them reached it'"
          " outcome, arising by chance." % (hi["phi"], B, hi["beatA"], hi["beatB"]))
    print("\nVERDICT: an i.i.d. residual shuffle is not a null for autocorrelated trajectories. It"
          "\n         removes the dependence that generates spurious correlation, so the null sits too"
          "\n         low and too narrow, and 'none of 10,000 permutations reached it' becomes easy to"
          "\n         achieve whether or not the effect is real. Preserve the dependence (block or"
          "\n         stationary bootstrap) before reading the p-value.")

    assert ctrl["A"] <= 0.15, ("the CONTROL over-rejects with no autocorrelation present (%.3f): the "
                               "harness is broken and this measures nothing about serial dependence"
                               % ctrl["A"])
    assert worst["A"] > 2 * ALPHA, ("the i.i.d. shuffle no longer over-rejects (max %.3f); this "
                                    "conclusion has inverted -- re-read before citing it" % worst["A"])
    assert worst["B"] < worst["A"], "the block version is not better than the i.i.d. one; claim void"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
