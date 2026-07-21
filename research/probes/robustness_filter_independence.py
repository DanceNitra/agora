# Runnable model for the post "Robustness checks aren't ritual - they're a measurable filter".
#
# Setup (the post's minimal model): a population of causal claims, 70% spurious. Each claim is put
# through 5 imperfect falsification tests. A genuinely REAL effect survives any one test w.p. 0.85;
# a SPURIOUS one survives w.p. 0.45. Among claims that survive exactly k of the 5 tests, what
# fraction is still false (the false-discovery rate)?
#
# Part A (analytic, reproduces the post's table): sequential Bayes / positive-predictive-value under
#   INDEPENDENT tests. FDR(k) = pi*Bin(k;5,0.45) / (pi*Bin(k;5,0.45) + (1-pi)*Bin(k;5,0.85)), pi=0.70.
#
# Part B (the experiment the post DEFERS, "the next thing to measure"): make the test outcomes
#   CORRELATED via a shared latent (Gaussian copula, correlation rho) and measure how fast the
#   filter degrades. At rho=0 the tests are independent (FDR@survive-all-5 ~9%); at rho=1 they are
#   one test wearing five hats, so surviving all five == surviving one, FDR -> the single-test value.
from math import comb, sqrt
import numpy as np

pi = 0.70                    # base rate of spurious claims
p_real, p_spur = 0.85, 0.45  # per-test survival probability

# ---- Part A: analytic FDR vs number of tests survived (independent) ----
def binpmf(k, n, p):
    return comb(n, k) * p**k * (1 - p)**(n - k)

print("Part A - independent tests, FDR among claims surviving exactly k of 5 (post's table):")
print(f"{'k':>3} {'FDR':>8}   [post]")
post_tbl = {0: "100%", 1: "~99.6%", 2: "~97%", 3: "~82%", 4: "~40%", 5: "~9%"}
for k in range(6):
    f = pi * binpmf(k, 5, p_spur)
    r = (1 - pi) * binpmf(k, 5, p_real)
    fdr = f / (f + r)
    print(f"{k:>3} {fdr:>8.4f}   [{post_tbl[k]}]")

# single-test posterior (the floor the filter collapses toward under full correlation)
fdr1 = pi * p_spur / (pi * p_spur + (1 - pi) * p_real)
print(f"\nFDR after surviving ONE test = {fdr1:.4f}  (the correlated-tests collapse floor)")

# ---- Part B: correlated tests via a Gaussian copula; FDR among survive-all-5 vs rho ----
# Zero-dependency inverse-normal CDF (Acklam approximation) so the copula needs no scipy.
def norm_ppf(p):
    # Peter Acklam's rational approximation to the inverse normal CDF (abs err < 1.15e-9).
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    p = np.asarray(p, float)
    plow, phigh = 0.02425, 1 - 0.02425
    q = np.empty_like(p)
    lo = p < plow; hi = p > phigh; mid = ~(lo | hi)
    ql = np.sqrt(-2 * np.log(p[lo]))
    q[lo] = (((((c[0]*ql+c[1])*ql+c[2])*ql+c[3])*ql+c[4])*ql+c[5]) / ((((d[0]*ql+d[1])*ql+d[2])*ql+d[3])*ql+1)
    qh = np.sqrt(-2 * np.log(1 - p[hi]))
    q[hi] = -(((((c[0]*qh+c[1])*qh+c[2])*qh+c[3])*qh+c[4])*qh+c[5]) / ((((d[0]*qh+d[1])*qh+d[2])*qh+d[3])*qh+1)
    r = (p[mid] - 0.5)
    r2 = r * r
    q[mid] = (((((a[0]*r2+a[1])*r2+a[2])*r2+a[3])*r2+a[4])*r2+a[5])*r / (((((b[0]*r2+b[1])*r2+b[2])*r2+b[3])*r2+b[4])*r2+1)
    return q

def fdr_survive_all5(rho, N=400000, seed=7):
    rng = np.random.default_rng(seed)
    is_spur = rng.random(N) < pi
    p = np.where(is_spur, p_spur, p_real)             # marginal survival prob per claim
    thr = norm_ppf(1 - p)                             # survive if latent > thr  => P(survive)=p
    Zc = rng.standard_normal(N)                       # shared component (common bias)
    survive_all = np.ones(N, bool)
    for _ in range(5):
        Zi = rng.standard_normal(N)
        latent = sqrt(rho) * Zc + sqrt(1 - rho) * Zi
        survive_all &= (latent > thr)
    surv = survive_all
    n_surv = surv.sum()
    fdr = (is_spur & surv).sum() / max(n_surv, 1)
    return fdr, n_surv / N

print("\nPart B - correlated tests (Gaussian copula, exchangeable), posterior FDR among survive-all-5 vs rho.")
print("(Averaged over 8 seeds; report 2 sig figs - the 3rd digit is Monte-Carlo noise.)")
print(f"{'rho':>5} {'FDR@5':>7} {'+-sd':>6} {'frac_surv':>10}")
for rho in (0.0, 0.2, 0.4, 0.6, 0.8, 0.95):
    vals = [fdr_survive_all5(rho, N=120000, seed=s)[0] for s in range(8)]
    fracs = [fdr_survive_all5(rho, N=120000, seed=s)[1] for s in range(8)]
    m = float(np.mean(vals)); sd = float(np.std(vals))
    print(f"{rho:>5} {m:>7.2f} {sd:>6.3f} {float(np.mean(fracs)):>10.2f}")
print(f"Note: exchangeable Gaussian copula has NO tail dependence, so it UNDERSTATES real degradation.")
print(f"At rho=0 it matches Part A (~0.09); as rho->1 it climbs toward the single-test floor {fdr1:.2f}.")

# ---- Part C: DETERMINISTIC shared bias (the more realistic dependence) ----
# Real robustness checks share ONE identifying assumption. Model it directly: a fraction phi of
# spurious claims are fooled by a common confound and pass ALL five tests together (the rest, and
# all real claims, face independent tests). This gives an IRREDUCIBLE FDR floor at ANY number of
# tests -- the failure the copula's zero-tail-dependence smooths away.
print("\nPart C - deterministic shared bias: fraction phi of spurious claims pass ALL tests together.")
print(f"{'phi':>5} {'FDR@5':>7}   (analytic)")
for phi in (0.0, 0.02, 0.05, 0.1, 0.2, 0.3):
    p_spur_all = phi + (1 - phi) * p_spur**5     # spurious survives all 5
    p_real_all = p_real**5
    fdr = pi * p_spur_all / (pi * p_spur_all + (1 - pi) * p_real_all)
    print(f"{phi:>5} {fdr:>7.2f}")
print(f"Even phi=0.05 (a confound fooling 1 in 20 spurious claims) lifts FDR@5 to ~0.26; phi=0.3 exceeds")
print(f"the single-test floor ({fdr1:.2f}) -- a shared assumption makes five checks WORSE than one honest test.")
