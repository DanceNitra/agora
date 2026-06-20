"""
Insight 34c235: a corrected best-of-k procedure with SELECTION-AWARE false-discovery control.

Context: an overnight finding measured that naive best-of-100 selection inflates the false-discovery
rate to ~0.79, and -- the non-obvious part -- Benjamini-Hochberg BARELY helped (0.79 -> 0.77). Why?
Because best-of-k reports only the WINNER (the most significant of k candidate analyses), and the
winner's p-value under the null is NOT uniform: it is the minimum of k uniforms, i.e. Beta(1,k),
piled up near zero. BH assumes valid (super-uniform) null p-values, so feeding it the raw winners
leaves it nearly defenceless.

The fix is a selection-aware calibration: transform each reported winner p_min by the exact null CDF
of the best-of-k statistic, p_corr = 1-(1-p_min)^k (Sidak / max-null), THEN run BH. This restores
valid null p-values, so FDR returns to its nominal level -- at a measurable cost in power.

Relevance to the frontier (better thinking + AI engineering): best-of-n / self-consistency / reranking
is everywhere in LLM agents; "pick the best of n samples" is exactly best-of-k selection, and the same
winner's curse inflates how often the chosen answer is spuriously confident. The correction is cheap.

This is a MEASURE-only severe test: three procedures, one realized-FDR number each, plus power.
Honest: report whatever the numbers say.
"""
import math
try:
    import numpy as np
    _HAVE_NP = True
except Exception:
    _HAVE_NP = False

M = 2000          # number of independent studies/hypotheses
PI1 = 0.10        # fraction that are truly real
K = 10            # best-of-k candidate analyses per study (the forking paths)
MU = 3.2          # real-effect mean z (so a real study's best-of-k is reliably significant)
ALPHA = 0.05      # target FDR
TRIALS = 200      # averaging


def _norm_sf(z):
    # two-sided p for a standard normal |z|
    return math.erfc(abs(z) / math.sqrt(2.0))


def _bh_reject(pvals, alpha):
    """Benjamini-Hochberg: return a boolean mask of rejections."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    thresh = -1
    for rank, idx in enumerate(order, start=1):
        if pvals[idx] <= alpha * rank / m:
            thresh = rank
    rej = [False] * m
    for rank, idx in enumerate(order, start=1):
        if rank <= thresh:
            rej[idx] = True
    return rej


def one_trial(rng):
    is_real = [rng.random() < PI1 for _ in range(M)]
    pmin = [0.0] * M
    for i in range(M):
        mu = MU if is_real[i] else 0.0
        # k candidate analyses; analyst reports the most significant (min p)
        best = 1.0
        for _ in range(K):
            z = rng.gauss(mu, 1.0)
            p = _norm_sf(z)
            if p < best:
                best = p
        pmin[i] = best

    # transform p-values for the three procedures
    p_naive = pmin                                   # treat winner as a valid p (the mistake)
    p_corr = [1.0 - (1.0 - p) ** K for p in pmin]    # selection-aware (max-null / Sidak)

    def fdr_power(rej):
        disc = sum(rej)
        fd = sum(1 for i in range(M) if rej[i] and not is_real[i])
        td = sum(1 for i in range(M) if rej[i] and is_real[i])
        real = sum(is_real)
        return (fd / disc if disc else 0.0), (td / real if real else 0.0)

    # 1) NAIVE: threshold raw winner at alpha, no multiplicity control
    rej_naive = [p < ALPHA for p in p_naive]
    # 2) BH on the raw winners (the routinely-misapplied fix)
    rej_bh = _bh_reject(p_naive, ALPHA)
    # 3) SELECTION-AWARE: BH on the calibrated winners
    rej_sa = _bh_reject(p_corr, ALPHA)
    return fdr_power(rej_naive), fdr_power(rej_bh), fdr_power(rej_sa)


def main():
    import random
    rng = random.Random(20260620)
    acc = {"naive": [0.0, 0.0], "bh": [0.0, 0.0], "sa": [0.0, 0.0]}
    for _ in range(TRIALS):
        (fn, pn), (fb, pb), (fs, ps) = one_trial(rng)
        acc["naive"][0] += fn; acc["naive"][1] += pn
        acc["bh"][0] += fb;    acc["bh"][1] += pb
        acc["sa"][0] += fs;    acc["sa"][1] += ps
    for k in acc:
        acc[k][0] /= TRIALS; acc[k][1] /= TRIALS

    print(f"=== selection-aware best-of-k FDR (M={M}, k={K}, pi_real={PI1}, target FDR={ALPHA}) ===", flush=True)
    print(f"  {'procedure':>26} {'realized FDR':>13} {'power':>8}")
    print(f"  {'naive threshold @ alpha':>26} {acc['naive'][0]:>12.0%} {acc['naive'][1]:>8.0%}")
    print(f"  {'BH on raw winners':>26} {acc['bh'][0]:>12.0%} {acc['bh'][1]:>8.0%}")
    print(f"  {'selection-aware (max-null)+BH':>26} {acc['sa'][0]:>12.0%} {acc['sa'][1]:>8.0%}")
    controlled = acc["sa"][0] <= ALPHA * 1.5
    bh_fails = acc["bh"][0] > ALPHA * 2
    print("=== VERDICT ===")
    print(f"  BH on raw best-of-k winners {'FAILS' if bh_fails else 'holds'} (FDR {acc['bh'][0]:.0%}); "
          f"max-null calibration {'RESTORES control' if controlled else 'does not control'} "
          f"(FDR {acc['sa'][0]:.0%}) at power {acc['sa'][1]:.0%}.")


if __name__ == "__main__":
    main()
