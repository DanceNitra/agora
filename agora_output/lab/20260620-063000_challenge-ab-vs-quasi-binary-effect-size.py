"""
CHALLENGE (severe test): belief "an A/B test beats a quasi-experiment by a BIAS threshold, NOT effect
size; the crossover is invariant to the true effect tau" (insight-ab-vs-quasi-bias-not-effect-size,
Lab 9965a4).

The belief's mechanism: for an unbiased RCT error ~N(0,var_rct) and a biased quasi error ~N(bias,
var_quasi), tau cancels in (estimate - tau), so RMSE can't depend on tau. TRUE -- but only when var_rct
is CONSTANT in tau. That holds for continuous, constant-variance outcomes. The canonical A/B test is on
a CONVERSION RATE (binary outcome), where SE_rct = sqrt(p(1-p)/n) depends on the rates, hence on tau.

Challenge: in the binary/rate setting, does the A/B-vs-quasi crossover MOVE with effect size -- can the
winner FLIP at a FIXED confounding level as tau changes? If yes, the "invariant to effect size" claim is
an artifact of the continuous-constant-variance setup and the belief must be refined. Falsifier of the
challenge: if even for binary outcomes the winner is invariant to tau, the original belief survives.
"""
import numpy as np

RNG = np.random.default_rng(0)
N_RCT = 100      # per arm: randomized, expensive -> small n
N_QUASI = 2000   # per arm: observational, cheap -> large n, but confounded (bias b on the rate diff)


def se_rct_binary(p_c, tau, n=N_RCT):
    p_t = p_c + tau
    return np.sqrt(p_t * (1 - p_t) / n + p_c * (1 - p_c) / n)


def rmse_quasi_binary(p_c, tau, b, n=N_QUASI):
    p_t = p_c + tau
    var = p_t * (1 - p_t) / n + p_c * (1 - p_c) / n
    return np.sqrt(b ** 2 + var)               # bias b dominates; large-n variance is tiny


def winner(p_c, tau, b):
    r = se_rct_binary(p_c, tau)                 # RCT unbiased -> RMSE = SE
    q = rmse_quasi_binary(p_c, tau, b)
    return ("A/B" if r < q - 1e-6 else "quasi" if q < r - 1e-6 else "tie"), r, q


# ---- 1) BINARY outcomes: does the winner move with effect size at FIXED confounding? ----
print("=== BINARY (conversion-rate) A/B vs quasi: winner across tau x confounding (p_c=0.10) ===")
P_C = 0.10
TAUS = [0.02, 0.05, 0.10, 0.20]
BIASES = [0.00, 0.03, 0.05, 0.08]
print(f"  {'bias b':>7} | " + " | ".join(f"tau={t:<4}" for t in TAUS))
for b in BIASES:
    cells = []
    for t in TAUS:
        w, r, q = winner(P_C, t, b)
        cells.append(f"{w:<5}")
    print(f"  {b:>7.2f} | " + " | ".join(cells))

# the decisive demonstration: a FIXED confounding level where the winner FLIPS with effect size
print("\n=== DECISIVE: fixed confounding bias b=0.05, p_c=0.10 -- winner vs effect size ===")
flips = set()
for t in TAUS:
    w, r, q = winner(P_C, t, 0.05)
    print(f"  tau={t:<5} SE_rct={r:.4f}  RMSE_quasi={q:.4f}  -> winner: {w}")
    flips.add(w)

# ---- 2) CONTROL: continuous constant-variance outcome -- belief should HOLD (winner invariant in tau) ----
print("\n=== CONTROL: continuous, constant-variance outcome (the belief's original setting) ===")
SIGMA = 1.0
se_rct_cont = SIGMA / np.sqrt(N_RCT)                 # flat in tau by construction
def winner_cont(tau, b):
    q = np.sqrt(b ** 2 + (SIGMA ** 2) / N_QUASI)
    return "A/B" if se_rct_cont < q - 1e-9 else "quasi"
print(f"  SE_rct (flat) = {se_rct_cont:.4f}")
print(f"  {'bias b':>7} | " + " | ".join(f"tau={t:<4}" for t in TAUS))
for b in BIASES:
    print(f"  {b:>7.2f} | " + " | ".join(f"{winner_cont(t,b):<5}" for t in TAUS))

# ---- verdict ----
binary_moves = len(flips) > 1
print()
if binary_moves:
    w_small, _, _ = winner(P_C, TAUS[0], 0.05)
    w_big, _, _ = winner(P_C, TAUS[-1], 0.05)
    print("VERDICT: belief REFINED (challenge SUCCEEDS for the practical case). For BINARY/conversion-rate "
          f"outcomes -- the canonical A/B setting -- the winner DOES move with effect size: at a fixed "
          f"confounding bias b=0.05 the winner flips from {w_small} (tau={TAUS[0]}) to {w_big} "
          f"(tau={TAUS[-1]}), because SE_rct=sqrt(p(1-p)/n) GROWS as the treated rate rises with tau. "
          "The 'invariant to effect size' claim is an artifact of the continuous, constant-variance "
          "outcome (CONTROL above: winner is indeed invariant in tau there). Refined rule: the crossover "
          "is bias-vs-SE_rct, and SE_rct is itself effect-size-dependent whenever outcome variance depends "
          "on the mean (binary, Poisson, any GLM) -- so for rate metrics effect size re-enters the A/B-vs-"
          "quasi decision through the RCT's standard error.")
else:
    print("VERDICT: belief SURVIVES -- even for binary outcomes the winner is invariant to effect size.")
