"""
Severe test for the AI-engineering claim:

  "Adding a reranker (cross-encoder) on top of first-stage retrieval
   reliably improves end-to-end RAG answer accuracy, or at worst never
   hurts it ('drop in a reranker for a free boost')."

Smallest runnable model (numpy-only, deterministic).

Mechanism modeled
-----------------
Per query there is 1 gold doc and a 30-doc distractor pool. Of the
distractors, 3 are HARD NEGATIVES (lexically similar, moderate true
relevance) and 27 are soft (irrelevant). Two retrieval branches:

  NO-RERANK : first-stage scores = true_rel + N(0,1.2); take top-5.
  RERANK    : rescore with a cleaner scorer true_rel + N(0,0.6),
              BUT add an inflation term `infl` to the 3 hard negatives
              only (a cross-encoder fooled by lexical overlap).

Generator correctness depends on the gold doc's RANK inside the top-5
window (position bias). If gold is not retrieved -> parametric-knowledge
floor 0.15. Bernoulli draw, metric = mean correctness.

Anti-rig controls
-----------------
* infl=0.0 is the CONTROL / negative case: with no hard-negative
  inflation the cleaner reranker MUST help (delta > 0). If the control
  failed to show a gain, the harness would be broken and we'd report
  NOT_COMPUTABLE.
* The DGP does not bake in the conclusion: the only thing that turns the
  reranker harmful is the `infl` knob, swept openly; the verdict is read
  off the printed delta curve, not asserted.
"""

import numpy as np

RNG_SEED = 0
N = 200_000
N_DISTRACT = 30
N_HARD = 3
TOPK = 5
POS_BIAS = np.array([0.85, 0.72, 0.60, 0.50, 0.42])  # P(correct) by gold rank 0..4
FLOOR = 0.15  # P(correct) when gold not in top-5
INFL_SWEEP = [0.0, 1.4, 2.2, 3.0]


def simulate(infl, seed):
    """Return mean end-to-end correctness for both branches at given infl."""
    rng = np.random.default_rng(seed)

    # True relevance of the gold doc and all distractors.
    gold_rel = rng.normal(3.0, 0.7, size=N)                       # (N,)
    hard_rel = rng.normal(1.5, 0.5, size=(N, N_HARD))             # (N,3)
    soft_rel = rng.normal(0.0, 1.0, size=(N, N_DISTRACT - N_HARD))  # (N,27)

    # Assemble the candidate set: column 0 = gold, 1..3 = hard, rest soft.
    true_rel = np.concatenate(
        [gold_rel[:, None], hard_rel, soft_rel], axis=1
    )  # (N, 31), gold at index 0

    n_docs = true_rel.shape[1]
    gold_idx = 0
    hard_mask = np.zeros(n_docs, dtype=bool)
    hard_mask[1:1 + N_HARD] = True

    # ---- NO-RERANK branch: noisy first-stage scorer ----
    fs_score = true_rel + rng.normal(0.0, 1.2, size=true_rel.shape)
    acc_no = _branch_accuracy(fs_score, gold_idx, rng)

    # ---- RERANK branch: cleaner scorer, but inflates hard negatives ----
    rr_score = true_rel + rng.normal(0.0, 0.6, size=true_rel.shape)
    rr_score[:, hard_mask] += infl
    acc_rr = _branch_accuracy(rr_score, gold_idx, rng)

    return acc_no, acc_rr


def _branch_accuracy(scores, gold_idx, rng):
    """Top-5 by score; correctness via position bias on gold's rank."""
    # Rank of gold = number of docs strictly out-scoring it.
    gold_score = scores[:, gold_idx]
    gold_rank = np.sum(scores > gold_score[:, None], axis=1)  # 0 = top

    in_window = gold_rank < TOPK
    p_correct = np.full(scores.shape[0], FLOOR)
    p_correct[in_window] = POS_BIAS[gold_rank[in_window]]

    draws = rng.random(scores.shape[0])
    correct = draws < p_correct
    return correct.mean()


def main():
    print("=" * 64)
    print("Reranker 'free boost' claim - severe test (numpy, seeded)")
    print("n_queries = %d  per infl  | seed = %d" % (N, RNG_SEED))
    print("=" * 64)

    deltas = {}
    for i, infl in enumerate(INFL_SWEEP):
        acc_no, acc_rr = simulate(infl, RNG_SEED + i)
        delta = acc_rr - acc_no
        deltas[infl] = delta
        print("infl=%4.1f | no-rerank=%.4f  rerank=%.4f  delta=%+.4f"
              % (infl, acc_no, acc_rr, delta))

    # Crossover infl* where delta crosses 0 (linear interp between samples).
    xs = INFL_SWEEP
    ys = [deltas[x] for x in xs]
    cross = None
    for a, b in zip(range(len(xs) - 1), range(1, len(xs))):
        if ys[a] >= 0 >= ys[b] or ys[a] <= 0 <= ys[b]:
            if ys[a] != ys[b]:
                t = ys[a] / (ys[a] - ys[b])
                cross = xs[a] + t * (xs[b] - xs[a])
                break

    print("-" * 64)
    control = deltas[0.0]
    worst = min(deltas.values())
    print("CONTROL (infl=0.0) delta = %+.4f  (must be > 0: cleaner scorer helps)" % control)
    print("WORST delta over sweep    = %+.4f" % worst)
    if cross is not None:
        print("Crossover infl* (delta=0) ~ %.3f" % cross)
    else:
        print("Crossover infl* (delta=0) : none in swept range")

    # ---- Decision rule ----
    control_ok = control > 0.0  # harness sanity: control must show a gain
    never_hurts = all(d >= -0.005 for d in deltas.values())
    fails_in_range = any(deltas[infl] <= -0.02 for infl in INFL_SWEEP if infl >= 2.0)

    if not control_ok:
        verdict = "NOT_COMPUTABLE"
        reason = "control (infl=0) did not show a gain -> harness broken"
    elif never_hurts:
        verdict = "REPRODUCED"  # i.e. the 'never hurts' claim holds
        reason = "delta >= -0.005 for ALL swept infl"
    elif fails_in_range:
        verdict = "FAILED"
        reason = "delta <= -0.02 for at least one realistic infl (>=2.0)"
    else:
        verdict = "NOT_COMPUTABLE"
        reason = "neither clean-help nor clean-harm threshold met"

    print("=" * 64)
    print("MEASURED delta curve: " +
          ", ".join("%.1f->%+.4f" % (k, deltas[k]) for k in INFL_SWEEP))
    print("VERDICT: %s (%s)" % (verdict, reason))
    print("=" * 64)


if __name__ == "__main__":
    main()
