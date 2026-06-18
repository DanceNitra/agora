# "Design a causal DiD experiment for the Terman conscientiousness->longevity finding."
# The sharp methods result: you CANNOT DiD a stable trait. Conscientiousness is time-invariant with
# no manipulable treatment-onset, so DiD's machinery doesn't apply. The real threat is a STABLE
# unobserved confounder (childhood environment/genetics) driving both conscientiousness and longevity
# -- exactly what cross-sectional adjustment cannot remove. The correct quasi-experimental design is
# WITHIN-FAMILY (sibling/twin) differencing, which cancels the shared confounder. Smallest model
# measures the bias of each estimator against the known true effect. Source: simulation.
import numpy as np
rng = np.random.default_rng(0)

F = 40000                      # families
beta_true = 0.30               # TRUE causal effect of conscientiousness (SD) on longevity (years/SD)
alpha = 0.70                   # how much the shared family confounder U drives conscientiousness
gamma = 0.60                   # DIRECT confounding effect of U on longevity (the bias source)

U = rng.normal(size=F)                                   # stable unobserved family confounder
def sib():
    C = alpha * U + np.sqrt(max(1 - alpha**2, 0)) * rng.normal(size=F)   # conscientiousness (a trait)
    L = beta_true * C + gamma * U + rng.normal(size=F)                   # longevity
    return C, L
C1, L1 = sib(); C2, L2 = sib()
# a NOISY proxy for U that an analyst might control for (e.g., measured childhood SES), reliability rho
rho = 0.6
P1 = U + np.sqrt((1 - rho**2) / rho**2) * rng.normal(size=F)
P2 = U + np.sqrt((1 - rho**2) / rho**2) * rng.normal(size=F)

def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + X)
    return np.linalg.lstsq(X, y, rcond=None)[0]

C = np.concatenate([C1, C2]); L = np.concatenate([L1, L2]); P = np.concatenate([P1, P2])
b_naive = ols(L, [C])[1]                               # naive cross-sectional association
b_proxy = ols(L, [C, P])[1]                            # adjust for the noisy confounder proxy
# sibling fixed-effects: within-family difference cancels the shared U
dL = L1 - L2; dC = C1 - C2
b_sib = np.linalg.lstsq(dC[:, None], dL, rcond=None)[0][0]

def pct(b): return 100 * (b - beta_true) / beta_true
print(f"TRUE causal effect beta = {beta_true:.3f} (years of life per SD of conscientiousness)\n")
print(f"{'estimator':<34}{'beta_hat':>9}{'bias %':>9}")
print(f"{'naive cross-sectional OLS':<34}{b_naive:>9.3f}{pct(b_naive):>8.0f}%")
print(f"{'+ adjust for noisy U-proxy':<34}{b_proxy:>9.3f}{pct(b_proxy):>8.0f}%")
print(f"{'sibling fixed-effects (within-fam)':<34}{b_sib:>9.3f}{pct(b_sib):>8.0f}%")
print("\n=> Naive OLS and proxy-adjustment overstate the effect (stable confounder U leaks through);"
      "\n   sibling differencing recovers the true beta. DiD is INAPPLICABLE (no time-varying treatment"
      "\n   on a fixed trait) -- the right design for a trait->outcome claim is within-family, not DiD.")
