"""Before telling him his control row is a reading artifact, reproduce the row.

WHY THIS EXISTS, and it is a red team finding about our own work. The companion probe,
the_control_graph_row_under_a_fresh_start_and_the_full_manifold.py, compares two arms and calls one
of them "as_published". It is not his procedure. It differs from his run in TWO ways at once: the
correlations are read from one eigenvector rather than the ground manifold, which is the change we
want to measure, AND every scan point starts from a fresh random vector rather than continuing from
the previous point's eigenvector, which is not.

The tell was already in our own numbers. That arm gives 0.0771 on every ring edge with a cross-seed
spread of exactly zero, while his ring row reports 0.0891 single-seed and 0.0993 +- 0.0286 over
three. A procedure that reproduced his could not have zero spread where his has 0.0286. So the
difference between the two arms cannot be attributed to the manifold, and the finding as drafted
was not safe to send.

WHAT THIS ARM IS. His settings as the paper and his scripts state them: the S_z = -1/2 sector alone
(N_up = 7), one eigenvector, k = 1, and a WARM START, each point continuing from the eigenvector the
previous point returned. Both grids are swept, because the manuscript says 13 points over s in [0,3]
and we established on 2026-09-03 that the tree and random scans actually used 61.

THE QUESTION IS BINARY. If 0.0891, 0.1050 or 0.0730 fall out of this arm on some edge, the
disagreement between our pipelines is explained and the manifold claim can be stated. If they do
not, the honest verdict is that our pipelines disagree for a reason neither of us has found, and no
claim about his table survives that.

CONTROLS:
  * THE TREE MUST STILL REPRODUCE 0.0750 at s = 1.70 on edge (2,3). It does in both existing arms.
    A warm start that broke it would mean this arm is broken rather than faithful.
  * A WARM START MUST ACTUALLY DIFFER from a fresh start somewhere, or the arm is a rename.
  * THE SEARCH FOR HIS NUMBERS IS TWO-SIDED: a value we DO hold, 0.0750, must be found by the same
    matcher that reports the others missing. A matcher that finds nothing finds nothing for a
    reason, and this says which.
"""
import io
import itertools
import json
import multiprocessing as mp
import os
import sys
import time

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import eigsh

try:
    import networkx as nx
except ImportError:                                   # pragma: no cover
    print("CANNOT RUN: networkx is not installed")
    raise SystemExit(2)

N = 15
N_UP = 7
SEEDS = (0, 1, 2)
GRIDS = {"13pt": np.linspace(0.0, 3.0, 13), "61pt": np.linspace(0.0, 3.0, 61)}
HIS_NUMBERS = {"ring_single": 0.0891, "ring_multi": 0.0993, "ring_spread": 0.0286,
               "tree": 0.0750, "random_single": 0.1050, "random_multi": 0.0730,
               "random_spread": 0.0548}
TOL = 0.005
RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"


def graphs():
    ring = [(i, (i + 1) % N) for i in range(N)]
    try:
        tree = sorted(tuple(sorted(e)) for e in nx.random_labeled_tree(N, seed=42).edges())
    except AttributeError:
        tree = sorted(tuple(sorted(e)) for e in nx.random_tree(N, seed=42).edges())
    rnd = sorted(tuple(sorted(e)) for e in nx.gnm_random_graph(N, 27, seed=42).edges())
    return {"ring": ring, "tree": tree, "random": rnd}


BASIS = list(itertools.combinations(range(N), N_UP))
INDEX = {st: i for i, st in enumerate(BASIS)}


def build(edges, J_vals):
    H = lil_matrix((len(BASIS), len(BASIS)), dtype=float)
    for (i, j), J in zip(edges, J_vals):
        for idx, st in enumerate(BASIS):
            H[idx, idx] += J * (1 if i in st else -1) * (1 if j in st else -1)
        for idx, st in enumerate(BASIS):
            iu, ju = i in st, j in st
            if iu and not ju:
                ns = list(st); ns.remove(i); ns.append(j)
                H[idx, INDEX[tuple(sorted(ns))]] += 2.0 * J
            elif ju and not iu:
                ns = list(st); ns.remove(j); ns.append(i)
                H[idx, INDEX[tuple(sorted(ns))]] += 2.0 * J
    return csr_matrix(H)


DIAG = None


def diags(edges):
    return np.array([[((1 if i in st else -1) * (1 if j in st else -1)) for st in BASIS]
                     for (i, j) in edges], dtype=float)


def scan_one(args):
    """One edge, one grid, one seed, WARM START: v0 is the previous point's eigenvector."""
    edges, e_idx, grid_name, seed = args
    grid = GRIDS[grid_name]
    D = diags(edges)
    rng = np.random.default_rng(seed)
    v0 = rng.standard_normal(len(BASIS))
    ys = []
    for s in grid:
        J = [1.0] * len(edges)
        J[e_idx] = float(s)
        H = build(edges, J)
        vals, vecs = eigsh(H, k=1, which="SA", v0=v0, maxiter=20000, tol=1e-9)
        psi = vecs[:, 0]
        v0 = psi                                       # the continuation his scripts use
        ys.append(float(np.std(D @ (np.abs(psi) ** 2))))
    y = np.array(ys)
    k = int(np.argmin(y))
    return (e_idx, grid_name, seed, float(grid[k]), float(y[0] - y[k]))


def main():
    started = time.time()
    gs = graphs()
    jobs = [(edges, i, gname, seed)
            for name, edges in gs.items()
            for i in range(len(edges))
            for gname in GRIDS
            for seed in SEEDS]
    print("scanning %d edge-grid-seed combinations" % len(jobs), flush=True)
    out_rows = {name: {} for name in gs}
    with mp.Pool(processes=min(12, os.cpu_count() or 4)) as pool:
        done = 0
        by_key = {}
        for name, edges in gs.items():
            sub = [j for j in jobs if j[0] == edges]
            for res in pool.imap_unordered(scan_one, sub):
                e_idx, gname, seed, pos, dep = res
                key = str(tuple(edges[e_idx]))
                by_key.setdefault((name, key, gname), {"valley_s": {}, "depth": {}})
                by_key[(name, key, gname)]["valley_s"][seed] = pos
                by_key[(name, key, gname)]["depth"][seed] = dep
                done += 1
                if done % 50 == 0:
                    print("  %d/%d  %.0fs" % (done, len(jobs), time.time() - started), flush=True)
    for (name, key, gname), v in by_key.items():
        deps = [v["depth"][s] for s in SEEDS]
        poss = [v["valley_s"][s] for s in SEEDS]
        out_rows[name].setdefault(key, {})[gname] = {
            "valley_s": poss, "depth": deps,
            "depth_single": deps[0], "depth_mean": float(np.mean(deps)),
            "depth_spread": float(np.std(deps)), "pos_spread": float(np.std(poss))}

    # Which of his numbers does this arm produce anywhere?
    found = {}
    for label, target in HIS_NUMBERS.items():
        hits = []
        for name, rows in out_rows.items():
            for key, grids in rows.items():
                for gname, v in grids.items():
                    for field in ("depth_single", "depth_mean", "depth_spread"):
                        if abs(v[field] - target) <= TOL:
                            hits.append([name, key, gname, field, round(v[field], 4)])
        found[label] = hits

    checks = []

    def check(nm, ok, got):
        checks.append({"check": nm, "pass": bool(ok), "got": got})

    tree_23 = out_rows["tree"].get("(2, 3)", {})
    tree_ok = any(abs(v["depth_single"] - 0.0750) <= 0.0005 and abs(v["valley_s"][0] - 1.70) < 1e-9
                  for v in tree_23.values())
    check("CONTROL_THE_TREE_STILL_REPRODUCES_0_0750_AT_s_1_70", tree_ok,
          "edge (2,3): %s" % {g: (round(v["depth_single"], 4), v["valley_s"][0])
                              for g, v in tree_23.items()})
    check("CONTROL_THE_MATCHER_FINDS_A_NUMBER_WE_DO_HOLD",
          len(found["tree"]) > 0,
          "%d hit(s) for 0.0750" % len(found["tree"]))
    ring_spread = max(v["depth_spread"] for v in
                      (g for row in out_rows["ring"].values() for g in row.values()))
    check("A_WARM_START_PRODUCES_A_CROSS_SEED_SPREAD_ON_THE_RING",
          ring_spread > 1e-6,
          "largest ring cross-seed depth spread under a warm start is %.4f, against 0.0000 under a "
          "fresh start and %.4f in his table" % (ring_spread, HIS_NUMBERS["ring_spread"]))
    reproduced = [k for k in ("ring_single", "random_single", "random_multi") if found[k]]
    check("HIS_PUBLISHED_DEPTHS_ARE_REPRODUCED_BY_HIS_OWN_SETTINGS",
          len(reproduced) == 3,
          "reproduced within %.3f: %s; not reproduced: %s"
          % (TOL, reproduced,
             [k for k in ("ring_single", "random_single", "random_multi") if not found[k]]))

    out = {
        "probe": os.path.basename(__file__),
        "arm": "his settings: N_up=7 only, k=1, warm start from the previous point's eigenvector",
        "grids": {k: [float(v[0]), float(v[-1]), len(v)] for k, v in GRIDS.items()},
        "seeds": list(SEEDS),
        "his_numbers": HIS_NUMBERS,
        "match_tolerance": TOL,
        "rows": out_rows,
        "where_his_numbers_appear": found,
        "checks": checks,
        "all_passed": all(c["pass"] for c in checks),
        "elapsed_s": round(time.time() - started, 1),
        "scope": (
            "Three N=15 control graphs, every edge, two grids over s in [0,3], three seeds, one "
            "magnetisation sector, one eigenvector, warm start. This asks only whether his "
            "published depths fall out of his own settings. It is not a claim about which reading "
            "is correct."),
    }
    with io.open(RESULT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps({"checks": checks, "all_passed": out["all_passed"],
                      "where_his_numbers_appear":
                          {k: len(v) for k, v in found.items()}}, indent=1))
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
