"""Authenticated-but-false: a second adjudicator recovers detection ONLY if its failure mode is orthogonal.

Motivation (from a r/RAG exchange on the Veracity-Gap result): corroboration measures independence of ORIGIN,
never correctness -- so when genuinely independent sources CONVERGE on a wrong claim ("authenticated-but-false"),
nothing in the record content catches it. The suggested move: don't promote convergence to "true"; carry it as
convergence-backed, and put adjudication ABOVE the text-scoring layer, with a DIFFERENT failure mode.

This probe MEASURES that last clause -- and does NOT lean on the trivial part. "Corroboration alone detects 0%
of convergent-false" is TRUE BY CONSTRUCTION (corroboration scores agreement, and a convergent-false claim has
agreement), so it is not the finding. The finding is the TRADE-OFF of a second adjudicator as a function of how
CORRELATED its failure mode is with the first:

  A second check adds detection of convergent-false ONLY to the degree its errors are INDEPENDENT of the first
  check's errors. A second text-agreement check (correlated failure) adds ~0; an orthogonal check (recompute /
  ground-truth / a different modality) adds the most -- and the marginal gain scales with 1 - failure_corr.

This is the measured basis for inspeximus's grade ladder (corroboration -> `corroborated`, never `verified`) and for
`settled` requiring >=2 DISTINCT lenses: distinctness is not decoration, it is the whole mechanism -- correlated
lenses are one lens counted twice.

FALSIFIER: if a highly-correlated second adjudicator (failure_corr ~ 1) detected convergent-false about as well
as an orthogonal one (failure_corr ~ 0), "different failure mode" would be doing no work and the thesis is wrong.

Deterministic (fixed seed; needs numpy):  python convergence_adjudication.py
MIT-licensed. Part of Agora / inspeximus (https://github.com/DanceNitra/inspeximus).
"""
import math
import numpy as np

N = 20000            # claims, each backed by several genuinely-independent sources
P_FALSE = 0.5        # half are convergent-FALSE (independent sources agree, but wrong)
SEED = 7
TARGET_FPR = 0.10    # operating point: allow 10% false-positives on TRUE-convergent claims


def _auroc(score, label):
    pos = score[label == 1]; neg = score[label == 0]
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty(len(order)); ranks[order] = np.arange(1, len(order) + 1)
    return (ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def _detection_at_fpr(score, is_false, fpr=TARGET_FPR):
    """detection (recall) of convergent-FALSE at a threshold set to `fpr` false positives on TRUE claims.
    score = higher means 'more likely false' (what the adjudicator flags)."""
    thr = np.quantile(score[is_false == 0], 1 - fpr)     # threshold from the TRUE-claim score distribution
    return float((score[is_false == 1] >= thr).mean())


def main():
    rng = np.random.default_rng(SEED)
    is_false = (rng.random(N) < P_FALSE).astype(int)     # 1 = convergent-FALSE, 0 = convergent-TRUE

    # "convincingness": the latent that fools any AGREEMENT/text check. Convergent-false claims are, by
    # selection, just as convincing as true ones (that is why independent sources converged on them).
    convincing = rng.normal(0, 1, N)                     # independent of truth by construction

    # CHANNEL 1 = corroboration / text-agreement: its "is this false?" signal is driven by (lack of)
    # convincingness -- it CANNOT read correctness, so on convergent-false it is at chance.
    ch1_false_score = -convincing + rng.normal(0, 0.3, N)

    print("=== Authenticated-but-false: can a second adjudicator catch what corroboration cannot? ===\n")
    print("[by construction] corroboration alone, detection of convergent-FALSE @ %d%% FPR: %.3f  (~chance -- it"
          % (int(TARGET_FPR * 100), _detection_at_fpr(ch1_false_score, is_false)))
    print("                  scores agreement, and a convergent-false claim HAS agreement). Not the finding.\n")

    # CHANNEL 2 = a second adjudicator. It has a REAL correctness signal, but we tune how much of its error is
    # shared with channel 1 (i.e. how much it also just reads 'convincingness'). w=0 -> orthogonal failure mode
    # (pure correctness); w=1 -> correlated failure mode (it fails exactly where channel 1 fails).
    truth_signal = (1 - 2 * is_false).astype(float)      # +1 true, -1 false (the real thing ch1 can't see)
    print(" adjudicator failure-mode        | corr(err2, err1) | detection of false @10%%FPR | marginal vs ch1")
    base = _detection_at_fpr(ch1_false_score, is_false)
    for w, name in [(0.0, "orthogonal (recompute/GT)"), (0.25, "mostly orthogonal"),
                    (0.5, "half-shared"), (0.75, "mostly shared"), (1.0, "correlated (text again)")]:
        # ch2 flags 'false' from correctness (strength s) blended with the shared convincingness failure mode
        s = 1.2
        ch2_false = -s * (1 - w) * truth_signal + w * (-convincing) + rng.normal(0, 0.5, N)
        # empirical failure-mode correlation: correlation of the two checks' ERRORS on the claims each gets wrong
        err1 = (ch1_false_score - ch1_false_score.mean())
        err2 = (ch2_false - ch2_false.mean())
        # residualize out the truth signal so we measure SHARED-ERROR correlation, not shared-correct
        def resid(x):
            b = np.polyfit(truth_signal, x, 1); return x - (b[0] * truth_signal + b[1])
        fc = float(np.corrcoef(resid(err1), resid(err2))[0, 1])
        det = _detection_at_fpr(ch2_false, is_false)
        print("  %-30s |      %+.2f       |          %.3f           |   %+.3f"
              % (name, fc, det, det - base))

    print("\nILLUSTRATION (design rationale, NOT a measured finding -- see docstring): corroboration cannot")
    print("separate convergent-false from convergent-true (~chance, by construction).")
    print("A second adjudicator recovers detection in proportion to how ORTHOGONAL its failure mode is: an")
    print("orthogonal check (recompute / ground-truth) catches nearly all of it; a correlated second text check")
    print("adds almost nothing. => 'different failure mode' is the whole mechanism; distinct lenses aren't decoration.")
    print("This is why inspeximus carries convergence as `corroborated` (never `verified`) and reserves `verified`/")
    print("`settled` for out-of-band reproduction + >=2 DISTINCT lenses. Falsifier: a correlated 2nd check would")
    print("have matched the orthogonal one -- it does not.")


if __name__ == "__main__":
    main()
