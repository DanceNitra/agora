"""
Frontier hypothesis (severe-test): does increasing-returns reinforcement become QUALITY-BLIND?

Theme: Path Dependence (Economics x Complexity x AI feedback loops).
Bridge: Arthur (1989) increasing-returns lock-in; nonlinear Polya urn; AI recommender / self-training
"rich-get-richer" loops.

Setup: two options A (quality q_A=1+delta) and B (q_B=1). A generalized Polya urn: at each step pick
option i with probability proportional to (n_i)^alpha * q_i, then add a unit to i. alpha is the
INCREASING-RETURNS strength:
  alpha<1 sublinear (diminishing returns), alpha=1 linear (classic Polya), alpha>1 superlinear
  (winner-take-all / lock-in).

HYPOTHESIS: P(the higher-quality option A ends with the majority) DECREASES as alpha rises — i.e.
stronger winner-take-all reinforcement becomes quality-blind, because superlinear reinforcement
amplifies EARLY CHANCE fluctuations faster than it amplifies the per-pick quality signal.

FALSIFIER: if P(A wins) is flat or INCREASES with alpha (more reinforcement always helps quality),
the hypothesis is false.
"""
import numpy as np


def simulate(alpha, delta, T=1500, trials=4000, seed=0):
    """Vectorized over trials. Returns P(A wins majority), mean & sd of final A-share."""
    rng = np.random.default_rng(seed)
    qA, qB = 1.0 + delta, 1.0
    nA = np.ones(trials); nB = np.ones(trials)
    for _ in range(T):
        wA = np.power(nA, alpha) * qA
        wB = np.power(nB, alpha) * qB
        pA = wA / (wA + wB)
        pick = rng.random(trials) < pA
        nA = nA + pick
        nB = nB + (~pick)
    share = nA / (nA + nB)
    return float((nA > nB).mean()), float(share.mean()), float(share.std())


def first_mover_vs_quality(alpha, delta, T=1500, trials=4000, lead_step=40, seed=1):
    """Diagnostic: how much does the FINAL winner depend on the early (step lead_step) leader
    vs on quality? Returns P(final winner == early leader)."""
    rng = np.random.default_rng(seed)
    qA, qB = 1.0 + delta, 1.0
    nA = np.ones(trials); nB = np.ones(trials)
    early_leadA = None
    for t in range(T):
        wA = np.power(nA, alpha) * qA; wB = np.power(nB, alpha) * qB
        pA = wA / (wA + wB)
        pick = rng.random(trials) < pA
        nA = nA + pick; nB = nB + (~pick)
        if t == lead_step:
            early_leadA = nA > nB
    finalA = nA > nB
    return float((finalA == early_leadA).mean())


delta = 0.2   # A is 20% higher quality
print(f"Quality edge delta={delta} (A is the better option). Sweeping increasing-returns alpha.\n")
print("alpha   P(better A wins)   mean A-share   sd     P(final==early leader)")
alphas = [0.0, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
res = {}
for a in alphas:
    pw, ms, sd = simulate(a, delta)
    pl = first_mover_vs_quality(a, delta)
    res[a] = pw
    print(f"{a:<6} {pw:>10.3f}        {ms:>8.3f}   {sd:>5.3f}   {pl:>8.3f}")

# self-disagreement check: the strongest case AGAINST is "a bigger quality gap rescues quality even
# under strong winner-take-all". Measure P(better wins) at alpha=2 across quality gaps delta.
print("\nSelf-disagreement test — does a larger quality gap delta rescue quality at alpha=2 (winner-take-all)?")
print("delta   P(better wins, alpha=2)")
rescue = {}
for dd in [0.05, 0.2, 0.5, 1.0, 2.0]:
    pw, _, _ = simulate(2.0, dd)
    rescue[dd] = pw
    print(f"{dd:<6} {pw:>10.3f}")

# verdict
pw0 = res[0.0]; pw_lin = res[1.0]; pw_hi = res[2.0]
monotone_decreasing = all(res[alphas[i]] >= res[alphas[i+1]] - 0.02 for i in range(len(alphas)-1))
big_drop = (pw0 - pw_hi) > 0.15
print("\n=== VERDICT ===")
print(f"P(better wins): alpha=0 -> {pw0:.3f}, alpha=1 -> {pw_lin:.3f}, alpha=2 -> {pw_hi:.3f}")
if monotone_decreasing and big_drop:
    print("SUPPORTED: stronger increasing-returns reinforcement is quality-blind — P(better wins) falls "
          f"by {pw0-pw_hi:.2f} from pure-quality (alpha=0) to strong winner-take-all (alpha=2).")
elif big_drop:
    print("PARTIAL: P(better wins) drops with alpha overall but not strictly monotone.")
else:
    print("REFUTED: P(better wins) does not fall with alpha — reinforcement is not quality-blind here.")
print("Interpretation: superlinear reinforcement (alpha>1) locks in whoever leads early; the early")
print("leader is increasingly chance-driven, so the quality signal is washed out — the formal core of")
print("path-dependent lock-in to inferior options in AI recommender / self-training feedback loops.")
