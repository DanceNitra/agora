"""Audit of the TAT proteomics anomaly metrics (Marat Sultanov, 2026-08-03).

The claim under test is NOT biological. It is algebraic: the notebook computes three
"independent" anomaly scores and reports that they converge on the same treatments.

Two of the three scores are checked here on synthetic data, because their behaviour is a
property of the formula, not of the proteome. A defect that reproduces on any input is a
defect in the metric.

  M1  agreement = (1 - coarse_norm) * (1 - fine_norm) * err_norm,  "lower = more anomalous"
      -> the error term enters with the OPPOSITE sign to the other two. Does the ranking
         then put well-predicted samples at the anomalous end?

  M2  defence = distance, in sorted-rank space, to the nearest point where the sorted
      target-protein concentration jumps by more than mean+2sd,  "higher = more anomalous"
      -> FIRST HYPOTHESIS, REFUTED BY ITS OWN CONTROL: that it would peak on the most
         typical samples. It does not; it does flag the extremes. That claim is withdrawn
         and is NOT cited. What the control exposed instead is measured below: how many
         anchors the mean+2sd rule finds is governed by the tail shape of the distribution,
         not by the data's structure, and with few anchors the score collapses into a
         deterministic function of one protein's rank.

Each check carries a control that must fail if the harness is not actually reproducing the
notebook's formula.
"""

import numpy as np
from scipy.stats import spearmanr

RNG = np.random.default_rng(20260803)
N = 4454  # the notebook's test-set size


def normalize(x):
    """Verbatim from the notebook (cell 2)."""
    return (x - x.min()) / (x.max() - x.min() + 1e-8)


def agreement(coarse, fine, err):
    """Verbatim from the notebook (cell 2)."""
    return (1 - normalize(coarse)) * (1 - normalize(fine)) * normalize(err)


def defence(target_values):
    """Verbatim from the notebook (cell 6)."""
    sorted_idx = np.argsort(target_values)
    sorted_values = target_values[sorted_idx]
    grad = np.diff(sorted_values)
    threshold = np.mean(np.abs(grad)) + 2 * np.std(np.abs(grad))
    anchors_rel = np.where(np.abs(grad) > threshold)[0]
    score = np.zeros(len(target_values))
    for i in range(len(target_values)):
        if len(anchors_rel) > 0:
            pos = np.where(sorted_idx == i)[0][0]
            score[i] = np.min(np.abs(anchors_rel - pos))
    return score, anchors_rel


def m1_sign_coherence():
    """Does 'low agreement' select high-error or low-error samples?"""
    coarse = RNG.lognormal(0, 1, N)          # a protein concentration: right-skewed
    fine = RNG.gamma(4, 0.5, N)              # mean kNN distance: positive, unimodal
    err = np.abs(RNG.standard_t(3, N))       # prediction error: heavy-tailed, as MSE-trained

    a = agreement(coarse, fine, err)
    anomalous = np.argsort(a)[: N // 10]     # the 10% "most anomalous" by the notebook's rule
    normal = np.argsort(a)[-N // 10 :]

    rho = spearmanr(a, err).statistic
    print("M1  agreement vs prediction error")
    print(f"      spearman(agreement, err)        = {rho:+.3f}")
    print(f"      mean err | 10% MOST anomalous   = {err[anomalous].mean():.4f}")
    print(f"      mean err | 10% MOST normal      = {err[normal].mean():.4f}")
    print(f"      share of err_norm below 0.05    = {(normalize(err) < 0.05).mean():.3f}")
    inverted = err[anomalous].mean() < err[normal].mean()
    print(f"      VERDICT: error sign is {'INVERTED' if inverted else 'coherent'}")

    # Control: flip the error term to enter with the same sign as the others. If the harness
    # is faithfully reproducing the formula, this must restore coherence.
    a2 = (1 - normalize(coarse)) * (1 - normalize(fine)) * (1 - normalize(err))
    an2 = np.argsort(a2)[: N // 10]
    nm2 = np.argsort(a2)[-N // 10 :]
    ctrl_ok = err[an2].mean() > err[nm2].mean()
    print(f"      CONTROL (error term flipped)    = {'coherent, as expected' if ctrl_ok else 'STILL INVERTED -- harness is wrong'}")
    return inverted and ctrl_ok


def m2_anchor_stability():
    """Is the anchor rule a property of the data's structure, or of its tail shape?

    The direction of the score is fine -- it does flag extremes. The question is whether the
    RESOLUTION of the detector is set by anything meaningful. The rule keeps gaps above
    mean+2sd of the gaps; a heavy tail inflates sd, so the same rule on the same sample size
    can find a handful of anchors or hundreds purely from the shape.
    """
    shapes = {
        "lognormal(0,1)": lambda r: r.lognormal(0, 1, N),
        "lognormal(0,2)": lambda r: r.lognormal(0, 2, N),
        "normal(0,1)": lambda r: r.standard_normal(N),
        "uniform(0,1)": lambda r: r.uniform(0, 1, N),
        "exponential(1)": lambda r: r.exponential(1, N),
    }
    print("\nM2  how many anchors does the mean+2sd rule find? (n = %d in every row)" % N)
    counts = {}
    for name, gen in shapes.items():
        c = [len(defence(gen(np.random.default_rng(s)))[1]) for s in (1, 2, 3)]
        counts[name] = c
        print(f"      {name:<16} anchors = {c}  ({100*np.mean(c)/(N-1):.2f}% of gaps)")
    lo, hi = min(min(v) for v in counts.values()), max(max(v) for v in counts.values())
    print(f"      spread across shapes            = {lo} to {hi} anchors, a {hi/max(lo,1):.0f}x swing")

    # With few anchors the score stops being a detector: it becomes a piecewise-linear
    # function of the sample's RANK in one protein. Measure that directly.
    target = RNG.lognormal(0, 1, N)
    score, anchors = defence(target)
    rank = np.argsort(np.argsort(target))
    print(f"      with {len(anchors)} anchors, spearman(|defence|, rank-derived) is exact by")
    print("      construction: defence(i) = min_a |rank(i) - a|, so the per-treatment mean is")
    print("      a summary of that treatment's ranks in ONE protein, not a structural signal.")

    # Control: the score must be recoverable from rank alone. If it is not, the reading above
    # is wrong and must not be cited.
    recovered = np.array([min(abs(anchors - r)) if len(anchors) else 0 for r in rank])
    exact = np.array_equal(recovered, score)
    print(f"      CONTROL (rebuild score from rank only) = {'EXACT match' if exact else 'MISMATCH -- do not cite'}")
    return exact and (hi / max(lo, 1) > 10)


def m3_shared_input():
    """How much of the 'three-metric convergence' is one protein measured three ways?"""
    print("\nM3  what each score is a function of")
    print("      coarse   = target protein concentration            (protein #1)")
    print("      err      = error of a net PREDICTING that protein  (protein #1)")
    print("      defence  = rank distance in that protein's sorted  (protein #1)")
    print("      fine     = mean kNN distance over all 500          (all 500)")
    print("      recon    = autoencoder MSE over all 500            (all 500)")
    print("      -> 3 of the 5 inputs, and 2 of the 3 reported scores, are functions of")
    print("         top_proteins[0] alone. Agreement between them is expected by")
    print("         construction and is not independent corroboration.")


if __name__ == "__main__":
    print(f"n = {N} synthetic samples, seed 20260803\n")
    a = m1_sign_coherence()
    b = m2_anchor_stability()
    m3_shared_input()
    print(f"\nMEASURED: agreement_sign_inverted={a}  defence_is_rank_of_one_protein={b}")
    print("VERDICT: " + ("agreement inverts its own error term; defence is one protein's rank"
                         if a and b else "at least one check did not reproduce -- do not cite"))
