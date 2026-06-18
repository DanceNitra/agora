"""
2nd-law attempt (Unification Engine): the Identification Threshold Law.

Law: a causal/true quantity is identified by STRUCTURE (graph + design), not data VOLUME. Below full
identification, bias persists at ANY N while the CI still shrinks ~1/sqrt(N) -> the danger zone is
HIGH-DATA + LOW-IDENTIFICATION (CONFIDENTLY WRONG; t-stat for the wrong value grows ~sqrt(N)). The
TELL of non-identification is SPECIFICATION INSTABILITY (the estimate moves across defensible control
sets), NOT a wide CI.

Subsumes: collider bias injects error regardless of N; A/B beats a quasi-experiment by a BIAS
threshold not sample size; causal inference has a phase diagram; alt-data alpha is an identification
premium. NOVEL prediction = the sqrt(N) confidently-wrong growth + the spec-instability (not CI)
detector.
"""
import numpy as np

def ols(Y, cols):
    M = np.column_stack([np.ones(len(Y))] + cols)
    coef, *_ = np.linalg.lstsq(M, Y, rcond=None)
    resid = Y - M @ coef
    s2 = resid @ resid / (len(Y) - M.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.inv(M.T @ M)))
    return float(coef[1]), float(se[1])      # coef on X (the first regressor after intercept)

def world(N, seed=0):
    """Two confounders drive X and Y; true effect of X on Y is 0."""
    rng = np.random.default_rng(seed)
    C1, C2 = rng.standard_normal(N), rng.standard_normal(N)
    X = 0.6*C1 + 0.6*C2 + rng.standard_normal(N)
    Y = 0.0*X + 0.6*C1 + 0.6*C2 + rng.standard_normal(N)   # beta_true = 0
    return X, Y, C1, C2

def est(N, control, seed=0):
    X, Y, C1, C2 = world(N, seed)
    cols = [X] + control(X, C1, C2)
    return ols(Y, cols)

# control specifications (each "defensible" to some analyst); only FULL identifies
SPECS = {
 "full[C1,C2]": lambda X,C1,C2: [C1, C2],
 "only C1":     lambda X,C1,C2: [C1],
 "only C2":     lambda X,C1,C2: [C2],
 "none":        lambda X,C1,C2: [],
 "proxy C1":    lambda X,C1,C2: [0.7*C1 + 0.7*np.random.default_rng(1).standard_normal(len(X))],
}

# (1) bias vs N for an under-identified spec (only C1) -> does NOT vanish with N
print("bias |beta_hat| (true=0), spec='only C1' (under-identified): does it vanish with N?")
for N in [1000, 10000, 100000]:
    b, se = est(N, SPECS["only C1"], seed=1)
    print(f"  N={N:<7} bias={abs(b):.3f}  SE={se:.4f}")

# (2) t-stat for the wrong value grows ~sqrt(N) (confidently wrong)
print("\nt-stat for the FALSE effect, spec='only C1':")
ts = {}
for N in [1000, 10000, 100000]:
    b, se = est(N, SPECS["only C1"], seed=2); ts[N] = abs(b/se)
    print(f"  N={N:<7} beta_hat={b:+.3f} SE={se:.4f} t={b/se:+.1f}")

# (3) the TELL: spec-dispersion across DEFENSIBLE control sets vs the (narrow) CI, at big N
print("\nNon-identification detector at N=20000: spread of beta_hat across DEFENSIBLE specs vs CI width")
N = 20000
betas = {}
for name, ctrl in SPECS.items():
    b, se = est(N, ctrl, seed=3); betas[name] = (b, se)
    print(f"  {name:<12} beta_hat={b:+.3f}  CI half-width~{1.96*se:.3f}")
incomplete = [betas[k][0] for k in ("only C1","only C2","none","proxy C1")]
disp = float(np.std(incomplete))
typ_ci = 1.96*np.mean([betas[k][1] for k in betas])
print(f"  -> spec-dispersion across defensible(incomplete) specs = {disp:.3f}")
print(f"  -> typical CI half-width                                = {typ_ci:.3f}")
print(f"  -> identified spec full[C1,C2] beta_hat = {betas['full[C1,C2]'][0]:+.3f} (~0, identified)")

# verdict
b1k = abs(est(1000, SPECS["only C1"], seed=1)[0]); b100k = abs(est(100000, SPECS["only C1"], seed=1)[0])
bias_persists = abs(b1k - b100k) < 0.05 and b100k > 0.1
t_grows = ts[100000] > 3*ts[1000]
detector = disp > 3*typ_ci         # the answer moves across specs by MORE than the CI says it should
print("\n=== VERDICT ===")
print(f"bias persists with N (identification, not data): {bias_persists}  ({b1k:.3f} vs {b100k:.3f})")
print(f"t-stat for the wrong value grows ~sqrt(N) (confidently wrong): {t_grows}  ({ts[1000]:.0f}->{ts[100000]:.0f})")
print(f"spec-instability >> CI detects non-identification: {detector}  (disp {disp:.3f} vs CI {typ_ci:.3f})")
print("LAW SUPPORTED" if (bias_persists and t_grows and detector) else "LAW NOT CLEAN")
print("Actionable: most dangerous = big-data + weak-identification; never read a narrow CI as evidence")
print("of identification -- read cross-specification STABILITY. Falsifier: bias shrinks with N at fixed")
print("under-identification, or spec-dispersion fails to exceed the CI when unidentified.")
