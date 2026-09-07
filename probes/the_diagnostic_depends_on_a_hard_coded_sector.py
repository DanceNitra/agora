"""Does the paper's diagnostic depend on which magnetisation sector the script happens to fix?

WHY THIS EXISTS. `his_scan.py` hard-codes `N_up = 7`, which on 15 spins is the S_z = -1/2 sector. The
Hamiltonian is SU(2) symmetric, so when the ground multiplet has total spin S >= 1 there are several
sectors that all hold a ground state at the SAME energy. The diagnostic is the standard deviation of
the ZZ correlations taken from the ground-state probability distribution, and that is not invariant
across the members of a multiplet: a rank-two quantity takes different values on different m.

If the ground multiplet of a graph carries S >= 3/2, then the number the paper reports for that graph
is a property of one line in the script, not of the graph. The multi-seed audit cannot see this,
because every seed runs in the same fixed sector.

WHAT IS TESTED, on the graph where it would matter most: the random graph that carries the Table II
control row, on the edge the paper now uses.

  * the ground energies of the two sectors, at several s. If they agree, both sectors hold a ground
    state and the sector choice is arbitrary;
  * the diagnostic curve in each sector, and whether the paper's own valley detector finds a valley;
  * the tree, as a control. It is bipartite with 8 and 7 sites, so Lieb-Mattis gives S = 1/2, a
    doublet, and the two sectors are then NOT both ground: the second must lie strictly higher, and
    the sector choice cannot matter. A finding on the random graph with no matching null on the tree
    would be a finding about the solver.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EDITS = os.path.join(os.path.dirname(HERE), "agora_output", "edrn_guanghao_edits")
GRID = [0.0, 0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]


def machinery():
    src = io.open(os.path.join(EDITS, "his_scan.py"), encoding="utf-8").read()
    g = {}
    exec(compile(src[:src.index("s_values = np.linspace")], "his_scan", "exec"), g)  # noqa: S102
    return g


def measure(g, graph, edge, n_up, grid):
    """Ground energy and the paper's diagnostic at each s, in one fixed sector."""
    from scipy.sparse.linalg import eigsh
    edges = list(graph.edges())
    idx = [tuple(sorted(e)) for e in edges].index(tuple(sorted(edge)))
    _, edge_ops, zz_diags, H_base = g["prepare_sector_operators"](
        graph.number_of_nodes(), edges, n_up)
    rng = np.random.default_rng(7)
    v0 = rng.standard_normal(H_base.shape[0])
    energies, diag = [], []
    for s in grid:
        H = H_base + (float(s) - 1.0) * edge_ops[idx]
        vals, vecs = eigsh(H, k=1, which="SA", v0=v0, tol=1e-9, maxiter=5000)
        psi = vecs[:, 0]
        v0 = psi
        prob = np.abs(psi) ** 2
        energies.append(float(vals[0]))
        diag.append(float(np.std(np.array([np.dot(prob, zz) for zz in zz_diags]))))
    return energies, diag


def has_valley(grid, vals):
    i = int(np.argmin(vals))
    if i == 0 or i == len(vals) - 1:
        return None
    return float(grid[i]) if vals[i] < vals[i - 1] and vals[i] < vals[i + 1] else None


def main():
    if not os.path.exists(os.path.join(EDITS, "his_scan.py")):
        print("the paper's scan code is not here")
        return 2
    g = machinery()
    out = {"grid": GRID, "cases": {}}

    for name, builder, edge, sectors in (
            ("random N=15 (Table II control row)", "generate_random_N15", (7, 8), (7, 6)),
            ("tree N=15 (bipartite 8/7, S=1/2)", "generate_tree_N15", (2, 3), (7, 6))):
        if builder not in g:
            print("  %s: the generator %s is not in the scan code" % (name, builder))
            continue
        G = g[builder]()
        rec = {"edge": list(edge), "sectors": {}}
        print("\n  %s, edge %s" % (name, edge))
        for n_up in sectors:
            sz = (n_up - (G.number_of_nodes() - n_up)) / 2.0
            en, di = measure(g, G, edge, n_up, GRID)
            v = has_valley(GRID, di)
            rec["sectors"]["N_up=%d" % n_up] = {
                "S_z": sz, "energies": [round(e, 7) for e in en],
                "diagnostic": [round(d, 6) for d in di],
                "valley_s": v, "valley_depth": None if v is None else round(di[0] - min(di), 6)}
            print("    N_up=%d (S_z=%+.1f)  E(s=1.0)=%.7f  valley: %s"
                  % (n_up, sz, en[GRID.index(1.0)],
                     "none" if v is None else "s=%.2f depth=%.6f" % (v, di[0] - min(di))))
        a, b = (rec["sectors"]["N_up=%d" % n] for n in sectors)
        same = all(abs(x - y) < 1e-6 for x, y in zip(a["energies"], b["energies"]))
        rec["both_sectors_are_ground"] = bool(same)
        rec["valley_differs"] = (a["valley_s"] is None) != (b["valley_s"] is None) or (
            a["valley_s"] is not None and b["valley_s"] is not None
            and abs(a["valley_s"] - b["valley_s"]) > 1e-9)
        print("    both sectors hold a ground state: %s | the valley differs between them: %s"
              % (same, rec["valley_differs"]))
        out["cases"][name] = rec

    print()
    rnd = out["cases"].get("random N=15 (Table II control row)")
    tree = out["cases"].get("tree N=15 (bipartite 8/7, S=1/2)")
    if tree and tree["both_sectors_are_ground"]:
        print("  VOID: the tree's two sectors are degenerate too, which contradicts Lieb-Mattis for a "
              "bipartite 8/7 graph. The sector construction is wrong, so the random-graph result "
              "below says nothing.")
        out["verdict"] = "void"
    elif rnd and rnd["both_sectors_are_ground"] and rnd["valley_differs"]:
        print("  THE SECTOR DECIDES. On the random graph both sectors hold a ground state at the same "
              "energy, and the paper's valley exists in one and not the other. The reported number "
              "is a property of the `N_up = 7` line, not of the graph. The tree control behaves as "
              "Lieb-Mattis requires, so this is not an artefact of the construction.")
        out["verdict"] = "sector_dependent"
    elif rnd and not rnd["both_sectors_are_ground"]:
        print("  NOT REPRODUCED: the two sectors do not share a ground energy on the random graph, so "
              "the sector choice is forced and the diagnostic is well defined.")
        out["verdict"] = "not_reproduced"
    else:
        print("  NO DIFFERENCE: both sectors are ground and both give the same valley, so the choice "
              "does not change the published number here.")
        out["verdict"] = "no_difference"

    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("  receipt: %s" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
