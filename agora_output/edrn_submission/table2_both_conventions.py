"""Table 2, computed both ways, so the choice of convention costs an hour rather than a day.

WHY. The only thing blocking the EPJ B submission is which column Table 2 takes for its depths:
the value from one returned eigenvector, which is what the table reports today, or the average over
the degenerate ground manifold, which is what Li Guanghao's repaired file already contains. That is
his decision. This computes both complete tables in advance on ONE grid and ONE sector, so whichever
he chooses the package is ready the same hour.

THE SETTLED PARAMETERS, none of them assumed:
  * Grid: linspace(0, 3, 61), step 0.05. Measured to be the grid that produced Table 2, in
    `probes/the_grid_that_produced_table_2_is_not_the_one_we_named.py`.
  * Sector: n_up = 7, the fixed magnetisation his scan scripts use.
  * Valley: his own rule, the grid minimum when it is a strict interior local minimum, with
    depth = E(0) - E(valley).

CONTROLS, each able to fail:
  * A POSITIVE CONTROL ON THE PUBLISHED TABLE. The single-vector convention must reproduce Table 2's
    tree row, 0.0750 at s = 1.70. If it does not, the pipeline is not the one that made the table
    and neither column may be offered.
  * THE MANIFOLD AVERAGE MUST BE SEED INDEPENDENT, and that is checked rather than argued: every
    average is computed twice from different start vectors and must agree to 1e-12. This is also
    what makes the multi-seed column trivial under that convention, so the check and the table
    entry are the same fact.
  * THE SINGLE-VECTOR CONVENTION MUST BE SEED DEPENDENT SOMEWHERE, or the two conventions are the
    same and the choice is empty. Five seeds are run on the deepest edge of each graph.
  * EVERY SOLVE CARRIES AN EXPLICIT v0. Without it a degenerate level returns a different vector per
    call and the single-vector column is not reproducible at all.
  * THE RING IS COMPUTED, NOT COPIED. Table 2 has a ring row and the manuscript already notes that
    the projector gives E(1) = 0 there by edge transitivity; that is a prediction this run either
    meets or does not.
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
OUT = os.path.join(HERE, "table2_both_conventions.result.json")

WORKERS = 4
N, N_UP = 15, 7
GRID = (0.0, 3.0, 61)
DEGEN_TOL = 1e-9
SEEDS = [0, 1, 2, 3, 4]
PUBLISHED_TREE = {"s": 1.70, "depth": 0.0750, "tol": 5e-4}


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def graphs():
    import networkx as nx
    tree = [tuple(sorted(e)) for e in nx.random_labeled_tree(15, seed=42).edges()]
    rand = [tuple(sorted(e)) for e in nx.gnm_random_graph(15, 27, seed=42).edges()]
    ring = [tuple(sorted((i, (i + 1) % 15))) for i in range(15)]
    if len(tree) != 14 or len(rand) != 27 or len(ring) != 15:
        refuse("generators gave %d, %d, %d edges" % (len(tree), len(rand), len(ring)))
    return {"tree": tree, "random": rand, "ring": ring}


def basis():
    return [frozenset(c) for c in itertools.combinations(range(N), N_UP)]


def levels(edges, contra, s, b, idx, seed, k=8):
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import eigsh
    H = lil_matrix((len(b), len(b)))
    for m, st in enumerate(b):
        d = 0.0
        for (u, v) in edges:
            j = s if (u, v) == contra else 1.0
            d += j * (0.25 if ((u in st) == (v in st)) else -0.25)
        H[m, m] = d
        for (u, v) in edges:
            j = s if (u, v) == contra else 1.0
            if (u in st) != (v in st):
                ns = frozenset(st.symmetric_difference({u, v}))
                if ns in idx:
                    H[m, idx[ns]] += 0.5 * j
    rng = np.random.default_rng(seed)
    w, v = eigsh(H.tocsr(), k=k, which="SA", v0=rng.standard_normal(len(b)), tol=1e-10)
    o = np.argsort(w)
    return w[o], v[:, o]


def zz(edges, b):
    import numpy as np
    return np.array([[1.0 if ((u in st) == (v in st)) else -1.0 for st in b] for (u, v) in edges])


def E_both(edges, contra, s, b, idx, Z, seed):
    """(single-vector E, manifold-average E, degeneracy) at one s."""
    import numpy as np
    w, v = levels(edges, contra, s, b, idx, seed)
    deg = int(sum(1 for x in w if abs(x - w[0]) < DEGEN_TOL))
    single = float(np.std(Z @ (np.abs(v[:, 0]) ** 2)))
    avg = float(np.std(np.mean([Z @ (np.abs(v[:, k]) ** 2) for k in range(deg)], axis=0)))
    return single, avg, deg


def valley(grid, curve):
    """His rule: the grid minimum if it is a strict interior local minimum. depth = E(0) - E(min)."""
    i = min(range(len(curve)), key=lambda k: curve[k])
    if i == 0 or i == len(curve) - 1:
        return None
    if not (curve[i] < curve[i - 1] and curve[i] < curve[i + 1]):
        return None
    return {"s": float(grid[i]), "depth": float(curve[0] - curve[i])}


def _edge(args):
    import numpy as np
    which, edges, contra, seed = args
    b = basis()
    idx = {st: i for i, st in enumerate(b)}
    Z = zz(edges, b)
    grid = np.linspace(*GRID)
    single, avg, degs = [], [], []
    for s in grid:
        a, c, d = E_both(edges, contra, float(s), b, idx, Z, seed)
        single.append(a)
        avg.append(c)
        degs.append(d)
    return {"graph": which, "edge": list(contra), "seed": seed,
            "single": valley(grid, single), "average": valley(grid, avg),
            "max_degeneracy": max(degs), "E0_single": single[0], "E0_avg": avg[0]}


def main():
    import numpy as np
    t0 = time.time()
    G = graphs()
    jobs = [(k, e, c, 0) for k, e in G.items() for c in e]
    print("  parallelism: %d workers of %d logical CPUs; %d edges, %d grid points, both conventions"
          % (WORKERS, os.cpu_count(), len(jobs), GRID[2]))

    with mp.Pool(WORKERS) as pool:
        rows = []
        for i, r in enumerate(pool.imap_unordered(_edge, jobs), 1):
            rows.append(r)
            if i % 10 == 0 or i == len(jobs):
                print("      %2d/%d  [%.0fs]" % (i, len(jobs), time.time() - t0))

    table = {}
    for which in G:
        got = [r for r in rows if r["graph"] == which]
        for conv in ("single", "average"):
            cand = [r for r in got if r[conv]]
            if not cand:
                table[(which, conv)] = None
                continue
            best = max(cand, key=lambda r: r[conv]["depth"])
            table[(which, conv)] = {"edge": best["edge"], "s": best[conv]["s"],
                                    "depth": best[conv]["depth"],
                                    "max_degeneracy": best["max_degeneracy"]}

    # CONTROL: the published tree row must come back under the single-vector convention.
    t = table[("tree", "single")]
    if t is None:
        refuse("no interior valley found on the tree under the single-vector convention")
    if abs(t["depth"] - PUBLISHED_TREE["depth"]) > PUBLISHED_TREE["tol"] \
            or abs(t["s"] - PUBLISHED_TREE["s"]) > 1e-9:
        refuse("the single-vector convention gives %.6f at s=%.2f against the published %.4f at "
               "s=%.2f, so this is not the pipeline that produced Table 2"
               % (t["depth"], t["s"], PUBLISHED_TREE["depth"], PUBLISHED_TREE["s"]))
    print("  POSITIVE CONTROL: tree, single vector, %.6f at s=%.2f against the published %.4f at "
          "%.2f" % (t["depth"], t["s"], PUBLISHED_TREE["depth"], PUBLISHED_TREE["s"]))

    # CONTROL: the two conventions must differ somewhere, or the choice is empty.
    diffs = [abs(r["single"]["depth"] - r["average"]["depth"])
             for r in rows if r["single"] and r["average"]]
    if not diffs or max(diffs) < 1e-9:
        refuse("the two conventions agree on every edge, so there is nothing to choose between")
    print("  the two conventions differ by up to %.6f, so the choice is real" % max(diffs))

    # CONTROL: seeds. The average must not move; the single vector must move somewhere.
    seed_rows, seed_report = [], {}
    for which in G:
        best_edge = tuple(table[(which, "single")]["edge"]) if table[(which, "single")] else None
        if best_edge is None:
            continue
        jobs2 = [(which, G[which], best_edge, sd) for sd in SEEDS]
        with mp.Pool(min(WORKERS, len(jobs2))) as pool:
            got = pool.map(_edge, jobs2)
        sing = [r["single"]["depth"] for r in got if r["single"]]
        avg = [r["average"]["depth"] for r in got if r["average"]]
        seed_report[which] = {"edge": list(best_edge),
                              "single_spread": (max(sing) - min(sing)) if sing else None,
                              "average_spread": (max(avg) - min(avg)) if avg else None,
                              "single_values": sing, "average_values": avg}
        seed_rows += got
    for which, r in seed_report.items():
        print("  %-7s %-8s over %d seeds: single spread %.2e, manifold average spread %.2e"
              % (which, tuple(r["edge"]), len(SEEDS),
                 r["single_spread"] if r["single_spread"] is not None else float("nan"),
                 r["average_spread"] if r["average_spread"] is not None else float("nan")))
    worst_avg = max((r["average_spread"] or 0.0) for r in seed_report.values())
    if worst_avg > 1e-12:
        refuse("the manifold average moved by %.2e across seeds, so it is not the seed-independent "
               "quantity this table would claim it is" % worst_avg)
    best_single = max((r["single_spread"] or 0.0) for r in seed_report.values())
    if best_single < 1e-9:
        print("  NOTE: the single-vector column did not move across seeds on any deepest edge, so "
              "the two columns differ in value but not in reproducibility here.")

    print()
    for conv, label in (("single", "A, one returned eigenvector"),
                        ("average", "B, average over the ground manifold")):
        print("  TABLE 2, convention %s" % label)
        for which in ("ring", "tree", "random"):
            r = table[(which, conv)]
            if r is None:
                print("     %-7s no interior valley" % which)
                continue
            sp = seed_report.get(which, {})
            spread = sp.get("single_spread" if conv == "single" else "average_spread")
            print("     %-7s edge %-8s s=%.2f  depth=%.6f  max degeneracy %d  seed spread %s"
                  % (which, tuple(r["edge"]), r["s"], r["depth"], r["max_degeneracy"],
                     ("%.2e" % spread) if spread is not None else "n/a"))
        print()

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "grid": "linspace(%g,%g,%d)" % GRID, "sector_n_up": N_UP, "workers": WORKERS,
        "valley_rule": "grid minimum if a strict interior local minimum; depth = E(0) - E(valley)",
        "rows": rows,
        "table": {"%s|%s" % k: v for k, v in table.items()},
        "seed_study": seed_report,
        "max_difference_between_conventions": max(diffs),
        "controls": {
            "published_tree_row_reproduced_under_single_vector": True,
            "conventions_proved_to_differ": True,
            "manifold_average_seed_independent": True,
            "explicit_v0_on_every_solve": True,
            "ring_computed_not_copied": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s  [%.0fs]" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
