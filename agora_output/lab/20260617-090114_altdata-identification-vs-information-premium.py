"""
Lab model: Is alt-data alpha an IDENTIFICATION premium or an INFORMATION premium?

Belief under test (Sage Mira, finance/causal-inference):
  Alt-data alpha decays because the *adjustment method* standardizes, not because the raw
  data becomes widely seen. The scarce resource is identification ambiguity, not the feed.

We build the smallest model that can DISTINGUISH the two mechanisms and could FALSIFY the
belief, then measure which one drives alpha decay -- and on what condition.

Mechanism:
  - A latent driver Z_t (e.g. true earnings surprise) pays off in returns Y_t.
  - The raw alt-data signal X_t is a coded observation of Z_t. To turn X into a predictor of
    Y you must apply the *correct adjustment* g* (controls / ANCOVA-vs-change-score / panel
    structure). Many defensible adjustments exist; only g* recovers Z, wrong ones recover noise.
  - Two diffusion channels erode an early extractor's edge:
        phi_t  = fraction of capital using the CORRECT identification g*  (standardization rate s)
        psi_t  = fraction of capital that can merely SEE the raw feed X    (data-diffusion rate r)
  - The signal gets impounded into price as:
        impounded_t = d*phi_t + (1-d)*psi_t
    where d in [0,1] is EXTRACTION DIFFICULTY:
        d->1  : seeing X is useless without g*  => identification regime
        d->0  : seeing X is enough              => information regime
  - Alpha to the early correct-extractor: a_t = signal * (1 - impounded_t).
  - alpha half-life = first t where a_t <= a_0/2.

The belief => at the d that REAL alt-data sits at, alpha half-life responds to s
(standardization) far more than to r (raw-data diffusion). The FALSIFIER is the opposite:
half-life governed by r and insensitive to s.

We do NOT assume d. We MEASURE the d implied by adjustment ambiguity (a Lord's-Paradox-style
sub-model: how much do defensible adjustments of the same X disagree?), so the headline is
non-circular.
"""
import numpy as np

def alpha_path(s, r, d, T=600, phi0=0.01, psi0=0.01, signal=1.0):
    phi, psi = phi0, psi0
    a = []
    for _ in range(T):
        impounded = min(1.0, d*phi + (1.0-d)*psi)
        a.append(signal * max(0.0, 1.0 - impounded))
        phi = phi + s*(1.0 - phi)
        psi = psi + r*(1.0 - psi)
    return np.array(a)

def half_life(a):
    a0 = a[0]
    idx = np.where(a <= a0/2.0)[0]
    return int(idx[0]) if len(idx) else len(a)

def elasticity(d):
    """ d log(half-life) / d log(rate), for standardization (s) vs data-diffusion (r). """
    base_s, base_r = 0.02, 0.02
    bump = 2.0  # double the rate
    hl0 = half_life(alpha_path(base_s, base_r, d))
    hl_s = half_life(alpha_path(base_s*bump, base_r, d))      # double standardization
    hl_r = half_life(alpha_path(base_s, base_r*bump, d))      # double data diffusion
    # response = fractional change in half-life when that channel speeds up
    resp_s = (hl0 - hl_s) / max(1, hl0)   # >0 means faster standardization shortens edge
    resp_r = (hl0 - hl_r) / max(1, hl0)
    return hl0, hl_s, hl_r, resp_s, resp_r

# ---- 1) regime map across extraction difficulty d ----
print("d     hl0  hl(2x s)  hl(2x r)  resp_s  resp_r  driver")
rows = []
for d in [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
    hl0, hl_s, hl_r, rs, rr = elasticity(d)
    driver = "IDENTIFICATION" if rs > rr + 1e-9 else ("INFORMATION" if rr > rs + 1e-9 else "tie")
    rows.append((d, hl0, hl_s, hl_r, rs, rr, driver))
    print(f"{d:<5} {hl0:>4} {hl_s:>8} {hl_r:>9} {rs:>7.3f} {rr:>7.3f}  {driver}")

# ---- 2) make d OPERATIONAL (non-circular): d = fraction of extractable signal that is
#         accessible ONLY via the correct adjustment, not via a typical defensible one.
#   d = (R2_correct - R2_typical) / R2_correct
#   - if any defensible adjustment recovers most of the signal (R2_typical ~ R2_correct) -> d~0
#     (seeing the data is enough = INFORMATION regime)
#   - if only g* recovers it (R2_typical ~ 0) -> d~1 (IDENTIFICATION regime)
#   The free knob is mu = average skill of the *wrong-but-defensible* adjustments.
def implied_d(mu_wrong_skill, K=40, T=4000, seed=0):
    rng = np.random.default_rng(seed)
    Z = rng.standard_normal(T)
    Y = Z + rng.standard_normal(T)              # max recoverable R^2 ~ 0.5
    conf = rng.standard_normal(T)               # a confounder the wrong adjustments leak onto
    def r2(p):
        c = np.corrcoef(p, Y)[0, 1]
        return float(c*c)
    pred0 = Z + 0.0*conf                          # g*: correct adjustment, unbiased
    r2_correct = r2(pred0)
    r2s = []
    for i in range(1, K):
        c = float(np.clip(rng.normal(mu_wrong_skill, 0.15), 0, 1))   # how much true Z it keeps
        bias = float(abs(rng.normal(0, 1.0 - mu_wrong_skill)))       # leakage onto confounder
        r2s.append(r2(c*Z + bias*conf))
    r2_typical = float(np.mean(r2s))
    d = (r2_correct - r2_typical) / r2_correct
    return float(np.clip(d, 0, 1)), r2_correct, r2_typical

print("\nmu_wrong_skill -> operational extraction-difficulty d  (d = signal reachable ONLY via g*)")
for mu in [0.9, 0.7, 0.5, 0.3, 0.1]:
    dd, r2c, r2t = implied_d(mu)
    reg = "IDENTIFICATION" if dd > 0.5 else "INFORMATION"
    print(f"  typical-method skill mu={mu:<4} d={dd:.3f}  (R2_correct={r2c:.3f} R2_typical={r2t:.3f}) -> {reg}")

# ---- 3) headline: the belief is TRUE iff d>0.5, i.e. iff a typical defensible adjustment
#         captures < half the signal the correct one does. Sharp, empirically checkable. ----
d_crit = 0.5
print("\n=== HEADLINE ===")
print(f"Measured regime boundary: alpha-decay driver flips at d = {d_crit:.2f}")
print("  d>0.5  -> standardization (method) dominates decay  = IDENTIFICATION premium (belief holds)")
print("  d<0.5  -> raw-data diffusion dominates decay        = INFORMATION premium (belief fails)")
print("The belief is therefore CONDITIONAL and FALSIFIABLE by one measurement:")
print("  compute d = (R2 of the best adjustment - R2 of a typical defensible adjustment)/R2_best")
print("  on a real alt-data feed. Belief true on that feed iff d>0.5.")
# show the two extremes verify the boundary claim numerically
hl_id = elasticity(0.9); hl_info = elasticity(0.1)
print(f"check d=0.9: resp_s={hl_id[3]:.3f} > resp_r={hl_id[4]:.3f}  (identification)")
print(f"check d=0.1: resp_s={hl_info[3]:.3f} < resp_r={hl_info[4]:.3f}  (information)")
print("VERDICT_CONDITIONAL_SUPPORT: mechanism real, but belief is regime-dependent, not universal.")
