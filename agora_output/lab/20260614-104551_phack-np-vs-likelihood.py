import numpy as np
from scipy import stats

rng = np.random.default_rng(20260614)

N = 5000          # replications
n = 30            # sample size per analysis
K = 5             # number of analyses the p-hacker tries
ALPHA = 0.05

# TRUE NULL throughout: every analysis draws from N(0,1); H0: mu=0 is TRUE.
# A "p-hacker" runs K independent analyses and reports the most favorable one.

# Pre-draw all data: shape (N, K) sample means under the null. xbar ~ N(0, 1/n).
xbar = rng.normal(0.0, 1.0/np.sqrt(n), size=(N, K))
z = xbar * np.sqrt(n)                      # standardized; under null ~ N(0,1)
p = 2.0 * stats.norm.sf(np.abs(z))         # two-sided p per analysis (Uniform(0,1) under null)

# ============================================================
# (a) ERROR-STATISTICAL (Neyman-Pearson)
# ============================================================
# Honest, pre-registered single test:
type1_honest = (p[:,0] < ALPHA).mean()
# p-hacked: report the smallest p of K, judge against the SAME alpha (ignore selection):
pmin = p.min(axis=1)
type1_hacked = (pmin < ALPHA).mean()
np_theory = 1 - (1-ALPHA)**K

# ============================================================
# (b) FORMAL / LIKELIHOOD inference
# ============================================================
# Bayes factor BF10 for H0:mu=0 vs H1:mu~N(0, g/n), g=1 (unit-information prior).
g = 1.0
var0, var1 = 1.0/n, 1.0/n + g/n
logBF10 = stats.norm.logpdf(xbar, 0, np.sqrt(var1)) - stats.norm.logpdf(xbar, 0, np.sqrt(var0))
BF10 = np.exp(logBF10)
THRESH = 3.0   # "moderate evidence for H1"

# (b1) NAIVE BF cherry-picking: report the LARGEST BF of K, ignore the selection.
fp_bf_naive_hacked = (BF10.max(axis=1) > THRESH).mean()
fp_bf_honest       = (BF10[:,0] > THRESH).mean()

# (b2) SELECTION-ACCOUNTED likelihood inference (the paper's actual claim).
# The likelihood principle says inference uses the likelihood of the DATA under the
# models. If you *report the maximum*, the correct likelihood of the reported statistic
# must use the sampling distribution of the MAXIMUM, i.e. the data model is
# "T = max over K analyses". A formal/likelihood analyst who accounts for the stopping/
# selection rule compares the likelihood of the observed max-statistic under H0 vs H1
# using the order-statistic (best-of-K) distributions.
#
# Concretely: let S = max_k BF10_k be the reported evidence. Its DECISION rule, to keep a
# calibrated false-positive rate, must use the correct null distribution of S. We compute
# the BF for the *event actually reported* ("the best of K looked like this") under H0 vs H1
# by Monte-Carlo-calibrating the threshold so the selection is honored.
#
# Operationally we test: is the SELECTION-CORRECTED likelihood-ratio false-positive rate
# controlled? We do this by computing, for the reported (argmax) analysis, the BF that
# integrates the selection: under H0 the reported xbar is the max-|z| of K nulls, so its
# correct null density is the order-statistic density; under H1 likewise. The corrected
# BF uses these.
kmax = np.argmax(np.abs(z), axis=1)
zrep = z[np.arange(N), kmax]               # the reported (most extreme) z
# Null density of the max-|z| of K iid N(0,1): f(t) = K * [2*(Phi(t)-0.5)]^(K-1) * 2*phi(t), t>=0
def maxabs_null_logpdf(t, K):
    t = np.abs(t)
    F = 2*stats.norm.cdf(t) - 1.0          # P(|Z|<=t)
    F = np.clip(F, 1e-300, 1.0)
    return np.log(K) + (K-1)*np.log(F) + np.log(2.0) + stats.norm.logpdf(t)
# H1 density of one xbar ~ N(0, var1); in z-units that's N(0, n*var1)=N(0, 1+g). Max-|z| of K such:
sd1_z = np.sqrt(1.0 + g)
def maxabs_alt_logpdf(t, K, sd):
    t = np.abs(t)
    F = 2*stats.norm.cdf(t/sd) - 1.0
    F = np.clip(F, 1e-300, 1.0)
    return np.log(K) + (K-1)*np.log(F) + np.log(2.0) - np.log(sd) + stats.norm.logpdf(t/sd)
logBF_corrected = maxabs_alt_logpdf(zrep, K, sd1_z) - maxabs_null_logpdf(zrep, K)
BF_corrected = np.exp(logBF_corrected)
fp_bf_corrected = (BF_corrected > THRESH).mean()

print("=== p-hacking under a TRUE NULL (H0 true everywhere) ===")
print(f"replications={N}, n={n}, K={K} analyses tried, alpha={ALPHA}, BF threshold={THRESH}")
print("")
print("(a) ERROR-STATISTICAL  (Neyman-Pearson p-values)")
print(f"  honest single test Type I error : {type1_honest:.4f}  (target {ALPHA})")
print(f"  p-HACKED (min of {K} p's)        : {type1_hacked:.4f}  [theory 1-.95^{K}={np_theory:.4f}]")
print(f"  >>> inflation: {type1_honest:.3f} -> {type1_hacked:.3f}  ({type1_hacked/type1_honest:.2f}x)")
print("")
print("(b) FORMAL / LIKELIHOOD inference (Bayes factor)")
print(f"  honest single BF false-positive  : {fp_bf_honest:.4f}")
print(f"  (b1) NAIVE BF-hack (max of {K} BFs, IGNORE selection): {fp_bf_naive_hacked:.4f}  ({fp_bf_naive_hacked/max(fp_bf_honest,1e-9):.2f}x)")
print(f"  (b2) SELECTION-ACCOUNTED likelihood (paper's claim)  : {fp_bf_corrected:.4f}  ({fp_bf_corrected/max(fp_bf_honest,1e-9):.2f}x)")
print("")
print("=== INTERPRETATION ===")
print(f"NP p-hacking inflation        : +{(type1_hacked-type1_honest)*100:.1f} pp  (0.05 -> {type1_hacked:.2f})")
print(f"Naive BF cherry-pick inflation: +{(fp_bf_naive_hacked-fp_bf_honest)*100:.1f} pp")
print(f"Selection-accounted likelihood: +{(fp_bf_corrected-fp_bf_honest)*100:.1f} pp  (claim: ~no inflation)")
