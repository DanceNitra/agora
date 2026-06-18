"""
Challenge belief (inbox 562d5d): "an A/B test beats a quasi-experiment by a BIAS threshold, INVARIANT to
effect size" (Lab 9965a4). The belief is algebraically correct for ADDITIVE bias: error = (estimate - tau),
and with quasi_est = tau + b the tau cancels, so the winner can't depend on tau. The challenge attacks the
hidden assumption: is the bias really additive (effect-independent)?

Disconfirming case: MULTIPLICATIVE / PROPORTIONAL bias, quasi_est = tau*(1+s). This arises whenever the
confounding scales with the effect - percentage/ratio outcomes, or a confounder that mediates a FRACTION
of the treatment's effect, or effect-modifying selection. Then |quasi_est - tau| = s*tau GROWS with tau,
so the A/B-vs-quasi winner FLIPS with effect size - breaking the 'invariant to effect size' claim.

We reproduce the additive (invariant) result and show the multiplicative (effect-dependent) failure, then
state the refined condition.
"""
import numpy as np

def rmse(true_tau, est_samples):
    return float(np.sqrt(np.mean((est_samples - true_tau) ** 2)))

def compare(tau, bias_mode, b_or_s, sigma=2.0, n_rct=100, n_quasi=2000, sims=4000, seed=0):
    rng = np.random.default_rng(abs(seed + int(tau * 1000)) % (2**32))
    se_rct = sigma / np.sqrt(n_rct)        # randomized, unbiased
    se_q = sigma / np.sqrt(n_quasi)        # observational, 20x data -> lower variance
    ab = tau + se_rct * rng.standard_normal(sims)
    if bias_mode == "additive":
        bias = b_or_s                       # fixed offset, independent of tau
    else:                                   # multiplicative / proportional
        bias = b_or_s * tau                 # bias scales with the effect
    q = tau + bias + se_q * rng.standard_normal(sims)
    r_ab, r_q = rmse(tau, ab), rmse(tau, q)
    return r_ab, r_q, ("A/B" if r_ab < r_q else "quasi")

if __name__ == "__main__":
    taus = [0.1, 0.5, 1.0, 2.0, 4.0]
    print("A/B (unbiased, n=100) vs quasi (n=2000, biased). Winner vs true effect size tau.\n")

    print("ADDITIVE bias b=0.30 (the belief's regime):")
    win_add = []
    for tau in taus:
        ra, rq, w = compare(tau, "additive", 0.30)
        win_add.append(w)
        print(f"   tau={tau:<4} RMSE_AB={ra:.3f} RMSE_quasi={rq:.3f} -> {w}")
    add_invariant = len(set(win_add)) == 1

    print("\nMULTIPLICATIVE bias s=0.30 (bias = 0.30*tau; proportional confounding):")
    win_mult = []
    for tau in taus:
        ra, rq, w = compare(tau, "multiplicative", 0.30)
        win_mult.append(w)
        print(f"   tau={tau:<4} RMSE_AB={ra:.3f} RMSE_quasi={rq:.3f} -> {w}")
    mult_flips = len(set(win_mult)) > 1

    print("\n=== VERDICT ===")
    print(f"additive bias -> winner INVARIANT to effect size: {add_invariant} ({win_add})")
    print(f"multiplicative bias -> winner FLIPS with effect size: {mult_flips} ({win_mult})")
    if add_invariant and mult_flips:
        print("\nCHALLENGE PARTIALLY CONFIRMED -> belief SURVIVES but is REFINED:")
        print("The effect-size-invariance is REAL but conditional on the bias being ADDITIVE (effect-")
        print("independent) - which is the common omitted-confounder / selection-on-levels case, so the")
        print("belief holds there. It FAILS for MULTIPLICATIVE / proportional bias (quasi_est = tau*(1+s)):")
        print("then |bias| = s*tau grows with the effect, so small effects favour the high-data quasi while")
        print("large effects favour the A/B - the winner FLIPS with tau. Proportional bias arises with")
        print("percentage/ratio outcomes, a confounder that mediates a FRACTION of the effect, or effect-")
        print("modifying selection. Refined rule: 'run the A/B iff plausible bias exceeds SE_rct, and this")
        print("decision is effect-size-invariant ONLY when the bias is additive; under proportional bias the")
        print("threshold scales as SE_rct / s, so effect size re-enters the decision.'")
    else:
        print("\nNot the predicted additive/multiplicative split -- investigate.")
