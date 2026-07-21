"""
Fair vs circular ground truth for "does the full chunk beat the flat 5-D projection?"
(motivated by the TAT / mnemo cross-framework thread, DeepSeek-V3 #1466).

Context. A state-relevance benchmark that defines relevance as "the 5 nearest neighbours
in the 5-D chunk" is CIRCULAR for the full-vs-flat question: relevance IS 5-D proximity,
so any extra layer (transitions, timestamps) can only pull a candidate away from the
target -> full-chunk can only match-or-lose, by construction. That yardstick cannot tell
you whether the extra layers ADD value; it can only tell you how far they DEVIATE from the
5-D. (On the real #1466 file the effect is monotone: cosine ceiling 5-D=0.80 ->
+transitions 0.35 -> +timestamp 0.31 -> full 15-D 0.17.)

This probe demonstrates the point on data we fully control, with ZERO external deps:
build one synthetic corpus of records drawn from 4 latent regimes whose 5-D centroids
OVERLAP (so the 5-D alone cannot fully separate them) but whose extra layers (transition
signature + time-of-day) are DISCRIMINATIVE. Then score the identical records + identical
retrieval under two different ground truths:

  * CIRCULAR GT  = 5-nearest in the 5-D core (mirrors the #1466 benchmark)
  * FAIR GT      = same latent regime label (independent of the raw 5-D coordinates)

Only the yardstick changes. Result (seed 20260707):
  CIRCULAR GT : flat-5D 1.000  full-chunk 0.535  delta -0.465
  FAIR GT     : flat-5D 0.595  full-chunk 1.000  delta +0.405

So the extra layers CAN add large value; the circular GT is simply structurally unable to
reward them. To test whether transitions/timestamps pay off, the ground truth must be
independent of the 5-D projection (a downstream/predictive or regime-membership label),
not nearest-in-the-same-5D.

Honest scope: this is a mechanism demonstration on constructed data, NOT a claim about any
specific real dataset. It shows what a non-circular GT reveals that a circular one cannot.

Run: python marat_fair_vs_circular_gt_probe.py
"""
import math
import random

CORE = ["theme", "role", "emotion", "meaning", "goal"]
LAYER = ["transition_prev", "transition_next", "cluster_density", "hour"]
ALL = CORE + LAYER

# 4 regimes; centroids so regimes 0&1 and 2&3 OVERLAP in 5-D but DIFFER in the extra layers.
CORE_C = {0: [0.30, 0.30, 0.5, 0.5, 0.5], 1: [0.33, 0.32, 0.5, 0.5, 0.5],
          2: [0.70, 0.70, 0.5, 0.5, 0.5], 3: [0.72, 0.71, 0.5, 0.5, 0.5]}
LAYER_C = {0: [0.20, 0.20, 0.3, 8], 1: [0.80, 0.80, 0.7, 20],
           2: [0.20, 0.80, 0.5, 8], 3: [0.80, 0.20, 0.5, 20]}


def make(rng, reg):
    c = {d: CORE_C[reg][i] + rng.gauss(0, 0.06) for i, d in enumerate(CORE)}
    for i, d in enumerate(LAYER):
        c[d] = LAYER_C[reg][i] + rng.gauss(0, 1.0 if d == "hour" else 0.05)
    return c, reg


def run(seed=20260707, n_records=200, n_queries=40, k=5):
    rng = random.Random(seed)
    recs = [make(rng, rng.randrange(4)) for _ in range(n_records)]
    queries = [make(rng, rng.randrange(4)) for _ in range(n_queries)]
    mn = {d: min(r[0][d] for r in recs) for d in ALL}
    mx = {d: max(r[0][d] for r in recs) for d in ALL}

    def norm(c):
        return {d: ((c[d] - mn[d]) / (mx[d] - mn[d]) if mx[d] > mn[d] else 0.0) for d in ALL}

    def eucl(a, b, dims):
        return math.sqrt(sum((a[d] - b[d]) ** 2 for d in dims))

    def score(dims, gt_mode):
        tot = 0.0
        for qc, qreg in queries:
            qn = norm(qc)
            ranked = sorted(recs, key=lambda r: eucl(norm(r[0]), qn, dims))
            if gt_mode == "regime":
                tot += sum(1 for r in ranked[:k] if r[1] == qreg) / k
            else:  # circular: GT = 5-NN in the 5-D core
                gt = set(id(r) for r in sorted(recs, key=lambda r: eucl(norm(r[0]), qn, CORE))[:k])
                tot += len(set(id(r) for r in ranked[:k]) & gt) / k
        return tot / len(queries)

    return {
        "circular": {"flat5D": score(CORE, "circ"), "full": score(ALL, "circ")},
        "fair": {"flat5D": score(CORE, "regime"), "full": score(ALL, "regime")},
    }


if __name__ == "__main__":
    r = run()
    print("Same synthetic corpus, two ground truths, ceiling (pure numeric-NN), recall@5:")
    for name, label in (("circular", "CIRCULAR GT (=5-NN in 5-D, like #1466)"),
                        ("fair", "FAIR GT (=same latent regime, independent) ")):
        a, b = r[name]["flat5D"], r[name]["full"]
        print(f"  {label}: flat-5D={a:.3f}  full-chunk={b:.3f}  delta={b - a:+.3f}")
    print("\ncircular GT: full-chunk can only match-or-lose (deviates from the definition).")
    print("fair GT:     full-chunk wins iff the extra layers carry signal the 5-D can't see.")
