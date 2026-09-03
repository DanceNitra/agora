"""Recompute every Table 2 edge from the Hamiltonian, both views, on one calibrated pipeline.

WHY. Edge (8,14) has three numbers on record and they disagree. Regenerating it settled that one:
the theory view reproduces 0.010163 exactly, the repaired CSV's 0.050837 reproduces nothing, and the
standard view finds no valley at all. That was one edge. Table 2 rests on the rest of them, so the
rest get the same treatment rather than an inference from the one.

The pipeline is the one from regenerate_edge_8_14.py, unchanged, and it is calibrated before it is
believed: tree edge (1,10), where the standard view, the theory view and the repaired CSV all agree
at 0.058909125, is computed first and must land within 5e-6 or nothing else is reported.

THE DEFECT THAT MADE THE FIRST ATTEMPT AGREE WITH ITSELF, recorded because it is the reason the two
views can be trusted to differ now. The ground manifold crosses magnetisation sectors: on the random
graph at s = 1.2, n_up = 6, 7, 8 and 9 all sit at E0 = -7.291497416, one S = 3/2 multiplet. Counting
degeneracy inside a single sector reported 1, so the projection average had one state to average and
the theory arm silently became a copy of the standard arm. Both printed -0.001524. On a bipartite
graph the two arms coincide for a real reason, since the members of an S = 1/2 doublet give the same
<sigma^z sigma^z> under spin flip, which is why the tree calibration passed either way and could not
have caught it.

CONTROLS:
  * CALIBRATION FIRST, on a value all three sources agree on. Fail it and nothing is published.
  * THE TWO VIEWS MUST DIFFER SOMEWHERE. If every edge gives standard == theory to machine
    precision, the projection average is not averaging and the run is void, exactly as it was the
    first time.
  * THE ORBIT CLAIM IS CHECKED, NOT ASSUMED. Tree edges in one automorphism orbit must give equal
    theory-view depths. That is the paper's own abstract, so a disagreement is a finding about the
    paper rather than about this script.
  * EVERY DEPTH IS REPORTED WITH ITS SIGN. A negative depth breaks the E(0) baseline and marks the
    edge ineligible, which is how (6,11) was already handled.
"""
from __future__ import annotations

import io
import json
import multiprocessing as mp
import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "regenerate_table2.result.json")

WORKERS = 4                  # of 24 logical CPUs. Dropped from 12 on the owner's request: at 12 each
                             # worker holds a 6435x6435 sparse operator and the box became unusable.
# THE GRID THAT BUILT TABLE 2, not the one the repaired folder states.
# The repaired folder runs linspace(0, 2, 41). Table 2 did not come from there: the archive's older
# .txt sweeps s in [0,3] at step 0.05 and ends with a FINAL SUMMARY carrying all four of Table 2's
# numbers verbatim. Scanning [0,2] and then reporting that Table 2 does not reproduce compares
# against a grid one third shorter than the one that produced it, and (3,11) has its minimum at
# s = 2.50, outside it entirely. I told Guanghao the opposite of this nine hours ago; he had it
# right in his item 5.
GRID_LO, GRID_HI, GRID_N = 0.0, 3.0, 61
CAL = {"edge": (1, 10), "expected": 0.058909125, "tol": 5e-6}


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def _one(args):
    """One edge, both views. Runs in a worker."""
    import numpy as np
    from regenerate_edge_8_14 import scan, valley
    which, edges, contra = args
    grid = np.linspace(GRID_LO, GRID_HI, GRID_N)
    cache = {}
    std = valley(scan(edges, contra, grid, standard=True, cache=cache))
    thy = valley(scan(edges, contra, grid, standard=False, cache=cache))
    return {"graph": which, "edge": list(contra), "standard": std, "theory": thy}


def main():
    import numpy as np
    import networkx as nx

    tree = [tuple(sorted(e)) for e in nx.random_labeled_tree(15, seed=42).edges()]
    rand = [tuple(sorted(e)) for e in nx.gnm_random_graph(15, 27, seed=42).edges()]
    if len(tree) != 14 or len(rand) != 27:
        refuse("generators gave %d and %d edges, not 14 and 27" % (len(tree), len(rand)))

    print("  parallelism: %d workers of %d logical CPUs; %d edges, two views each"
          % (WORKERS, os.cpu_count(), len(tree) + len(rand)))

    print("  CALIBRATION on tree edge %s" % (CAL["edge"],))
    cal = _one(("tree", tree, CAL["edge"]))
    d_std = abs(cal["standard"]["depth"] - CAL["expected"])
    d_thy = abs(cal["theory"]["depth"] - CAL["expected"])
    off = min(d_std, d_thy)
    print("      standard %.9f (off %.2e) | theory %.9f (off %.2e) | expected %.9f"
          % (cal["standard"]["depth"], d_std, cal["theory"]["depth"], d_thy, CAL["expected"]))
    calibrated = (d_std <= CAL["tol"]) or (d_thy <= CAL["tol"])
    if not calibrated:
        refuse("calibration missed by %.2e; this pipeline did not produce the published numbers "
               "and nothing computed with it may be reported" % off)

    jobs = [("tree", tree, e) for e in tree] + [("random", rand, e) for e in rand]
    t0 = time.time()
    with mp.Pool(WORKERS) as pool:
        rows = []
        for i, r in enumerate(pool.imap_unordered(_one, jobs), 1):
            rows.append(r)
            print("      %2d/%d  %-7s %-8s standard %+.6f at s=%.2f | theory %+.6f at s=%.2f  [%.0fs]"
                  % (i, len(jobs), r["graph"], tuple(r["edge"]), r["standard"]["depth"],
                     r["standard"]["valley_s"], r["theory"]["depth"], r["theory"]["valley_s"],
                     time.time() - t0))

    # CONTROL: the two views must differ somewhere, or the projection average is not averaging.
    diffs = [abs(r["standard"]["depth"] - r["theory"]["depth"]) for r in rows]
    if max(diffs) < 1e-9:
        refuse("standard and theory agree to machine precision on every edge, so the manifold "
               "average is collapsing to one state again and this run measures nothing")

    # CONTROL: the paper's orbit claim, checked on the tree.
    from networkx.algorithms.isomorphism import GraphMatcher
    G = nx.Graph(tree)
    auts = list(GraphMatcher(G, G).isomorphisms_iter())
    orbits = {}
    for u, v in G.edges():
        key = frozenset(frozenset((m[u], m[v])) for m in auts)
        orbits.setdefault(key, []).append(tuple(sorted((u, v))))
    by_edge = {tuple(r["edge"]): r for r in rows if r["graph"] == "tree"}
    orbit_report = []
    for members in orbits.values():
        if len(members) < 2:
            continue
        d = [by_edge[m]["theory"]["depth"] for m in members if m in by_edge]
        orbit_report.append({"members": [list(m) for m in members],
                             "theory_depths": d, "spread": max(d) - min(d)})
    worst = max((o["spread"] for o in orbit_report), default=0.0)

    neg = [r for r in rows if r["theory"]["depth"] < 0]
    print()
    print("  two views differ by up to %.6f, so the projection average is live" % max(diffs))
    print("  non-trivial tree orbits: %d, largest within-orbit theory spread %.3e"
          % (len(orbit_report), worst))
    print("  edges with NEGATIVE theory depth (ineligible under the E(0) baseline): %d  %s"
          % (len(neg), [tuple(r["edge"]) for r in neg]))

    json.dump({"script": os.path.basename(__file__),
               "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "networkx": nx.__version__, "grid": "linspace(%g,%g,%d)" % (GRID_LO, GRID_HI, GRID_N),
               "workers": WORKERS,
               "calibration": {"edge": list(CAL["edge"]), "expected": CAL["expected"],
                               "standard": cal["standard"], "theory": cal["theory"], "off_by": off},
               "rows": rows,
               "max_view_difference": max(diffs),
               "tree_orbits": orbit_report,
               "worst_within_orbit_spread": worst,
               "negative_theory_depth": [list(r["edge"]) for r in neg],
               "controls": {
                   "calibrated_before_anything_was_reported": True,
                   "two_views_proved_to_differ": True,
                   "orbit_claim_checked_not_assumed": True,
                   "signs_reported_so_ineligible_edges_are_visible": True,
               }},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
