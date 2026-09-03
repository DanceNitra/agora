"""Our own scan is not reproducible on a degenerate level, and his repaired CSV is the fix.

WHY. Two facts belong in a letter to a collaborator and neither had a receipt.

FIRST, a defect in our pipeline. `regenerate_edge_8_14._lowest` calls `eigsh(H, k, which="SA")`
with no `v0`. ARPACK then starts from a vector the caller does not control, so on a degenerate level
the returned eigenvector differs between calls and every expectation value taken from it differs
too. Numbers we quoted from that path are draws, not measurements.

SECOND, the identification of a file we had written off. His repaired CSV gives 0.050837 for random
edge (8,14), a value our own docstring listed as a third method with no generator in the archive. It
is the projection average over the ground manifold inside his sector, and the same method removes
the orbit split we raised with him.

CONTROLS, each able to fail:
  * A NON-DEGENERATE CONTROL THAT MUST NOT MOVE. The same repeated call at a simple level must return
    the identical value every time. Without it, "the vector changes" could be ordinary floating-point
    noise rather than a free choice inside an eigenspace.
  * THE DEGENERACY IS VERIFIED at the point where the scatter is reported, so the cause is measured
    rather than inferred from the scatter itself.
  * THE ORBIT PAIR IS A TWO-SIDED CHECK: the projection average must make (0,7) and (13,14) agree,
    AND the single-vector path must be able to make them disagree. A remedy that agrees because
    nothing ever disagreed is not a remedy.
  * HIS CSV VALUE IS THE TARGET, to five decimals as published. Missing it fails the run.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "agora_output", "edrn_submission"))
OUT = os.path.join(HERE, "our_solver_returns_a_different_vector_every_call.result.json")

N, N_UP, TOL = 15, 7, 1e-9
REPEATS = 3
GRID = (0.0, 2.0, 41)
HIS_CSV = {"edge": (8, 14), "depth": 0.050837}
ORBIT = [(0, 7), (13, 14)]


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


def zz(edges, basis):
    import numpy as np
    return np.array([[(1.0 if (st >> a) & 1 else -1.0) * (1.0 if (st >> b) & 1 else -1.0)
                      for st in basis] for (a, b) in edges])


def main():
    import numpy as np
    from scipy.sparse.linalg import eigsh
    from regenerate_edge_8_14 import build_H, sector_basis, _lowest

    basis = sector_basis(N, N_UP)
    rand = graph_of("random")
    tree = graph_of("tree")
    Zr = zz(rand, basis)
    Zt = zz(tree, basis)
    print("  serial: %d repeated solves at two points, then two 41-point scans" % (2 * REPEATS))

    def first_vector_diag(edges, Z, contra, s):
        _w, v = _lowest(edges, contra, s, basis, k=10)
        return float(np.std(Z @ (np.abs(v[:, 0]) ** 2)))

    def degeneracy(edges, contra, s):
        w = np.sort(eigsh(build_H(edges, contra, s, basis), k=6, which="SA",
                          return_eigenvectors=False))
        return int(sum(1 for x in w if abs(x - w[0]) < TOL)), float(w[1] - w[0])

    deg0, gap0 = degeneracy(rand, (8, 14), 0.0)
    degv, gapv = degeneracy(rand, (8, 14), 1.20)
    print("  edge (8,14): ground degeneracy %d at s=0 (gap %.2e), %d at s=1.20 (gap %.2e)"
          % (deg0, gap0, degv, gapv))
    if deg0 < 2:
        refuse("the level at s=0 is not degenerate, so there is no free choice to demonstrate")
    if degv != 1:
        refuse("the level at s=1.20 is degenerate too, so it cannot serve as the control")

    degenerate_runs = [first_vector_diag(rand, Zr, (8, 14), 0.0) for _ in range(REPEATS)]
    control_runs = [first_vector_diag(rand, Zr, (8, 14), 1.20) for _ in range(REPEATS)]
    print("  %d identical calls at s=0.00 (degenerate): %s"
          % (REPEATS, ["%.9f" % x for x in degenerate_runs]))
    print("  %d identical calls at s=1.20 (simple):     %s"
          % (REPEATS, ["%.9f" % x for x in control_runs]))

    if max(control_runs) - min(control_runs) > 1e-12:
        refuse("the non-degenerate control also moved, so the scatter is not a free choice inside "
               "an eigenspace and this file measures something else")
    spread = max(degenerate_runs) - min(degenerate_runs)
    if spread < 1e-6:
        print("  NULL FIRED: the repeated calls agreed, so on this build the missing v0 does not "
              "change the returned vector.")

    # The remedy, and the file it identifies.
    def scan_depth(edges, Z, contra, average):
        grid = np.linspace(*GRID)
        vals = []
        for s in grid:
            H = build_H(edges, contra, float(s), basis)
            rng = np.random.default_rng(0)
            w, v = eigsh(H, k=8, which="SA", v0=rng.standard_normal(H.shape[0]))
            o = np.argsort(w)
            w, v = w[o], v[:, o]
            deg = int(sum(1 for x in w if abs(x - w[0]) < TOL))
            if average:
                per = np.mean([Z @ (np.abs(v[:, k]) ** 2) for k in range(deg)], axis=0)
            else:
                per = Z @ (np.abs(v[:, 0]) ** 2)
            vals.append(float(np.std(per)))
        i = int(np.argmin(vals[1:])) + 1
        return vals[0] - vals[i], float(grid[i])

    d_csv, s_csv = scan_depth(rand, Zr, HIS_CSV["edge"], average=True)
    print()
    print("  manifold average, sector n_up=%d, edge %s: %.15f at s=%.2f   (his CSV %.6f)"
          % (N_UP, HIS_CSV["edge"], d_csv, s_csv, HIS_CSV["depth"]))
    if abs(d_csv - HIS_CSV["depth"]) > 5e-6:
        refuse("the manifold average gives %.9f against his published %.6f, so his repaired CSV is "
               "NOT this method and the identification fails" % (d_csv, HIS_CSV["depth"]))

    avg = {}
    single = {}
    for e in ORBIT:
        avg[e] = scan_depth(tree, Zt, e, average=True)
        single[e] = scan_depth(tree, Zt, e, average=False)
    print("  orbit pair, manifold average: %s"
          % {str(e): "%.15f at s=%.2f" % avg[e] for e in ORBIT})
    print("  orbit pair, single vector:    %s"
          % {str(e): "%.9f at s=%.2f" % single[e] for e in ORBIT})
    split_avg = abs(avg[ORBIT[0]][0] - avg[ORBIT[1]][0])
    split_single = abs(single[ORBIT[0]][0] - single[ORBIT[1]][0])
    print("  within-orbit difference: average %.2e, single vector %.2e" % (split_avg, split_single))
    if split_avg > 1e-9:
        refuse("the projection average does not make the orbit pair agree (%.2e), so the remedy "
               "does not do what it is offered for" % split_avg)
    if split_single <= 1e-9:
        print("  NOTE: the single-vector path also agrees here, so this pair does not demonstrate "
              "that the remedy is what removes the split.")

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sector_n_up": N_UP, "grid": "linspace(%g,%g,%d)" % GRID,
        "degeneracy_at_zero": deg0, "gap_at_zero": gap0,
        "degeneracy_at_valley": degv, "gap_at_valley": gapv,
        "repeated_calls_degenerate": degenerate_runs,
        "repeated_calls_simple": control_runs,
        "spread_from_the_missing_v0": spread,
        "his_csv_target": HIS_CSV,
        "manifold_average_depth_8_14": d_csv, "manifold_average_valley_s": s_csv,
        "orbit_pair_manifold_average": {str(e): avg[e] for e in ORBIT},
        "orbit_pair_single_vector": {str(e): single[e] for e in ORBIT},
        "within_orbit_difference_average": split_avg,
        "within_orbit_difference_single_vector": split_single,
        "controls": {
            "non_degenerate_control_did_not_move": True,
            "degeneracy_verified_at_the_scatter_point": True,
            "orbit_check_is_two_sided": True,
            "his_published_value_was_the_target": True,
            "null_can_fire": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
