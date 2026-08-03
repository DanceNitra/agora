"""Does the chi-square spread interval fail by a factor of (2 + g2)/2, with no n in it?

Context: measuring coverage of the nominal-95% chi-square interval for a spread across pools of
different excess kurtosis, no non-normal pool converged to nominal as n grew. jacksonxly proposed the
mechanism: chi-square assumes var(s^2) = 2 sigma^4 / n, while the truth is sigma^4 (2 + g2) / n, so the
interval is mis-scaled by 1 + g2/2 -- a constant, which is why growing n cannot fix it.

Agreeing with that is cheap. This tests it two ways that can FAIL:

  T1  DIRECTION AND SIZE. If the mechanism is the variance mis-scaling, then pools ordered by g2 must
      be ordered by coverage, and a pool with g2 < 0 must OVER-cover.

  T2  THE REPAIR. Substituting the true var(s^2) -- Satterthwaite effective df, d = 2n / (2 + g2) --
      must return coverage to nominal. A mechanism you can correct for is established; a mechanism you
      can only point at is a story. If the repaired interval still misses nominal, the mis-scaling is
      not the whole explanation and the original reading was too confident.

  T3  THE CONFOUND I FLAGGED MYSELF. My four-distinct-values pool over-covered to ~100%, but it is
      discrete, so "few distinct values" and "negative kurtosis" were not separated. jacksonxly's fix:
      symmetric beta(a, a) has excess kurtosis -6/(2a+3), so a = 0.7059 lands on the same -1.36 with
      CONTINUOUS support. If the two agree, kurtosis explains it and discreteness is not needed.

Controls: a normal pool must sit at nominal in every cell (else the harness is broken), and the
achieved g2 of each pool is measured from a large sample rather than assumed from the formula.
"""

import numpy as np
from scipy.stats import chi2

RNG_SEED = 20260803
DRAWS = 20000
NS = (5, 10, 20, 40, 80, 160, 320)
ALPHA = 0.05


def pools():
    """Each pool returns (sampler, true_sigma2, true_g2). g2 is the POPULATION excess kurtosis,
    derived in closed form -- a sample estimate of kurtosis is itself badly biased on a heavy tail,
    which is why the lognormal row was reported at 80.65 when the population value is 110.94."""
    e = np.e

    def normal(rng, size):
        return rng.standard_normal(size)

    # symmetric 4-point {-3,-1,1,3}: var = 5, m4 = 41, kurtosis 41/25 = 1.64 -> g2 = -1.36
    def four_values(rng, size):
        return rng.choice(np.array([-3.0, -1.0, 1.0, 3.0]), size=size)

    # symmetric beta(a,a), excess kurtosis -6/(2a+3); a = 0.7059 -> -1.36. Continuous support.
    A = 0.70588235
    def beta_matched(rng, size):
        return rng.beta(A, A, size=size)

    def lognormal(rng, size):
        return rng.lognormal(0.0, 1.0, size=size)

    beta_var = (A * A) / ((2 * A) ** 2 * (2 * A + 1))          # a*b / ((a+b)^2 (a+b+1))
    return [
        ("normal(0,1)  CONTROL", normal, 1.0, 0.0),
        ("four values {-3,-1,1,3}", four_values, 5.0, -1.36),
        ("beta(.706,.706) MATCHED", beta_matched, beta_var, -6.0 / (2 * A + 3)),
        ("lognormal(0,1)", lognormal, (e - 1) * e, e**4 + 2 * e**3 + 3 * e**2 - 6),
    ]


def coverage(sampler, sigma2, n, rng, g2=None):
    """Fraction of intervals containing the true sigma^2.

    g2=None -> the textbook chi-square interval (df = n-1).
    g2 given -> the repaired interval, Satterthwaite df = 2n/(2+g2) - 1, non-integer df used directly.

    The -1 is not cosmetic and it is mine, not the mechanism's: without it the repaired interval uses
    df = n where the textbook one uses n-1, and the NORMAL control then reads 91.9% at n=5 -- an
    artifact I would otherwise have charged to the kurtosis correction. With it the control is 95.0%
    at every n, so what remains below is the mechanism and not my off-by-one."""
    x = sampler(rng, (DRAWS, n))
    s2 = x.var(axis=1, ddof=1)
    df = (n - 1) if g2 is None else (2.0 * n / (2.0 + g2) - 1.0)
    if df <= 0:
        return float("nan"), x   # effective df below 1: see MIN_N below
    lo = df * s2 / chi2.ppf(1 - ALPHA / 2, df)
    hi = df * s2 / chi2.ppf(ALPHA / 2, df)
    return float(np.mean((lo <= sigma2) & (sigma2 <= hi))), x


def main():
    print(f"nominal 95% coverage of sigma^2, {DRAWS} draws/cell, seed {RNG_SEED}\n")
    hdr = "pool".ljust(25) + "g2".rjust(9) + "1+g2/2".rjust(9) + "".join(f"n={n}".rjust(8) for n in NS)
    print("== T1/T3  textbook chi-square interval ==")
    print(hdr)
    rows = {}
    for name, sampler, sigma2, g2 in pools():
        rng = np.random.default_rng(RNG_SEED)
        cov = [coverage(sampler, sigma2, n, rng)[0] for n in NS]
        rows[name] = cov
        print(name.ljust(25) + f"{g2:9.2f}" + f"{1 + g2 / 2:9.2f}"
              + "".join(f"{100*c:8.1f}" for c in cov))

    print("\n== T2  repaired interval, df = 2n/(2+g2) ==")
    print(hdr)
    rep = {}
    for name, sampler, sigma2, g2 in pools():
        rng = np.random.default_rng(RNG_SEED)
        cov = [coverage(sampler, sigma2, n, rng, g2=g2)[0] for n in NS]
        rep[name] = cov
        print(name.ljust(25) + f"{g2:9.2f}" + f"{1 + g2 / 2:9.2f}"
              + "".join(f"{100*c:8.1f}" for c in cov))

    # ---- controls -------------------------------------------------------------------------------
    print("\n== controls ==")
    ctrl = rows["normal(0,1)  CONTROL"]
    ok_ctrl = all(0.94 <= c <= 0.96 for c in ctrl)
    print(f"  harness control: normal within 94-96% in every cell = {ok_ctrl} "
          f"({min(ctrl)*100:.1f}-{max(ctrl)*100:.1f})")

    # the discreteness confound: does a CONTINUOUS pool at the same g2 reproduce the discrete one?
    a, b = rows["four values {-3,-1,1,3}"], rows["beta(.706,.706) MATCHED"]
    gap = max(abs(x - y) for x, y in zip(a, b))
    print(f"  T3 discrete vs continuous at g2=-1.36: max gap = {100*gap:.1f} pp "
          f"-> {'kurtosis explains it, discreteness NOT needed' if gap < 0.02 else 'they DIFFER -- discreteness carries part of it'}")

    # zero-width intervals are impossible on continuous support -- assert it, do not assume it
    rng = np.random.default_rng(RNG_SEED)
    _, xs = coverage(pools()[1][1], 5.0, 5, rng)
    zero_disc = float(np.mean(xs.var(axis=1, ddof=1) == 0))
    rng = np.random.default_rng(RNG_SEED)
    _, xb = coverage(pools()[2][1], pools()[2][2], 5, rng)
    zero_cont = float(np.mean(xb.var(axis=1, ddof=1) == 0))
    print(f"  all-identical draws at n=5: discrete {100*zero_disc:.1f}%  continuous {100*zero_cont:.1f}%")

    # T2 verdict, excluding the control
    bad = {k: v for k, v in rep.items() if "CONTROL" not in k
           and not all(0.93 <= c <= 0.97 for c in v)}
    print(f"  T2 repair returns every non-normal pool to 93-97%: {not bad}")
    for k, v in bad.items():
        print(f"      {k}: {['%.1f' % (100*c) for c in v]}")

    # What 1 + g2/2 MEANS as a sample size. df_eff = 2n/(2+g2) reaches 1 only at n = (2+g2)/2, so the
    # mis-scaling factor doubles as the number of real observations you need per effective degree of
    # freedom. Below that n the repaired interval is not merely inaccurate, it is undefined -- which is
    # the honest form of "chi-square is not a valid reference here".
    print("\n== real observations needed per effective degree of freedom ==")
    for name, _, _, g2 in pools():
        print(f"  {name.ljust(25)} g2 {g2:8.2f}   n for df_eff = 1: {max(1.0, (2 + g2) / 2):8.1f}")

    print(f"\nMEASURED: control_holds={ok_ctrl}  discreteness_needed={gap >= 0.02}  repair_works={not bad}")


if __name__ == "__main__":
    main()
