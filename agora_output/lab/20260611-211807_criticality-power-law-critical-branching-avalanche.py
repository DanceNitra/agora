"""
Replicate the core claim of Kitzbichler et al. (2009): critical systems show power-law scaling.
Smallest computable mechanism = a Galton-Watson branching process (the canonical model of neuronal
avalanches, Beggs & Plenz). Control parameter = branching ratio sigma (mean offspring).

Prediction (criticality => power law): at sigma=1 the avalanche-SIZE distribution is a power law
P(s) ~ s^(-3/2) (mean-field exponent); off-critical (sigma<1) it has an exponential cutoff and is
NOT a power law. If the critical run yields tau ~ 1.5 over a broad range and the subcritical run
does not, the claim's mechanism reproduces.
"""
import numpy as np

rng = np.random.default_rng(3)
SIZE_CAP = 1_000_000   # guard against supercritical runaway


def avalanche_sizes(sigma, n=200_000):
    sizes = np.empty(n, dtype=np.int64)
    for i in range(n):
        active, total = 1, 1
        while active > 0 and total < SIZE_CAP:
            # each active node spawns Poisson(sigma) descendants in the next generation
            active = int(rng.poisson(sigma * active))
            total += active
        sizes[i] = total
    return sizes


def fit_tail_exponent(sizes, smin=5, smax=2000):
    """MLE-ish power-law exponent via the slope of the log-log complementary CDF over [smin,smax]."""
    s = sizes[(sizes >= smin) & (sizes <= smax)]
    if len(s) < 200:
        return None
    vals, counts = np.unique(s, return_counts=True)
    pdf = counts / counts.sum()
    x, y = np.log(vals), np.log(pdf)
    A = np.vstack([x, np.ones_like(x)]).T
    slope, _ = np.linalg.lstsq(A, y, rcond=None)[0]
    return -slope   # P(s) ~ s^-tau


print(f"{'sigma':>6} {'mean_size':>10} {'max_size':>9} {'tail tau (P(s)~s^-tau)':>24} {'regime':>12}")
for sigma in (0.85, 0.95, 1.00, 1.05):
    sizes = avalanche_sizes(sigma)
    tau = fit_tail_exponent(sizes)
    runaway = float(np.mean(sizes >= SIZE_CAP))
    regime = "critical" if abs(sigma - 1.0) < 1e-9 else ("sub" if sigma < 1 else "super")
    taus = f"{tau:.2f}" if tau is not None else "n/a (cutoff)"
    print(f"{sigma:>6.2f} {sizes.mean():>10.1f} {sizes.max():>9d} {taus:>24} {regime:>12}"
          + (f"  runaway={runaway:.2%}" if runaway > 0 else ""))

print("\nReference mean-field critical exponent for avalanche size: tau = 3/2 = 1.50")
print("Power-law (tau~1.5) at sigma=1 + exponential cutoff below => criticality reproduces the claim.")
