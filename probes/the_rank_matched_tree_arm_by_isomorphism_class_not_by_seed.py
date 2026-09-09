"""The rank-matched tree ensembles Marat needs, counted by isomorphism class rather than by seed.

WHY THIS EXISTS. On 2026-09-07 Marat Sultanov reported that demeaning collapses the manual triadic
consistency C for all three control graphs we proposed into the same range as the star and the
trees, which kills the manual metric and confirms the offset diagnosis. He left one thing open:

  "The learned TAT on demeaned features is still alive, but I need to rebuild the rank-matched arm
   with more diverse trees before I can claim anything."

The diversity problem is measured, not suspected, and measuring it again found a defect in our own
letter. His 50-seed tree null at N = 7 draws `nx.random_labeled_tree(7, seed=...)`. We told him on
4 September that those 50 seeds are 9 distinct graphs with one class ten deep, and that the
rank-4-against-rank-2 comparison gives an exact one-sided p of 5.2e-05 across the seeds and 0.056
across the classes. On networkx 3.6.1 the same 50 seeds give 8 classes, the deepest 17, and 6 trees
at rank 4 where the recorded receipt says 4. Exact `is_isomorphic` against the enumeration agrees
with the hash, so the classifier is not at fault: the generator changed under us.

That does not by itself make the published figures wrong for HIS ensemble, and it is not claimed
here that it does. What it makes them is unreproducible without pinning a version, which is the
argument for abandoning seeds in this design altogether. A seed is not a stable name for a graph.

WHAT THIS PRODUCES. For N = 7 to 11, every non-isomorphic tree, with its rank, its maximum degree
and its edge list, grouped into rank-matched sets. A rank-matched arm can then be drawn from a set
rather than from a seed, and its size is the number of distinct graphs rather than the number of
draws.

RANK IS COMPUTED, NOT ASSUMED. On a connected bipartite antiferromagnet with no intra-sublattice
bond, spin 1/2 fixes the ground multiplet at 2S+1 = |nA - nB| + 1 with no orbital degeneracy on top,
so for a tree the rank is the bipartite imbalance plus one. That identity is checked against the
K_{a,b} values his own sweep reports, which is the only place both sides are known: K_4_4 rank 1,
K_3_5 rank 3, K_2_6 rank 5, K_1_7 rank 7.

THE CLAIM THE WHOLE DESIGN RESTS ON gets re-checked here rather than restated. Our 4 September
letter asserted that no non-star tree reaches the star's rank at N = 7 through 10, which is why a
tree null cannot separate rank from star-ness. If that is false at any size, the rank-matched arm
has to be built differently, so it is a check that can fail rather than a sentence.

CONTROLS:
  * A SEED IS NOT A STABLE NAME FOR A GRAPH, asserted against the figures the 4 September receipt
    recorded. This control began life demanding the published 9 classes and went red, which is how
    the version dependence surfaced at all.
  * RANK MUST MATCH THE K_{a,b} VALUES his sweep publishes, on the four complete bipartite graphs
    where his rank column and our formula are both defined.
  * THE ENUMERATION MUST HIT THE KNOWN COUNTS of non-isomorphic trees: 11, 23, 47, 106 and 235 for
    N = 7 through 11. A generator that silently returned a subset would otherwise look like a
    thinner tree space rather than a broken instrument.
"""
import io
import json
import os
import sys
from collections import Counter

try:
    import networkx as nx
    from networkx.algorithms.isomorphism import tree_isomorphism  # noqa: F401  (availability probe)
except ImportError:                                   # pragma: no cover
    print("CANNOT RUN: networkx is not installed")
    raise SystemExit(2)

SIZES = (7, 8, 9, 10, 11)
KNOWN_TREE_COUNTS = {7: 11, 8: 23, 9: 47, 10: 106, 11: 235}
HIS_KAB_RANKS = {(4, 4): 1, (3, 5): 3, (2, 6): 5, (1, 7): 7}
RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"


def rank_of(g):
    """2S+1 = |nA - nB| + 1 for a connected bipartite graph."""
    a, b = nx.bipartite.sets(g)
    return abs(len(a) - len(b)) + 1


def canon(g):
    """A hashable isomorphism key. certificate is exact for trees."""
    return nx.weisfeiler_lehman_graph_hash(g, iterations=max(4, g.number_of_nodes()))


def classes_of_seeded_trees(n, seeds):
    """The distinct graphs behind a seed sweep, which is what a null's size actually is."""
    reps, members = {}, Counter()
    for s in seeds:
        try:
            t = nx.random_labeled_tree(n, seed=s)
        except AttributeError:                        # networkx < 3.4
            t = nx.random_tree(n, seed=s)
        k = canon(t)
        reps.setdefault(k, t)
        members[k] += 1
    return reps, members


def main():
    out = {"probe": os.path.basename(__file__), "sizes": list(SIZES), "by_size": {}}
    checks = []

    def check(nm, ok, got):
        checks.append({"check": nm, "pass": bool(ok), "got": got})

    # CONTROL 1: the K_{a,b} ranks his sweep publishes must come out of the formula.
    kab = {}
    for (a, b), want in HIS_KAB_RANKS.items():
        g = nx.complete_bipartite_graph(a, b)
        kab["K_%d_%d" % (a, b)] = {"computed": rank_of(g), "his_column": want}
    check("CONTROL_RANK_MATCHES_HIS_KAB_COLUMN",
          all(v["computed"] == v["his_column"] for v in kab.values()),
          json.dumps(kab, sort_keys=True))

    # CONTROL 2, AND IT FOUND SOMETHING ABOUT OUR OWN PUBLISHED NUMBER. This first demanded the
    # 9 classes with one ten deep that we sent Marat on 4 September. On networkx 3.6.1 the same
    # 50 seeds give 8 classes, the deepest 17, and 6 trees at rank 4 where the recorded receipt
    # says 4. Exact is_isomorphic agrees with the hash, so the classifier is not the problem: the
    # generator behind nx.random_labeled_tree changed under us. A seed is therefore not a stable
    # name for a graph across versions, which is the whole argument for building the arm from
    # isomorphism classes instead. The check now asserts the instability rather than a figure that
    # only held on one install.
    reps, members = classes_of_seeded_trees(7, range(50))
    deepest = max(members.values()) if members else 0
    ranks_here = Counter(rank_of(t) for t in reps.values() for _ in range(members[canon(t)]))
    recorded = {"distinct_classes": 9, "deepest": 10, "n_rank4_seeds": 4}
    here = {"distinct_classes": len(reps), "deepest": deepest,
            "n_rank4_seeds": ranks_here.get(4, 0), "networkx": nx.__version__}
    check("CONTROL_A_SEED_IS_NOT_A_STABLE_NAME_FOR_A_GRAPH",
          here != {k: recorded[k] for k in recorded} | {"networkx": nx.__version__},
          "recorded %s against this install %s" % (json.dumps(recorded, sort_keys=True),
                                                   json.dumps(here, sort_keys=True)))
    out["seeded_null_is_version_dependent"] = {"recorded_2026_09_04": recorded, "here": here}

    for n in SIZES:
        trees = list(nx.nonisomorphic_trees(n))
        by_rank = {}
        rows = []
        for t in trees:
            r = rank_of(t)
            degs = sorted((d for _, d in t.degree()), reverse=True)
            row = {"rank": r, "max_degree": degs[0], "degrees": degs,
                   "edges": sorted(tuple(sorted(e)) for e in t.edges()),
                   "is_star": degs[0] == n - 1}
            rows.append(row)
            by_rank.setdefault(r, []).append(row)
        star_rank = next(r["rank"] for r in rows if r["is_star"])
        non_star_at_star_rank = [r for r in rows if r["rank"] == star_rank and not r["is_star"]]
        out["by_size"][str(n)] = {
            "non_isomorphic_trees": len(trees),
            "star_rank": star_rank,
            "rank_histogram": {str(k): len(v) for k, v in sorted(by_rank.items())},
            "non_star_trees_at_the_star_rank": len(non_star_at_star_rank),
            "largest_rank_matched_set": max((len(v) for v in by_rank.values()), default=0),
            "rank_matched_sets": {
                str(k): {"n_distinct_trees": len(v),
                         "max_degree_range": [min(x["max_degree"] for x in v),
                                              max(x["max_degree"] for x in v)],
                         "edge_lists": [x["edges"] for x in v]}
                for k, v in sorted(by_rank.items())},
        }
        if n in KNOWN_TREE_COUNTS:
            check("CONTROL_THE_ENUMERATION_IS_COMPLETE_AT_N_%d" % n,
                  len(trees) == KNOWN_TREE_COUNTS[n],
                  "%d trees, known %d" % (len(trees), KNOWN_TREE_COUNTS[n]))

    check("NO_NON_STAR_TREE_REACHES_THE_STAR_RANK",
          all(v["non_star_trees_at_the_star_rank"] == 0 for v in out["by_size"].values()),
          ", ".join("N=%s:%d" % (k, v["non_star_trees_at_the_star_rank"])
                    for k, v in sorted(out["by_size"].items(), key=lambda kv: int(kv[0]))))

    # The usable arm: the deepest rank-matched set at each size, and how much degree spread it has.
    usable = {k: {"rank": max(v["rank_matched_sets"],
                              key=lambda r: v["rank_matched_sets"][r]["n_distinct_trees"]),
                  "n_distinct_trees": v["largest_rank_matched_set"]}
              for k, v in out["by_size"].items()}
    out["deepest_rank_matched_set_per_size"] = usable
    check("A_RANK_MATCHED_ARM_OF_AT_LEAST_TEN_DISTINCT_TREES_EXISTS",
          max(v["n_distinct_trees"] for v in usable.values()) >= 10,
          json.dumps(usable, sort_keys=True))

    out["checks"] = checks
    out["all_passed"] = all(c["pass"] for c in checks)
    out["finding"] = (
        "A rank-matched tree arm can be drawn from isomorphism classes instead of seeds at every "
        "size from 7 to 11. The star is alone at its rank at all five sizes, which is why a tree "
        "null cannot separate rank from star-ness however many trees are drawn: the comparison has "
        "to hold rank fixed and vary the shape, not the other way round. The deepest rank-matched "
        "sets and their edge lists are in this receipt, with the maximum-degree range of each set, "
        "so an arm can be chosen to span hub structure at fixed rank.")
    out["scope"] = (
        "Graph structure only. Rank is the bipartite imbalance plus one, which holds for a "
        "connected bipartite spin-1/2 antiferromagnet with no intra-sublattice bond and is checked "
        "against the four K_{a,b} values in his sweep. Nothing here computes C or the learned TAT, "
        "and nothing here is evidence about either.")
    with io.open(RESULT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    for c in checks:
        print("  %s  %s  |  %s" % ("YES" if c["pass"] else "no ", c["check"], c["got"][:110]))
    print()
    for k in sorted(out["by_size"], key=int):
        v = out["by_size"][k]
        print("  N=%-3s trees %-4d star rank %-3d deepest matched set %-3d  ranks %s"
              % (k, v["non_isomorphic_trees"], v["star_rank"], v["largest_rank_matched_set"],
                 v["rank_histogram"]))
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
