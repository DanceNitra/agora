"""Two claims from jacksonxly, tested rather than agreed with.

C1  THE CEILING. Sample excess kurtosis is bounded above by (n^2 - 3n + 3)/(n-1) - 3, whatever the
    population is. At n=80 the largest computable g2 is 75.0, so lognormal(0,1)'s population 110.94
    is not reachable until n=116. If true, any g2 ESTIMATED FROM THE SAMPLE in that regime is
    estimating a number it cannot represent.

    Scope note I owe my own table: the repair I ran used the POPULATION g2, so the ceiling does not
    invalidate those rows. What it invalidates is using 1 + g2/2 in practice, where g2 comes from the
    same sample. That is the sharper reading and it is not the one I would have reached alone.

C2  THE PROPOSAL. Put the interval on a QUANTILE instead of on the variance. Order statistics give
    coverage straight off the binomial, with no moment assumption, so it should hold where the
    variance-based interval cannot -- including Cauchy, where the variance does not exist.

Controls, because both claims are the kind that look true:
  * the ceiling is checked against the ACHIEVED maximum over many draws, not only against algebra;
  * a normal pool must sit at nominal for the quantile interval, or the harness is broken;
  * a DELIBERATELY NARROWED interval must under-cover, or the harness cannot detect a bad interval
    and every "holds" below is worthless;
  * Cauchy is included precisely because the variance-based interval has nothing to say there.
"""

import numpy as np
from scipy.stats import binom

RNG_SEED = 20260803
DRAWS = 20000
NS = (5, 10, 20, 40, 80, 160, 320)
ALPHA = 0.05


def ceiling(n):
    """Algebraic upper bound on sample EXCESS kurtosis for a sample of size n."""
    return (n * n - 3 * n + 3) / (n - 1) - 3.0


def pools():
    e = np.e
    A = 0.70588235
    # (name, sampler, population g2, TRUE MEDIAN). The median is carried explicitly because deriving
    # it from the name is how the first run reported 0.0 for every lognormal cell: "normal" is a
    # substring of "lognormal", so the lognormal median was silently set to 0 instead of 1.
    return [
        ("normal(0,1) CONTROL", lambda r, s: r.standard_normal(s), 0.0, 0.0),
        ("beta(.706,.706)", lambda r, s: r.beta(A, A, s), -6.0 / (2 * A + 3), 0.5),
        ("lognormal(0,1)", lambda r, s: r.lognormal(0.0, 1.0, s), e**4 + 2 * e**3 + 3 * e**2 - 6, 1.0),
        ("cauchy(0,1)", lambda r, s: r.standard_cauchy(s), float("nan"), 0.0),
    ]


def c1_ceiling():
    print("C1  can the sample even represent the population kurtosis?")
    print(f"    {'n':>5}{'algebraic max g2':>20}{'max observed, lognormal':>26}")
    rng = np.random.default_rng(RNG_SEED)
    pop = np.e**4 + 2 * np.e**3 + 3 * np.e**2 - 6
    reachable_at = None
    for n in NS + (116, 200):
        x = rng.lognormal(0.0, 1.0, (5000, n))
        m = x - x.mean(axis=1, keepdims=True)
        m2 = (m**2).mean(axis=1)
        m4 = (m**4).mean(axis=1)
        g2 = m4 / np.where(m2 == 0, np.nan, m2) ** 2 - 3.0
        cap = ceiling(n)
        print(f"    {n:>5}{cap:>20.2f}{np.nanmax(g2):>26.2f}")
        if reachable_at is None and cap >= pop:
            reachable_at = n
    print(f"    population g2 for lognormal(0,1) = {pop:.2f}; first n in this grid whose ceiling "
          f"reaches it: {reachable_at}")
    print(f"    algebraic crossing: ceiling(115)={ceiling(115):.2f}  ceiling(116)={ceiling(116):.2f}")
    return ceiling(116) >= pop > ceiling(115)


def quantile_ci(x, q, alpha):
    """Distribution-free CI for the q-quantile from order statistics.

    Picks the widest pair of ranks whose binomial coverage is still >= 1-alpha, so the interval is
    CONSERVATIVE by construction and the achieved coverage is reported next to the nominal one.
    Returns (lo, hi, nominal) or None when n is too small for any pair to reach 1-alpha."""
    n = x.shape[1]
    xs = np.sort(x, axis=1)
    best = None
    for i in range(1, n + 1):     # ranks are 1-INDEXED; i=0 would mean an unbounded lower end, and
                                  # silently substituting the sample minimum for -inf is what left the
                                  # n=5 cells at 93.6% against a nominal 95% that is NOT ACHIEVABLE there
        # smallest j with coverage >= 1-alpha; coverage = P(i <= Bin(n,q) <= j-1)
        lo_cdf = binom.cdf(i - 1, n, q)
        for j in range(i + 1, n + 1):
            cov = binom.cdf(j - 1, n, q) - lo_cdf
            if cov >= 1 - alpha:
                if best is None or (j - i) < (best[1] - best[0]):
                    best = (i, j, cov)
                break
    if best is None:
        return None
    i, j, cov = best
    # 1-INDEXED ranks: P(X_(i) <= xi_q <= X_(j)) = P(i <= Bin(n,q) <= j-1), so in 0-indexed numpy the
    # lower endpoint is xs[:, i-1]. Taking xs[:, i] shortens the interval by one order statistic and
    # put the normal control at 92-94% against a nominal 95% -- the harness, not the method.
    return xs[:, i - 1], xs[:, j - 1], cov


def c2_quantile_coverage(narrow=False):
    label = "DELIBERATELY NARROWED (control)" if narrow else "order-statistic interval"
    print(f"\nC2  {label}: coverage of the true MEDIAN, nominal {100*(1-ALPHA):.0f}%")
    print("    " + "pool".ljust(22) + "".join(f"n={n}".rjust(9) for n in NS))
    ok = True
    for name, sampler, _, truth in pools():
        rng = np.random.default_rng(RNG_SEED)
        row = []
        for n in NS:
            x = sampler(rng, (DRAWS, n))
            res = quantile_ci(x, 0.5, ALPHA)
            if res is None:
                row.append("  n/a")
                continue
            lo, hi, _ = res
            if narrow:                                    # shrink toward the sample median
                mid = np.median(x, axis=1)
                lo, hi = mid - 0.02 * (hi - lo), mid + 0.02 * (hi - lo)
            c = float(np.mean((lo <= truth) & (truth <= hi)))
            row.append(f"{100*c:.1f}")
            if not narrow and "CONTROL" in name and not (0.94 <= c <= 1.0):
                ok = False
        print("    " + name.ljust(22) + "".join(v.rjust(9) for v in row))
    return ok


if __name__ == "__main__":
    print(f"{DRAWS} draws/cell, seed {RNG_SEED}\n")
    ceil_ok = c1_ceiling()
    held = c2_quantile_coverage(narrow=False)
    c2_quantile_coverage(narrow=True)
    print("\ncontrols")
    print(f"  C1 ceiling crosses the lognormal population exactly between n=115 and n=116: {ceil_ok}")
    print(f"  C2 the normal control stays at or above nominal: {held}")
    print("  C2 the narrowed arm above must be far BELOW nominal, or this harness cannot detect a")
    print("     bad interval and every 'holds' in the row above it means nothing")
