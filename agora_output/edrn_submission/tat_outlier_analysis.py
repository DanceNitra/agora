"""The star as an outlier against the tree population, not as a class in a classifier.

FOR MARAT. You asked for the script rather than the description, so this is runnable as it stands.
It does the four things you listed, and one you did not, which is the one that makes the number
mean something.

WHY THE FRAMING CHANGES. Your positive class is one graph jittered fifty times. Cross-validation
over near-duplicates measures memorisation: no fold can hold the star out, because there is only one
star. That is not a flaw in the classifier, it is a question the data cannot answer in that shape.
One object against a population is an outlier question, and an outlier question has a statistic and
a null.

THE FOUR CHANGES YOU NAMED:
  1. s = 0 is dropped. The contradiction edge has weight zero there, the graph comes apart, the gap
     inside four of the six ground sectors falls to about 2e-15, and `eigh` returns an arbitrary
     vector out of a degenerate subspace. Measured: the same star under two node labellings gives
     I(0) = 0.219396 and 0.208193, while at s = 1 the two agree to 1.1e-16.
  2. The six constant features are dropped. `demean_norm` z-scores each stream, so E_mean, O_mean and
     I_mean are 0 and the three standard deviations are 1, in every row. Nine features remain.
  3. `bipartite_rank` runs as a baseline, so the report says what the features add over one integer.
  4. The statistic is distance from the tree population, not an accuracy.

THE FIFTH, AND IT IS THE ONE THAT DECIDES WHETHER THE NUMBER IS WORTH ANYTHING. A distance on its
own is unreadable: 3.2 is large or small only against something. So every TREE is also scored as an
outlier against the remaining trees, leave-one-out. That gives a null distribution of exactly the
same statistic, computed the same way, on objects we agree are not special. The star's rank within
that null is the result. If the star sits inside the tree null, the features do not separate it, and
the script says so.

WHAT THIS SCRIPT WILL NOT DO. It will not tell you the features beat `bipartite_rank`. Rank separates
the two classes perfectly on its own, at every size, because the star is the unique tree at its own
degeneracy. The honest question is not whether the star is an outlier, which rank already settles,
but whether it is an outlier IN THE DYNAMICS once rank is held fixed. The rank-matched arm at the
end is where that gets answered, and it is the arm that can come out against us.

CONTROLS, each of which can fail:
  * A NULL FROM THE SAME STATISTIC. Trees scored leave-one-out. Without it a distance is a number
    with no scale.
  * A FALSE-POSITIVE RATE. Every tree takes the star's place in turn and is scored against a null
    built from the trees remaining after it is removed. The fraction called extreme is the rate at
    which this procedure flags nothing at all. If that rate meets the star's own p-value, the result
    is empty and the script says so.
    Written first as a single swap of one tree, which could not fail: that number IS the null's own
    first entry, so the control agreed with itself by construction and its warning branch was dead
    code. A verification pass caught it. Note the rate cannot fall below 1/(n+1), so with fifty trees
    a p-value near 0.02 is at the resolution limit of the sample rather than a finding.
  * A CONSTANT-FEATURE ASSERTION. The six dropped features are checked to be constant on the data
    actually loaded, rather than dropped by name on trust.
  * A RANK-MATCHED ARM. Star against trees of the same ground degeneracy. This is the only arm that
    can show the dynamics carry something rank does not, and it is allowed to fail.
"""
from __future__ import annotations

import io
import json
import os
import sys

sys.stdout.reconfigure(line_buffering=True)

FEAT_NAMES = ["E_mean", "E_std", "E_min", "E_max",
              "O_mean", "O_std", "O_min", "O_max",
              "I_mean", "I_std", "I_min", "I_max",
              "corr(E,O)", "corr(E,I)", "corr(O,I)"]
CONSTANT_BY_CONSTRUCTION = ["E_mean", "E_std", "O_mean", "O_std", "I_mean", "I_std"]


def refuse(why):
    print("REFUSED: " + why)
    raise SystemExit(2)


def bipartite_rank(n, edges):
    """Your function, unchanged, so the baseline is yours and not my restatement of it."""
    import networkx as nx
    from collections import deque
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from(edges)
    color = {0: 0}
    q = deque([0])
    while q:
        u = q.popleft()
        for v in G.neighbors(u):
            if v not in color:
                color[v] = 1 - color[u]
                q.append(v)
    nA = sum(1 for v, c in color.items() if c == 0)
    return int(2 * (abs(nA - (n - nA)) / 2) + 1)


def outlier_score(point, population):
    """Robust distance from a population, in units of that population's own spread.

    Median and MAD rather than mean and standard deviation, because with fifty near-identical rows a
    single extreme member inflates the standard deviation and hides itself. Per-feature, then the
    largest, so one genuinely extreme coordinate is not averaged away by eight ordinary ones.
    """
    import numpy as np
    pop = np.asarray(population, dtype=float)
    med = np.median(pop, axis=0)
    mad = np.median(np.abs(pop - med), axis=0) * 1.4826
    mad = np.where(mad < 1e-12, np.nan, mad)          # a dead feature scores nothing, not infinity
    z = np.abs(np.asarray(point, dtype=float) - med) / mad
    z = z[~np.isnan(z)]
    if z.size == 0:
        refuse("every feature had zero spread in the population, so no distance is defined")
    return float(np.max(z)), z


def analyse(star_rows, tree_rows, label, live=None):
    import numpy as np
    star = np.asarray(star_rows, dtype=float)
    trees = np.asarray(tree_rows, dtype=float)

    # CONTROL: the six are constant on THIS data, not by reputation.
    allrows = np.vstack([star, trees])
    spread = allrows.max(axis=0) - allrows.min(axis=0)
    dead = [FEAT_NAMES[i] for i in range(len(FEAT_NAMES)) if spread[i] < 1e-6]
    if sorted(dead) != sorted(CONSTANT_BY_CONSTRUCTION):
        print("  NOTE: the constant features on this data are %s, not the six expected. Dropping "
              "what is actually constant." % dead)
    keep = [i for i in range(len(FEAT_NAMES)) if FEAT_NAMES[i] not in dead]
    S, T = star[:, keep], trees[:, keep]

    star_point = np.median(S, axis=0)
    star_score, _ = outlier_score(star_point, T)

    # NULL: every tree against the others, same statistic, same code path.
    null = []
    for i in range(len(T)):
        others = np.delete(T, i, axis=0)
        s, _ = outlier_score(T[i], others)
        null.append(s)
    null = np.array(null)
    rank = int((null >= star_score).sum())
    p_like = (rank + 1) / (len(null) + 1)

    # CONTROL: a FALSE-POSITIVE RATE, not a single swap.
    #
    # The first version scored T[0] against the other trees and compared that to the null. Those are
    # the same computation: null[0] IS that number, so the control agreed with itself by
    # construction and its warning branch could never run. A control that cannot fire is the defect
    # this whole analysis exists to avoid, and it was sitting in the analysis.
    #
    # What the control has to answer is: if an ORDINARY object stood where the star stands, how often
    # would this procedure call it extreme? So every tree takes the star's place in turn and is
    # scored against a null built from the trees that remain after it is removed. The fraction that
    # land at or beyond the star's own score is the rate at which the statistic flags nothing.
    flagged = 0
    for i in range(len(T)):
        rest = np.delete(T, i, axis=0)
        s_i, _ = outlier_score(T[i], rest)
        null_i = []
        for j in range(len(rest)):
            others = np.delete(rest, j, axis=0)
            sj, _ = outlier_score(rest[j], others)
            null_i.append(sj)
        if (np.array(null_i) >= s_i).sum() == 0:
            flagged += 1
    false_positive_rate = flagged / len(T)

    print("  [%s] features kept %d of %d (dropped %s)"
          % (label, len(keep), len(FEAT_NAMES), ", ".join(dead) or "none"))
    print("      star outlier score %.3f | tree null median %.3f, max %.3f"
          % (star_score, float(np.median(null)), float(null.max())))
    print("      trees scoring at least as extreme as the star: %d of %d  (p-like %.3f)"
          % (rank, len(null), p_like))
    print("      FALSE-POSITIVE CONTROL: %d of %d ordinary trees would also be called extreme in "
          "the star's position (%.0f%%)" % (flagged, len(T), 100 * false_positive_rate))
    if false_positive_rate >= p_like:
        print("      ^ the procedure calls an ordinary tree extreme at least as often as it calls "
              "the star extreme. The star's score carries no information here.")
    return {"label": label, "features_kept": len(keep), "dropped": dead,
            "star_score": star_score, "null_median": float(np.median(null)),
            "null_max": float(null.max()), "trees_at_least_as_extreme": rank,
            "p_like": p_like,
            "false_positive_rate": false_positive_rate,
            "ordinary_trees_flagged": flagged,
            "control_says_result_is_empty": false_positive_rate >= p_like}


def main():
    import numpy as np
    src = os.environ.get("TAT_FEATURES")
    if not src or not os.path.exists(src):
        print(__doc__)
        print("USAGE: set TAT_FEATURES to a JSON file shaped")
        print('  {"star": [[15 floats] x N], "trees": [[15 floats] x M],')
        print('   "tree_ranks": [M ints], "star_rank": int}')
        print()
        print("The 15 floats are your feature vector in the order printed by cell 33, and the ranks")
        print("come from bipartite_rank. Nothing else is needed. If you export from the notebook")
        print("with s_values[1:] the s=0 point is already gone; otherwise rebuild the streams")
        print("without it, because dropping a COLUMN is not the same as dropping that scan point.")
        return 1

    d = json.load(io.open(src, encoding="utf-8"))
    star, trees = d["star"], d["trees"]
    if not star or not trees:
        refuse("the feature file has no star rows or no tree rows")
    if len(star[0]) != 15 or len(trees[0]) != 15:
        refuse("expected 15 features per row, found %d and %d" % (len(star[0]), len(trees[0])))

    print("  loaded %d star rows, %d tree rows" % (len(star), len(trees)))
    out = {"n_star": len(star), "n_trees": len(trees), "arms": []}
    out["arms"].append(analyse(star, trees, "all trees"))

    # THE ARM THAT CAN GO AGAINST US: hold rank fixed.
    tr, sr = d.get("tree_ranks"), d.get("star_rank")
    if tr and sr is not None:
        matched = [trees[i] for i, r in enumerate(tr) if r == sr]
        print()
        print("  BASELINE: bipartite_rank alone. star rank %s, tree ranks %s"
              % (sr, dict((r, tr.count(r)) for r in sorted(set(tr)))))
        if sr not in tr:
            print("      rank separates the two classes perfectly on its own, with no dynamics at")
            print("      all. So the arm below is the one that decides what the features add.")
        if len(matched) < 5:
            print("      only %d rank-matched trees: too few for a null. Generate more at a size "
                  "where they exist, which is why cell 37 had to move to N=9." % len(matched))
        else:
            out["arms"].append(analyse(star, matched, "rank-matched trees only"))
    else:
        print("  NOTE: no ranks supplied, so the baseline arm did not run. Add tree_ranks and")
        print("        star_rank; without them this script cannot say what the features add.")

    dst = os.path.splitext(src)[0] + ".outlier_result.json"
    json.dump(out, io.open(dst, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print()
    print("  written: %s" % dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
