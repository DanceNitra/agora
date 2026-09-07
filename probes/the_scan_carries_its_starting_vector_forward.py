"""Does the published valley position survive when the scan stops warm-starting from s=0?

WHAT THE SCAN ACTUALLY MEASURES, because the first attempt at this got it wrong. The diagnostic is
not an energy and not a gap. `his_scan.scan_edge` takes the ground-state vector at each s, forms the
probability distribution, contracts it with each edge's ZZ operator, and reports the STANDARD
DEVIATION of those edge correlations. The valley is an interior minimum of that curve, and the depth
is the value at s=0 minus the value at the minimum.

A previous probe minimised the gap instead and its non-degenerate control moved to the edge of the
grid, which is how the error was caught. The receipt of that void run is kept beside this one.

WHY THE DEGENERACY REACHES THE POSITION. Because the diagnostic depends on the VECTOR, not on the
eigenvalue, a degenerate ground manifold makes it ill-defined: every solver returns an arbitrary
member of the manifold, dense diagonalisation included. `scan_edge` then does something that turns
that into a curve-wide effect: it warm-starts each point from the previous one, `v0 = psi`. So an
arbitrary vector picked at s=0, where four of this tree's edges have a degenerate reference, is
carried forward into every later point.

THE TEST. The same curve computed two ways, on the same grid, with the same solver:

  continued    v0 = psi from the previous s, which is what the paper's scan does
  independent  a fresh random v0 at every s, so nothing propagates

If the published positions are a property of the graph, the two agree. If they are a property of the
starting vector, the independent runs disagree with them and with each other.

THE CONTROLS:
  * (2,3) has a unique s=0 reference and a published position of 1.70. Both methods must agree there,
    or a disagreement on the affected edges says nothing about degeneracy;
  * the continued arm must reproduce the published positions, or this is not the paper's scan;
  * several seeds per arm, because a single run cannot show a spread.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EDITS = os.path.join(os.path.dirname(HERE), "agora_output", "edrn_guanghao_edits")

PUBLISHED = {(0, 7): 0.1000, (4, 8): 0.0500, (13, 14): 0.1000, (2, 3): 1.7000}
DEGENERATE = {(0, 7), (4, 8), (13, 14)}
SEEDS = 5


def load():
    src = io.open(os.path.join(EDITS, "his_scan.py"), encoding="utf-8").read()
    g = {}
    exec(compile(src[:src.index("s_values = np.linspace")], "his_scan", "exec"), g)  # noqa: S102
    G = g["generate_tree_N15"]()
    edges = list(G.edges())
    prepared = g["prepare_sector_operators"](15, edges, 7)
    return g, [tuple(sorted(e)) for e in edges], prepared


def curve(prepared, idx, grid, seed, continued):
    """The paper's diagnostic at every s. `continued` reproduces its warm start."""
    from scipy.sparse.linalg import eigsh
    _, edge_ops, zz_diags, H_base = prepared
    rng = np.random.default_rng(seed)
    v0 = rng.standard_normal(H_base.shape[0])
    out = []
    for s in grid:
        H = H_base + (float(s) - 1.0) * edge_ops[idx]
        _, evecs = eigsh(H, k=1, which="SA", v0=v0, tol=1e-9, maxiter=2000)
        psi = evecs[:, 0]
        if continued:
            v0 = psi
        else:
            v0 = rng.standard_normal(H_base.shape[0])
        prob = np.abs(psi) ** 2
        out.append(float(np.std(np.array([np.dot(prob, zz) for zz in zz_diags]))))
    return np.array(out)


def interior_min(grid, vals):
    """The paper's own detector: an interior minimum, or nothing."""
    i = int(np.argmin(vals))
    if i == 0 or i == len(vals) - 1:
        return None
    if vals[i] < vals[i - 1] and vals[i] < vals[i + 1]:
        return float(grid[i])
    return None


def main():
    if not os.path.exists(os.path.join(EDITS, "his_scan.py")):
        print("the paper's scan code is not here")
        return 2
    _, edges, prepared = load()
    grid = np.linspace(0.0, 3.0, 61)
    print("  sector dimension %d, %d grid points, %d seeds per arm"
          % (prepared[3].shape[0], len(grid), SEEDS))

    out = {"grid_points": len(grid), "seeds": SEEDS, "edges": {}}
    for e in sorted(PUBLISHED):
        idx = edges.index(e)
        rec = {"published": PUBLISHED[e], "degenerate_reference": e in DEGENERATE}
        for arm, cont in (("continued", True), ("independent", False)):
            pos = []
            for sd in range(SEEDS):
                pos.append(interior_min(grid, curve(prepared, idx, grid, 1000 + sd, cont)))
                print("    %-9s %-12s seed %d -> %s"
                      % (str(e), arm, sd, "none" if pos[-1] is None else "%.4f" % pos[-1]))
            found = [p for p in pos if p is not None]
            rec[arm] = {"positions": pos, "distinct": sorted(set(found)),
                        "agrees_with_published": bool(found)
                        and all(abs(p - PUBLISHED[e]) < 0.051 for p in found),
                        "no_valley_in": pos.count(None)}
        out["edges"][str(e)] = rec

    ctrl = out["edges"]["(2, 3)"]
    print()
    if not ctrl["continued"]["agrees_with_published"]:
        print("  VOID: the continued arm does not reproduce the published position on the control "
              "(2,3): %s against %.4f. This is not the paper's scan, so nothing below holds."
              % (ctrl["continued"]["distinct"], ctrl["published"]))
        verdict = "void"
    elif not ctrl["independent"]["agrees_with_published"]:
        print("  VOID: removing the warm start moves the NON-degenerate control too (%s against "
              "%.4f), so the effect is not about degeneracy."
              % (ctrl["independent"]["distinct"], ctrl["published"]))
        verdict = "void"
    else:
        moved = [e for e, r in out["edges"].items()
                 if r["degenerate_reference"] and not r["independent"]["agrees_with_published"]]
        if moved:
            print("  THE STARTING VECTOR CARRIES. The control holds its position under both arms. "
                  "%d of the %d degenerate-reference edges do not: %s. Those published positions "
                  "are a property of the vector the solver was handed at s=0, not of the graph."
                  % (len(moved), len(DEGENERATE), moved))
            verdict = "position_is_an_artefact"
        else:
            print("  THE POSITIONS HOLD. Removing the warm start changes nothing on any edge, so "
                  "the degenerate reference reaches the depth and not the position.")
            verdict = "position_is_real"
    out["verdict"] = verdict

    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("  receipt: %s" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
