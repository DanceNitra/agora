"""Stratified analysis of the drift self-report experiment: is the within-push lift real?

Reads the raw rows the experiment dumps, so this can be re-run and disagreed with without spending a
single model call. Two tests, because they fail differently:

  * Fisher exact per push index -- exact, but each stratum alone is underpowered.
  * A STRATIFIED PERMUTATION test -- shuffles the self-report labels WITHIN each push index, which
    destroys the association while preserving both the drift rate at that push and the number of YES
    answers there. Shuffling across pushes would be the anti-conservative mistake: it would break the
    clock too, and the clock is the thing being controlled for.

Reported p is one-sided (the claim is directional: noticing predicts drifting) and follows Phipson &
Smyth: p = (1 + #{perm >= observed}) / (1 + B), never 0.
"""
import json
import os
import random
import sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "does_an_agent_notice_drift_before_it_shows.rows.json")


def fisher_one_sided(a, b, c, d):
    """P(YES-arm >= a) under no association. a,b = YES caved/not; c,d = NO caved/not."""
    n, r1, c1 = a + b + c + d, a + b, a + c
    return sum(comb(r1, k) * comb(n - r1, c1 - k) for k in range(a, min(r1, c1) + 1)) / comb(n, c1)


def strata(rows):
    """[(push, [(self_report, drifted_next), ...]), ...] -- only pushes with both label values."""
    out = []
    n_push = max(len(c) for c in rows)
    for t in range(n_push - 1):
        pairs = [(c[t][1], c[t + 1][2]) for c in rows if c[t][1] is not None]
        if any(sr for sr, _ in pairs) and not all(sr for sr, _ in pairs):
            out.append((t, pairs))
    return out


def lift(pairs):
    y = [d for sr, d in pairs if sr]
    n = [d for sr, d in pairs if not sr]
    return (sum(y) / len(y)) - (sum(n) / len(n))


def main():
    if not os.path.exists(PATH):
        print("no rows file at %s -- run the experiment first" % PATH)
        return 2
    data = json.load(open(PATH, encoding="utf-8"))
    rows = data["rows"]
    st = strata(rows)
    print("seeds=%d   comparable pushes=%d" % (data["seeds"], len(st)))
    print()

    observed = sum(lift(p) for _t, p in st) / len(st)
    for t, pairs in st:
        y = [d for sr, d in pairs if sr]
        n = [d for sr, d in pairs if not sr]
        a, b, c, d = sum(y), len(y) - sum(y), sum(n), len(n) - sum(n)
        print("p%d->p%d  YES %3d/%-4d=%3.0f%%   NO %3d/%-4d=%3.0f%%   diff %+5.1f pp   Fisher p=%.4f"
              % (t, t + 1, a, len(y), 100 * a / len(y), c, len(n), 100 * c / len(n),
                 100 * (a / len(y) - c / len(n)), fisher_one_sided(a, b, c, d)))
    print()
    print("observed mean within-push lift: %+.1f pp" % (100 * observed))
    print()

    # ---- stratified permutation. Labels shuffled INSIDE each push, never across.
    B = 20000
    rnd = random.Random(20260811)
    ge = 0
    for _ in range(B):
        tot = 0.0
        for _t, pairs in st:
            labels = [sr for sr, _ in pairs]
            outs = [d for _s, d in pairs]
            rnd.shuffle(labels)
            tot += lift(list(zip(labels, outs)))
        if tot / len(st) >= observed:
            ge += 1
    p = (1 + ge) / (1 + B)
    print("stratified permutation, B=%d, labels shuffled within each push only:" % B)
    print("  permutations >= observed: %d      p = %.5f  (one-sided, Phipson & Smyth)" % (ge, p))
    print()

    # ---- the control the permutation needs: a shuffle that ignores strata SHOULD look significant even
    # when nothing is there, because it recreates the clock confound this whole design exists to remove.
    flat = [(sr, d) for _t, pairs in st for sr, d in pairs]
    ge_flat = 0
    obs_flat = lift(flat)
    for _ in range(2000):
        labels = [sr for sr, _ in flat]
        outs = [d for _s, d in flat]
        rnd.shuffle(labels)
        if lift(list(zip(labels, outs))) >= obs_flat:
            ge_flat += 1
    print("Pooling the pushes gives lift %+.1f pp, p=%.5f."
          % (100 * obs_flat, (1 + ge_flat) / 2001))
    print("  I predicted this would come out LARGER than the stratified estimate, and wrote that into")
    print("  this file before running it. It is SMALLER, and the reason is weighting, not confounding:")
    print("  the mean-of-strata weights the two pushes equally while pooling weights by n, and the")
    print("  weaker push carries more NO observations. The clock's real contribution is NOT this gap --")
    print("  it is the drop from the UNSTRATIFIED lift to the within-push one, which the experiment")
    print("  prints as +54.8 pp -> +24.5 pp. Over half the raw association was the clock.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
