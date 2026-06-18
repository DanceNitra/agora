# Crucible replication (computable) of the deep-research finding: whether a mouse longevity compound
# is recorded as "working" can depend on the survival statistic chosen (log-rank vs Gehan-Wilcoxon),
# and reporting the best-of-several tests inflates the false-positive rate (garden-of-forking-paths).
# Source: deep-research 2026-06-16 + Jiang et al., GeroScience 2024 (Gehan reanalysis of NIA ITP data).
# Self-contained: implements the weighted log-rank family (no lifelines dependency).
import numpy as np
from math import erf, sqrt

rng = np.random.default_rng(42)

def wlr_p(t1, t2, scheme):
    """Two-sided weighted log-rank p-value. No censoring (lifespan study: all mice die).
    scheme: 'logrank' (w=1), 'gehan' (w=n at risk), 'tarone' (w=sqrt(n))."""
    s1, s2 = np.sort(t1), np.sort(t2); n1, n2 = len(s1), len(s2)
    ut = np.unique(np.concatenate([s1, s2]))
    ar1 = n1 - np.searchsorted(s1, ut, side='left')          # at risk in grp1 (time >= ut)
    ar2 = n2 - np.searchsorted(s2, ut, side='left')
    n = ar1 + ar2
    d1 = np.searchsorted(s1, ut, 'right') - np.searchsorted(s1, ut, 'left')
    d = d1 + (np.searchsorted(s2, ut, 'right') - np.searchsorted(s2, ut, 'left'))
    m = (n > 1) & (d > 0)
    ar1, n, d1, d = ar1[m], n[m], d1[m], d[m]
    w = {'logrank': np.ones_like(n, float), 'gehan': n.astype(float),
         'tarone': np.sqrt(n.astype(float))}[scheme]
    OE = np.sum(w * (d1 - d * ar1 / n))
    V = np.sum(w * w * d * (ar1 / n) * (1 - ar1 / n) * (n - d) / np.maximum(n - 1, 1))
    if V <= 0: return 1.0
    Z = OE / sqrt(V)
    return 2 * (1 - 0.5 * (1 + erf(abs(Z) / sqrt(2))))

def lifespans(n, age_localized_boost=0.0):
    """Mouse lifespans ~ Normal(900,130) days. age_localized_boost rescues EARLY-dying mice only
    (a benefit that fades with age -> non-proportional hazards), the regime where Gehan > log-rank."""
    x = rng.normal(900, 130, n)
    if age_localized_boost:
        early = x < np.quantile(x, 0.35)
        x[early] += age_localized_boost
    return np.clip(x, 1, None)

N_ARM, TRIALS, A = 50, 4000, 0.05

# (1) DISCORDANCE under a REAL age-localized effect: do the two tests agree on "it works"?
boost = 170.0
pl = np.empty(TRIALS); pg = np.empty(TRIALS); pt = np.empty(TRIALS)
for i in range(TRIALS):
    c = lifespans(N_ARM); t = lifespans(N_ARM, boost)
    pl[i], pg[i], pt[i] = wlr_p(c, t, 'logrank'), wlr_p(c, t, 'gehan'), wlr_p(c, t, 'tarone')
print(f"(1) Age-localized true effect (early-mortality rescue), n={N_ARM}/arm, {TRIALS} trials")
print(f"    log-rank power : {np.mean(pl<A):.1%}")
print(f"    Gehan power    : {np.mean(pg<A):.1%}")
print(f"    Tarone-Ware    : {np.mean(pt<A):.1%}")
disc = np.mean((pl >= A) & (pg < A))
print(f"    DISCORDANCE (log-rank says null, Gehan says works): {disc:.1%} of identical datasets\n")

# (2) FORKING-PATHS type-I inflation: under the NULL (no effect), report the BEST of the tests.
pl0 = np.empty(TRIALS); pg0 = np.empty(TRIALS); pt0 = np.empty(TRIALS)
for i in range(TRIALS):
    c = lifespans(N_ARM); t = lifespans(N_ARM)               # no effect
    pl0[i], pg0[i], pt0[i] = wlr_p(c, t, 'logrank'), wlr_p(c, t, 'gehan'), wlr_p(c, t, 'tarone')
fp_single = np.mean(pl0 < A)
fp_best = np.mean(np.minimum(np.minimum(pl0, pg0), pt0) < A)
print(f"(2) NULL (no real effect) - false-positive rate at alpha={A}")
print(f"    single pre-specified test : {fp_single:.1%}  (should be ~5%)")
print(f"    report BEST of 3 tests    : {fp_best:.1%}  (garden-of-forking-paths inflation)")
print(f"\nVERDICT: an age-localized geroprotector effect flips between 'null' and 'works' on "
      f"{disc:.0%} of identical datasets depending on log-rank vs Gehan; and cherry-picking the "
      f"best survival test inflates the false-positive rate from {fp_single:.0%} to {fp_best:.0%}.")
