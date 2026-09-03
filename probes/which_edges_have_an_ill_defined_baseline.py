"""How many contradiction edges have a baseline that no seed can pin down?

WHY. The seed scatter in Table 2's random depth sits entirely in E(0): 9.522e-02 across twelve
seeds at s = 0, against 2.803e-15 at the valley. The cause is structural. Edge (8,14) has endpoint
degrees 5 and 1, so setting its coupling to zero leaves node 14 with no bond, the free spin makes
the sector's ground level two-fold degenerate, and the solver returns an arbitrary member of it.
The valley is reproducible; the reference point it is measured from is not.

That is a property of the EDGE, not of the run, so it can be enumerated in advance. This probe asks
which of the 14 tree edges and 27 random-graph edges have it, before anyone chooses a representative
edge or reports a depth.

CONTROLS, each able to fail:
  * TWO INDEPENDENT SIGNALS, AND THEY MUST AGREE. A pendant edge is a graph fact, computed from the
    generator. A degenerate baseline is a spectral fact, computed from the Hamiltonian. Each edge is
    scored on both, and a disagreement between them is reported rather than smoothed over: it would
    mean the mechanism is not the one named above.
  * A POSITIVE AND A NEGATIVE CASE ARE PINNED. Random (8,14) must come out degenerate and tree
    (1,10) must come out clean, since both were measured over twelve seeds already. If the cheap
    test disagrees with the expensive one, the cheap test is wrong.
  * THE COUNTS ARE REPORTED AGAINST THE EDGES ALREADY KNOWN TO BE INELIGIBLE, so the overlap with
    the nine negative-depth edges is measured rather than assumed.
  * A NULL THAT CAN FIRE. If no edge in either graph has a degenerate baseline, the finding does not
    generalise beyond (8,14) and the probe says so.
"""
from __future__ import annotations

import io
import json
import multiprocessing as mp
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "which_edges_have_an_ill_defined_baseline.result.json")

WORKERS = 4
N = 15
N_UP = 7
TOL = 1e-9
# Measured over twelve seeds in the_seed_scatter_lives_in_the_baseline_not_the_valley.py.
PINNED = {("random", (8, 14)): True, ("tree", (1, 10)): False}
# The nine random edges our all-sector regeneration marks ineligible under the E(0) baseline.
NEGATIVE_DEPTH = [(0, 11), (0, 1), (0, 8), (1, 6), (4, 5), (4, 12), (6, 8), (6, 11), (8, 9)]


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def graph_of(which):
    import networkx as nx
    if which == "tree":
        return [tuple(sorted(e)) for e in nx.random_labeled_tree(15, seed=42).edges()]
    return [tuple(sorted(e)) for e in nx.gnm_random_graph(15, 27, seed=42).edges()]


def _one(args):
    """Both signals for one edge: the graph fact and the spectral fact at s = 0."""
    import numpy as np
    import networkx as nx
    from scipy.sparse.linalg import eigsh
    from table_2_random_depth_is_a_seed_draw import his_basis, his_H
    which, contra = args
    edges = graph_of(which)
    G = nx.Graph(edges)
    H = G.copy()
    H.remove_edge(*contra)
    isolated = [n for n in H.nodes if H.degree(n) == 0]

    J = np.ones(len(edges))
    J[edges.index(contra)] = 0.0
    w = np.sort(eigsh(his_H(N, edges, J, his_basis(N, N_UP)), k=8, which="SA",
                      return_eigenvectors=False))
    deg = int(sum(1 for x in w if abs(x - w[0]) < TOL))
    return {"graph": which, "edge": list(contra),
            "endpoint_degrees": [G.degree(contra[0]), G.degree(contra[1])],
            "isolates_a_node": bool(isolated),
            "baseline_degeneracy": deg,
            "baseline_gap": float(w[1] - w[0])}


def main():
    jobs = [(w, e) for w in ("tree", "random") for e in graph_of(w)]
    print("  parallelism: %d workers of %d logical CPUs; %d edges, one solve each"
          % (WORKERS, os.cpu_count(), len(jobs)))
    t0 = time.time()
    with mp.Pool(WORKERS) as pool:
        rows = pool.map(_one, jobs)
    print("  %d edges in %.0fs" % (len(rows), time.time() - t0))

    # CONTROL: the two signals must agree edge by edge.
    disagree = [r for r in rows if r["isolates_a_node"] != (r["baseline_degeneracy"] > 1)]
    if disagree:
        print("  SIGNALS DISAGREE on %d edges; the named mechanism is not the whole story:"
              % len(disagree))
        for r in disagree:
            print("    %-7s %-8s isolates=%s degeneracy=%d gap %.2e"
                  % (r["graph"], tuple(r["edge"]), r["isolates_a_node"],
                     r["baseline_degeneracy"], r["baseline_gap"]))

    # CONTROL: the two edges already measured over twelve seeds must come out right.
    for (which, edge), expect in PINNED.items():
        hit = [r for r in rows if r["graph"] == which and tuple(r["edge"]) == edge]
        if not hit:
            refuse("pinned edge %s %s is not in the enumeration" % (which, edge))
        got = hit[0]["baseline_degeneracy"] > 1
        if got != expect:
            refuse("pinned edge %s %s came out %s, against the twelve-seed measurement; the cheap "
                   "test disagrees with the expensive one" % (which, edge, got))
    print("  PINNED CASES: random (8,14) degenerate, tree (1,10) clean, both as measured")

    bad = {"tree": [], "random": []}
    for r in rows:
        if r["baseline_degeneracy"] > 1:
            bad[r["graph"]].append(tuple(r["edge"]))
    print()
    for which in ("tree", "random"):
        total = len(graph_of(which))
        print("  %-7s edges with a degenerate E(0) baseline: %d of %d  %s"
              % (which, len(bad[which]), total, sorted(bad[which])))

    if not bad["tree"] and not bad["random"]:
        print("  NULL FIRED: no edge has a degenerate baseline, so the finding does not generalise.")

    overlap = sorted(set(bad["random"]) & set(NEGATIVE_DEPTH))
    only_baseline = sorted(set(bad["random"]) - set(NEGATIVE_DEPTH))
    print()
    print("  of the nine random edges already ineligible for a NEGATIVE depth, %d also have a "
          "degenerate baseline: %s" % (len(overlap), overlap))
    print("  random edges the negative-depth rule does NOT already exclude: %s" % only_baseline)

    deepest_tree = (2, 3)
    tree_hit = deepest_tree in bad["tree"]
    print("  Table 2's tree edge %s has a degenerate baseline: %s" % (deepest_tree, tree_hit))

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sector_n_up": N_UP, "workers": WORKERS,
        "rows": rows,
        "degenerate_baseline": {k: [list(e) for e in sorted(v)] for k, v in bad.items()},
        "overlap_with_negative_depth": [list(e) for e in overlap],
        "not_already_excluded": [list(e) for e in only_baseline],
        "table2_tree_edge_affected": tree_hit,
        "signals_disagree_on": [{"graph": r["graph"], "edge": r["edge"]} for r in disagree],
        "controls": {
            "two_independent_signals_compared": True,
            "pinned_cases_match_the_twelve_seed_measurement": True,
            "null_can_fire": True,
            "overlap_with_known_ineligible_measured": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
