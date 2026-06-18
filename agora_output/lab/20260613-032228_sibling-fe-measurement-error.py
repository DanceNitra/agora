# Self-challenge to "use sibling fixed-effects for conscientiousness->longevity" (lab 74e0ff).
# That sim had PERFECTLY measured conscientiousness. Sibling-FE is notoriously fragile to MEASUREMENT
# ERROR: within-family differencing removes the shared confounder but also strips most of the true
# signal (siblings are similar), so measurement-error noise dominates ΔC -> severe attenuation toward
# zero. Measure β̂ vs the reliability of the conscientiousness scale, and the reliability-corrected fix.
# Source: simulation.
import numpy as np
rng = np.random.default_rng(0)

F = 80000
beta_true = 0.30
alpha = 0.70                      # family-confounder loading on conscientiousness
gamma = 0.60                      # direct confounding U->longevity

U = rng.normal(size=F)
def sib():
    Ctrue = alpha*U + np.sqrt(1-alpha**2)*rng.normal(size=F)     # Var(Ctrue)=1
    L = beta_true*Ctrue + gamma*U + rng.normal(size=F)           # longevity depends on TRUE C
    return Ctrue, L
C1t, L1 = sib(); C2t, L2 = sib()

def ols1(y, x):
    x = np.column_stack([np.ones(len(y)), x])
    return np.linalg.lstsq(x, y, rcond=None)[0][1]

print(f"TRUE beta = {beta_true}\n")
print(f"{'reliability ρ':>13}{'naive OLS':>11}{'sibling-FE':>12}{'FE + reliab.-corrected':>24}")
for rho in [1.00, 0.90, 0.80, 0.70, 0.60, 0.50]:
    sig2 = (1-rho)/rho                          # measurement-error variance for this reliability
    e = lambda: np.sqrt(sig2)*rng.normal(size=F)
    C1, C2 = C1t+e(), C2t+e()                   # observed (noisy) conscientiousness
    b_naive = ols1(np.concatenate([L1,L2]), np.concatenate([C1,C2]))
    dL, dC = L1-L2, C1-C2
    b_fe = np.linalg.lstsq(dC[:,None], dL, rcond=None)[0][0]
    # reliability correction: divide by the within-family attenuation factor
    var_dCtrue = np.var((C1t-C2t)); var_dCobs = np.var(dC)
    b_fe_corr = b_fe * var_dCobs/var_dCtrue
    print(f"{rho:>13.2f}{b_naive:>11.3f}{b_fe:>12.3f}{b_fe_corr:>24.3f}")
print("\n=> Sibling-FE is unbiased ONLY at perfect measurement (ρ=1). At realistic personality-scale"
      "\n   reliability (ρ≈0.7-0.8) it attenuates 30-50% toward zero — trading confounding bias for"
      "\n   measurement-error bias. The clean tool is sibling-FE PLUS a reliability correction (or a"
      "\n   high-reliability measure). My earlier note oversold the raw within-family estimate. REFINED.")
