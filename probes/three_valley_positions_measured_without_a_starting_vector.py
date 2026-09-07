"""Re-scan, with dense diagonalisation, the three tree edges whose valley sits against a degenerate
reference point. The paper tabulates those positions as measured.

WHY. Removing the contradiction edge e and diagonalising at s=0 gives the reference energy E(0), and
on four of this tree's fourteen edges that reference is DEGENERATE, which was reported to Guanghao as
a hazard for the DEPTH. Ranking the thirteen measured valley positions afterwards showed something
the depth story does not cover: the three degenerate-reference edges that have a valley hold the
three LOWEST positions of the thirteen, 0.05, 0.10 and 0.10 against 0.25 to 1.95 for the rest. That
is the most extreme arrangement available, two-sided p 0.0070.

Two readings fit that, and they call for opposite actions:

  ARTEFACT   the scan uses an iterative solver from a random start. Against a degenerate reference
             it can converge to a duplicate of the ground state, so the reported minimum hugs s=0
             and the position is an artefact of the solver.
  REAL       those cuts genuinely have their most coordinated point near s=0, and the position is
             physics that happens to coincide with the degeneracy.

A dense diagonalisation has no starting vector, so it separates them. This re-scans the affected
edges on the paper's own grid and reports whether the minimum moves.

THE CONTROLS:
  * the sector dimension and the s=0 degeneracy census must match `ground_truth.py`, or this is not
    the same Hamiltonian the paper used;
  * a NON-degenerate edge with a mid-range published position is re-scanned the same way. Dense and
    published must agree there, or a disagreement on the three says nothing about degeneracy and
    everything about a difference between the two toolchains;
  * every gap is reported, so a minimum sitting at the edge of the grid is visible rather than
    silently accepted.
"""
import io
import json
import os
import sys
import time

import numpy as np
from scipy.linalg import eigh

HERE = os.path.dirname(os.path.abspath(__file__))
EDITS = os.path.join(os.path.dirname(HERE), "agora_output", "edrn_guanghao_edits")

# The published positions, from the archive the paper's Table II was built from.
PUBLISHED = {(0, 7): 0.1000, (4, 8): 0.0500, (13, 14): 0.1000,        # degenerate reference
             (2, 3): 1.7000}                                          # the control: unique reference
DEGENERATE = {(0, 7), (4, 8), (13, 14)}


def load_scan_machinery():
    """The paper's own operators, taken from its own scan code rather than rebuilt."""
    src = io.open(os.path.join(EDITS, "his_scan.py"), encoding="utf-8").read()
    g = {}
    exec(compile(src[:src.index("s_values = np.linspace")], "his_scan", "exec"), g)  # noqa: S102
    G = g["generate_tree_N15"]()
    edges = [tuple(sorted(e)) for e in G.edges()]
    _, ops, _, H0 = g["prepare_sector_operators"](15, list(G.edges()), 7)
    return edges, ops, H0


def main():
    if not os.path.exists(os.path.join(EDITS, "his_scan.py")):
        print("the paper's scan code is not here, so there is nothing to re-scan against")
        return 2

    edges, ops, H0 = load_scan_machinery()
    dim = H0.shape[0]
    print("  sector dimension: %d" % dim)
    if dim != 6435:
        print("  the sector is not the published one (expected 6435), so this is a different "
              "Hamiltonian and nothing below is comparable")
        return 1

    # CONTROL: reproduce the s=0 degeneracy census.
    census = []
    for i, e in enumerate(edges):
        H = (H0 + (0.0 - 1.0) * ops[i]).toarray()
        w = eigh(H, eigvals_only=True, subset_by_index=[0, 1])
        if (w[1] - w[0]) < 1e-9:
            census.append(e)
    print("  control: %d of %d edges have a degenerate s=0 reference -> %s"
          % (len(census), len(edges), sorted(census)))
    if set(census) != DEGENERATE | {(5, 10)}:
        print("  the census does not match the published one (%s), so the machinery differs"
              % sorted(DEGENERATE | {(5, 10)}))
        return 1

    grid = np.linspace(0.0, 3.0, 61)
    out = {"sector_dimension": dim, "grid_points": len(grid), "edges": {}}
    for e in sorted(PUBLISHED):
        i = edges.index(e)
        t0 = time.time()
        gaps = []
        for k, s in enumerate(grid):
            H = (H0 + (s - 1.0) * ops[i]).toarray()
            w = eigh(H, eigvals_only=True, subset_by_index=[0, 1])
            gaps.append(float(w[1] - w[0]))
            if k % 15 == 0:
                print("    %-8s %2d/%d  s=%.2f  gap=%.6f  (%.0fs)"
                      % (str(e), k + 1, len(grid), s, gaps[-1], time.time() - t0))
        j = int(np.argmin(gaps))
        s_dense = float(grid[j])
        rec = {"published_position": PUBLISHED[e], "dense_position": s_dense,
               "dense_min_gap": gaps[j], "gap_at_s0": gaps[0],
               "degenerate_reference": e in DEGENERATE,
               "minimum_at_grid_edge": bool(j in (0, len(grid) - 1)),
               "moved": abs(s_dense - PUBLISHED[e]) > 0.051,
               "gaps": [round(x, 9) for x in gaps]}
        out["edges"][str(e)] = rec
        print("  %-8s published %.4f  dense %.4f  %s%s"
              % (str(e), PUBLISHED[e], s_dense, "MOVED" if rec["moved"] else "agrees",
                 "  <- at the edge of the grid" if rec["minimum_at_grid_edge"] else ""))

    ctrl = out["edges"]["(2, 3)"]
    moved = [e for e, r in out["edges"].items() if r["degenerate_reference"] and r["moved"]]
    print()
    if ctrl["moved"]:
        print("  VOID: the non-degenerate control (2, 3) also moved, from %.4f to %.4f. The dense "
              "scan and the published scan disagree for a reason that has nothing to do with "
              "degeneracy, so nothing here is attributable to it."
              % (ctrl["published_position"], ctrl["dense_position"]))
    elif moved:
        print("  ARTEFACT: the control agrees at %.4f, and %d of the %d degenerate-reference edges "
              "move under dense diagonalisation: %s. Those Table II positions are a property of the "
              "solver's starting vector, not of the graph."
              % (ctrl["dense_position"], len(moved), len(DEGENERATE), moved))
    else:
        print("  REAL: the control agrees and every degenerate-reference edge keeps its position "
              "under dense diagonalisation. Those valleys genuinely sit near s=0, and the clustering "
              "is a fact about those cuts rather than about the solver.")
    out["verdict"] = {"control_moved": ctrl["moved"], "degenerate_edges_that_moved": moved}

    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("  receipt: %s" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
