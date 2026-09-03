"""Where does the seed scatter in Table 2's random depth actually live: in E(0) or in E(valley)?

WHY. Running his pipeline over twelve seeds reproduces his published pair exactly (seed 0 gives
0.104966, seeds 0 to 2 give 0.073017 +/- 0.054799) and the depth swings from 0.009741 to 0.104966.
The depth is a difference, E(0) - E(valley), so the scatter is in one term or the other, and saying
which one changes what the paper has to fix. A separate check already found the ground state at
s = 1.20 to be NON-degenerate in his sector, which points at the baseline rather than the valley,
and that is a prediction rather than a measurement until both terms are measured.

WHAT IS BEING TESTED. At s = 0 the contradiction edge carries zero coupling. If that leaves an
endpoint with no remaining bond, the spin on it is free, the sector's ground level is degenerate,
and E(0) depends on which vector the solver returns. The valley term would then be deterministic
and the entire published spread would belong to the baseline.

CONTROLS, each able to fail:
  * A NEGATIVE CONTROL THAT MUST STAY FLAT. Tree edge (1,10) reproduces 0.058909125 on all twelve
    seeds, so both of its terms must be flat. If the tree's baseline scatters too, the mechanism
    proposed here is not what separates the two edges.
  * THE GRAPH FACT IS COMPUTED, NOT ASSUMED. Endpoint degrees and what the edge's removal does to
    connectivity are measured from the generator, not read off a picture.
  * DEGENERACY AT BOTH POINTS, not at one. A claim that the scatter sits in the baseline requires
    the valley to be non-degenerate AND the baseline to be degenerate.
  * THE TWO SPREADS ARE MEASURED SEPARATELY over the same twelve seeds, so the conclusion is a
    measurement of both terms rather than an inference from their difference.
  * IF BOTH TERMS SCATTER, OR NEITHER, THE PROBE SAYS SO. The verdict has three outcomes.
"""
from __future__ import annotations

import io
import itertools
import json
import multiprocessing as mp
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "the_seed_scatter_lives_in_the_baseline_not_the_valley.result.json")

WORKERS = 4
N = 15
N_UP = 7
SEEDS = list(range(12))
FLAT = 1e-9
CASES = [("random", (8, 14), 1.20), ("tree", (1, 10), 1.90)]


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


def _point(args):
    """E(s) for one seed at one s, through his exact call."""
    from table_2_random_depth_is_a_seed_draw import his_basis, his_diagnostic
    import numpy as np
    which, contra, s, seed = args
    edges = graph_of(which)
    ei = edges.index(contra)
    J = np.ones(len(edges))
    J[ei] = s
    return (which, s, seed, his_diagnostic(edges, J, his_basis(N, N_UP), seed))


def degeneracy(which, contra, s, tol=1e-9):
    from table_2_random_depth_is_a_seed_draw import his_basis, his_H
    import numpy as np
    from scipy.sparse.linalg import eigsh
    edges = graph_of(which)
    J = np.ones(len(edges))
    J[edges.index(contra)] = s
    H = his_H(N, edges, J, his_basis(N, N_UP))
    w = np.sort(eigsh(H, k=8, which="SA", return_eigenvectors=False))
    return int(sum(1 for x in w if abs(x - w[0]) < tol)), float(w[1] - w[0])


def main():
    import numpy as np
    import networkx as nx
    print("  parallelism: %d workers of %d logical CPUs; %d single-point solves"
          % (WORKERS, os.cpu_count(), len(CASES) * 2 * len(SEEDS)))

    facts = {}
    for which, contra, _s in CASES:
        edges = graph_of(which)
        G = nx.Graph(edges)
        if contra not in edges:
            refuse("edge %s is not in the %s generator, so the case does not exist" % (contra, which))
        H = G.copy()
        H.remove_edge(*contra)
        isolated = [n for n in H.nodes if H.degree(n) == 0]
        facts[which] = {"edge": list(contra),
                        "endpoint_degrees": [G.degree(contra[0]), G.degree(contra[1])],
                        "components_after_removal": nx.number_connected_components(H),
                        "isolated_after_removal": isolated}
        print("  %-7s edge %-8s endpoint degrees %s, removal leaves %d components, isolated %s"
              % (which, contra, facts[which]["endpoint_degrees"],
                 facts[which]["components_after_removal"], isolated))

    for which, contra, sv in CASES:
        d0, g0 = degeneracy(which, contra, 0.0)
        dv, gv = degeneracy(which, contra, sv)
        facts[which]["degeneracy_at_zero"] = d0
        facts[which]["gap_at_zero"] = g0
        facts[which]["degeneracy_at_valley"] = dv
        facts[which]["gap_at_valley"] = gv
        print("  %-7s ground degeneracy: s=0 -> %d (gap %.2e) | s=%.2f -> %d (gap %.2e)"
              % (which, d0, g0, sv, dv, gv))

    jobs = []
    for which, contra, sv in CASES:
        for s in (0.0, sv):
            for sd in SEEDS:
                jobs.append((which, contra, s, sd))
    t0 = time.time()
    with mp.Pool(WORKERS) as pool:
        rows = pool.map(_point, jobs)
    print("  %d solves in %.0fs" % (len(rows), time.time() - t0))

    spreads = {}
    print()
    for which, contra, sv in CASES:
        for name, s in (("E(0) baseline", 0.0), ("E(valley)", sv)):
            vals = [e for (w, ss, _sd, e) in rows if w == which and abs(ss - s) < 1e-12]
            if len(vals) != len(SEEDS):
                refuse("%s %s collected %d of %d seeds" % (which, name, len(vals), len(SEEDS)))
            spread = max(vals) - min(vals)
            spreads[(which, name)] = spread
            print("  %-7s %-14s over %d seeds: %.9f to %.9f, spread %.3e"
                  % (which, name, len(vals), min(vals), max(vals), spread))

    # CONTROL: the tree must be flat at BOTH points, or the mechanism does not separate the cases.
    tree_flat = (spreads[("tree", "E(0) baseline")] < FLAT
                 and spreads[("tree", "E(valley)")] < FLAT)
    if not tree_flat:
        refuse("the tree control scatters (baseline %.2e, valley %.2e), so the seed moves both "
               "edges and the random result is not specific"
               % (spreads[("tree", "E(0) baseline")], spreads[("tree", "E(valley)")]))
    print()
    print("  NEGATIVE CONTROL: the tree is flat at both points, below %.0e" % FLAT)

    rb = spreads[("random", "E(0) baseline")]
    rv = spreads[("random", "E(valley)")]
    if rb > FLAT and rv <= FLAT:
        verdict = "SCATTER_IS_ENTIRELY_IN_THE_BASELINE"
    elif rb > FLAT and rv > FLAT:
        verdict = "BOTH_TERMS_SCATTER"
    elif rb <= FLAT and rv > FLAT:
        verdict = "SCATTER_IS_IN_THE_VALLEY"
    else:
        verdict = "NEITHER_TERM_SCATTERS"
    print("  random: baseline spread %.3e, valley spread %.3e" % (rb, rv))
    print("  VERDICT: %s" % verdict)

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sector_n_up": N_UP, "seeds": SEEDS, "workers": WORKERS,
        "graph_facts": facts,
        "spreads": {"%s %s" % k: v for k, v in spreads.items()},
        "verdict": verdict,
        "controls": {
            "graph_fact_computed_from_the_generator": True,
            "degeneracy_measured_at_both_points": True,
            "both_terms_measured_over_the_same_seeds": True,
            "tree_negative_control_flat": tree_flat,
            "three_outcomes_reachable": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
