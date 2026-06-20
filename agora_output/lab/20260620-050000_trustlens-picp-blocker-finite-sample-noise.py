"""
Grounding for a GATED outreach draft on Khanz9664/TrustLens#145 (RFC: Regression Trust Score).

Their proposed HARD BLOCKERS are point thresholds on finite-sample estimates:
  - negative skill: R^2 < 0  -> auto grade D
  - severe miscoverage: calibration_error = PICP - target < -0.10  (i.e. PICP < 0.85 for a 95% target) -> grade D
But PICP and R^2 are ESTIMATES from a finite test set; both carry sampling noise. So a model that is
actually fine can be FALSE-BLOCKED purely by test-set noise on small evals. Quantify that false-block
rate vs test-set size n, so the recommendation (min-n guard / CI on the input, not a point threshold) is
evidence-backed. Pure numpy; no LLM. (Agora's wheelhouse: same eval-noise family as the winner's-curse entry.)
"""
import numpy as np

RNG = np.random.default_rng(0)
TARGET = 0.95
BLOCK_PICP = 0.85         # calibration_error < -0.10 for a 95% target
NDRAW = 4000


def picp_false_block(true_cov, n):
    """Model truly at coverage true_cov (>= 0.85, i.e. NOT meant to be blocked). How often does the
    empirical PICP over n points dip below 0.85 by chance -> false block?"""
    draws = RNG.binomial(n, true_cov, NDRAW) / n
    return float((draws < BLOCK_PICP).mean()), float(draws.std())


def r2_stats(true_r2, n, ny_var=1.0):
    """Sampling distribution of R-hat^2 = 1 - MSE/Var(y) for a model with true R^2 on n test points.
    Residual var = (1-true_r2)*ny_var; y var ~ ny_var. R2_hat = 1 - (sum res^2 / n) / (sample var of y)."""
    sd_res = np.sqrt((1 - true_r2) * ny_var)
    flips_neg = 0
    r2s = []
    for _ in range(NDRAW):
        y = RNG.normal(0, np.sqrt(ny_var), n)
        res = RNG.normal(0, sd_res, n)            # model residuals, independent of y scale here
        r2 = 1 - (np.mean(res ** 2)) / (np.var(y) + 1e-12)
        r2s.append(r2)
        if r2 < 0:
            flips_neg += 1
    return float(np.mean(r2s)), float(np.std(r2s)), flips_neg / NDRAW


print("=== TrustLens #145 blockers under finite-sample noise ===\n")
print("PICP severe-miscoverage blocker (PICP<0.85). False-block rate for models that are NOT meant to be blocked:")
print(f"  {'n':>5} | {'true cov 0.90':>14} | {'true cov 0.92':>14} | {'true cov 0.95':>14}")
for n in (20, 30, 50, 100, 200, 500):
    fb90, _ = picp_false_block(0.90, n)
    fb92, _ = picp_false_block(0.92, n)
    fb95, _ = picp_false_block(0.95, n)
    print(f"  {n:>5} | {fb90:>13.1%} | {fb92:>13.1%} | {fb95:>13.1%}")

print("\nNegative-skill blocker (R2_hat<0). False-block rate for weak-but-POSITIVE-skill models:")
print(f"  {'n':>5} | {'true R2 0.05':>13} | {'true R2 0.10':>13} | {'true R2 0.20':>13} | SD(R2_hat)@R2=.10")
for n in (20, 30, 50, 100, 200, 500):
    _, _, f05 = r2_stats(0.05, n)
    m10, sd10, f10 = r2_stats(0.10, n)
    _, _, f20 = r2_stats(0.20, n)
    print(f"  {n:>5} | {f05:>12.1%} | {f10:>12.1%} | {f20:>12.1%} | {sd10:>10.3f}")

# headline numbers for the draft
fb90_30, _ = picp_false_block(0.90, 30)
fb90_50, _ = picp_false_block(0.90, 50)
fb90_200, _ = picp_false_block(0.90, 200)
_, _, f10_30 = r2_stats(0.10, 30)
_, _, f10_200 = r2_stats(0.10, 200)
print("\n=== Headline (for the gated draft) ===")
print(f"A model truly at 90% coverage (calibration_error -0.05, NOT meant to be blocked) is FALSE-BLOCKED "
      f"by the PICP blocker {fb90_30:.0%} of the time at n=30, {fb90_50:.0%} at n=50, down to {fb90_200:.1%} at n=200.")
print(f"A weak-but-positive model (true R2=0.10) trips the negative-skill blocker {f10_30:.0%} of the time "
      f"at n=30, {f10_200:.1%} at n=200.")
print("Implication: gate the blockers on a minimum test-set size, or apply them to a one-sided confidence "
      "bound on PICP/R^2 rather than the point estimate, so a 'trust' score isn't itself noise-driven on small evals.")
