# Runnable model for the post "Why a more capable AI can be more confidently wrong".
# Claim: pooling K sources whose errors share a common component (pairwise correlation rho)
# makes a reasoner MORE confident without making it more accurate. A reasoner that treats the
# sources as independent shrinks its "95%" interval toward zero while the true error plateaus,
# so the interval's actual coverage of the truth collapses.
#
# This script reproduces every number in the post's coverage table and its two-stage fix:
#   naive 95%-CI coverage        : K=2/10/100 -> ~58% / ~50% / ~18%   (rho=0.4)
#   accuracy (RMS error)         : K=2/10/100 -> ~0.84 / ~0.68 / ~0.64, floor sqrt(rho)~=0.63
#   design-effect correction with the SAMPLE spread (self-calibration) -> only ~87% at large K,
#     because an equicorrelated sample's spread understates the true spread by sqrt(1-rho)
#   design-effect correction with the TRUE marginal spread supplied from OUTSIDE -> ~95% at every K
#
# Model: each source s_i = sqrt(rho)*C + sqrt(1-rho)*E_i, truth theta = 0, marginal var = 1.
# Effective independent count N_eff = K / (1 + (K-1)*rho) (Kish 1965 design effect).
import numpy as np

rho, TRIALS = 0.4, 40000
rng = np.random.default_rng(20)


def run(K):
    C = rng.standard_normal(TRIALS)                 # shared error component (echo chamber)
    E = rng.standard_normal((K, TRIALS))            # idiosyncratic per-source error
    src = np.sqrt(rho) * C[None, :] + np.sqrt(1 - rho) * E
    est = src.mean(0)                               # pooled point estimate
    err_rms = np.sqrt((est ** 2).mean())            # RMS error vs truth 0
    sd_sample = src.std(0, ddof=1)                  # spread measured WITHIN the correlated sample
    Neff = K / (1 + (K - 1) * rho)

    se_naive = sd_sample / np.sqrt(K)               # treats sources as iid
    cov_naive = np.mean(np.abs(est) <= 1.96 * se_naive)

    se_self = sd_sample / np.sqrt(Neff)             # design-effect correction, self-calibrated SD
    cov_self = np.mean(np.abs(est) <= 1.96 * se_self)

    se_ext = 1.0 / np.sqrt(Neff)                    # true marginal SD (=1) supplied from OUTSIDE
    cov_ext = np.mean(np.abs(est) <= 1.96 * se_ext)
    return err_rms, cov_naive, cov_self, cov_ext


print(f"rho={rho}, trials={TRIALS}, floor sqrt(rho)={np.sqrt(rho):.3f}")
print(f"{'K':>4} {'rms_err':>8} {'cov_naive':>10} {'cov_self(~87)':>13} {'cov_ext(~95)':>13}")
for K in (2, 10, 100):
    erms, cn, cs, ce = run(K)
    print(f"{K:>4} {erms:>8.3f} {cn:>10.3f} {cs:>13.3f} {ce:>13.3f}")

# Sensitivity of the naive-coverage collapse to rho (post cites ~43% at rho=0.1, ~57% at rho=0.05 for K=100).
print("\nnaive 95%-CI coverage at K=100 vs rho:")
for r in (0.4, 0.1, 0.05):
    C = rng.standard_normal(TRIALS)
    E = rng.standard_normal((100, TRIALS))
    src = np.sqrt(r) * C[None, :] + np.sqrt(1 - r) * E
    est = src.mean(0)
    se = src.std(0, ddof=1) / np.sqrt(100)
    print(f"  rho={r:<5} coverage={np.mean(np.abs(est) <= 1.96 * se):.3f}")
