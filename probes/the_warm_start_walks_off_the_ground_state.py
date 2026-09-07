"""The scan's warm start leaves the ground state, and a random start does not.

WHAT THE SCAN DOES. `his_scan.scan_edge` sweeps the contradiction-edge weight s and solves for the
ground state at each point with `eigsh(H, k=1, which='SA', v0=v0, tol=1e-9, maxiter=2000)`, then sets
`v0 = psi` for the next point. That continuation is what makes the sweep fast. It is also what makes
it possible to follow a level that stops being the lowest one.

TWO THINGS ARE MEASURED HERE, on the random N=15 graph that carries the Table II control row.

1. WHETHER THE WARM START STAYS ON THE GROUND STATE. At s = 1.0 the contradiction edge has its
   nominal weight, so H is exactly the base Hamiltonian and the true ground energy can be obtained
   independently. The warm-started walk is compared against it.

2. WHETHER THE SECTOR IS FORCED. `prepare_sector_operators` fixes N_up = 7, the S_z = -1/2 sector.
   Each edge operator is the diagonal sigma^z sigma^z plus an off-diagonal flip of amplitude 2, which
   is 4 S_i . S_j, so H is SU(2) symmetric and the ground multiplet spans every |S_z| <= S. If the
   S_z = -3/2 sector holds the same ground energy, the multiplet has S >= 3/2, and the diagnostic --
   a standard deviation of ZZ correlations -- is not the same on every member of it.

THE CONTROLS:
  * the truth is established by DENSE diagonalisation, which has no starting vector and no tolerance;
  * a random start is run at the paper's own settings, k=1 and tol=1e-9, over several seeds. If that
    also missed the ground state, the finding would be about `eigsh` rather than about the warm start;
  * the tree is run as well. It is bipartite with 8 and 7 sites, so Lieb-Mattis gives S = 1/2 and the
    S_z = -3/2 sector must lie strictly higher. A tree that showed the same sector degeneracy would
    mean the sector construction is wrong.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EDITS = os.path.join(os.path.dirname(HERE), "agora_output", "edrn_guanghao_edits")
WALK = [0.0, 0.5, 1.0, 1.2, 1.5]
SEEDS = 5


def machinery():
    src = io.open(os.path.join(EDITS, "his_scan.py"), encoding="utf-8").read()
    g = {}
    exec(compile(src[:src.index("s_values = np.linspace")], "his_scan", "exec"), g)  # noqa: S102
    return g


def main():
    if not os.path.exists(os.path.join(EDITS, "his_scan.py")):
        print("the paper's scan code is not here")
        return 2
    from scipy.linalg import eigh
    from scipy.sparse.linalg import eigsh
    g = machinery()
    out = {"graphs": {}}

    for label, builder, edge in (("random N=15", "generate_random_N15", (7, 8)),
                                 ("tree N=15", "generate_tree_N15", (2, 3))):
        G = g[builder]()
        edges = list(G.edges())
        keys = [tuple(sorted(e)) for e in edges]
        idx = keys.index(tuple(sorted(edge)))
        rec = {"edge": list(edge), "sectors": {}}
        print("\n  %s, edge %s" % (label, edge))

        for n_up in (7, 6):
            _, ops, _, H0 = g["prepare_sector_operators"](15, edges, n_up)
            true_e = float(eigh(H0.toarray(), eigvals_only=True, subset_by_index=[0, 0])[0])
            rec["sectors"]["N_up=%d" % n_up] = {"S_z": (n_up - (15 - n_up)) / 2.0,
                                                "dense_ground_at_s1": round(true_e, 7)}
            print("    N_up=%d (S_z=%+.1f)  dense ground at s=1.0: %.7f"
                  % (n_up, (n_up - (15 - n_up)) / 2.0, true_e))
            if n_up != 7:
                continue

            fresh = []
            for sd in range(SEEDS):
                rng = np.random.default_rng(sd)
                w, _ = eigsh(H0, k=1, which="SA", v0=rng.standard_normal(H0.shape[0]),
                             tol=1e-9, maxiter=2000)
                fresh.append(float(w[0]))
            missed = sum(1 for x in fresh if abs(x - true_e) > 1e-6)
            print("      random start, the paper's settings: %d of %d seeds miss the ground state"
                  % (missed, SEEDS))

            rng = np.random.default_rng(7)
            v0 = rng.standard_normal(H0.shape[0])
            walk = []
            for s in WALK:
                w, v = eigsh(H0 + (s - 1.0) * ops[idx], k=1, which="SA", v0=v0,
                             tol=1e-9, maxiter=2000)
                v0 = v[:, 0]
                walk.append(float(w[0]))
            gap_at_1 = walk[WALK.index(1.0)] - true_e
            print("      warm-started walk at s=1.0: %.7f, which is %+.4f from the ground state"
                  % (walk[WALK.index(1.0)], gap_at_1))
            rec["random_start_misses"] = missed
            rec["warm_started_walk"] = [round(x, 7) for x in walk]
            rec["warm_start_error_at_s1"] = round(gap_at_1, 7)

        a = rec["sectors"]["N_up=7"]["dense_ground_at_s1"]
        b = rec["sectors"]["N_up=6"]["dense_ground_at_s1"]
        rec["multiplet_spans_both_sectors"] = bool(abs(a - b) < 1e-6)
        print("    the ground multiplet spans both sectors: %s"
              % rec["multiplet_spans_both_sectors"])
        out["graphs"][label] = rec

    rnd, tree = out["graphs"]["random N=15"], out["graphs"]["tree N=15"]
    print()
    if tree["multiplet_spans_both_sectors"]:
        print("  VOID: the tree's multiplet also spans both sectors, which Lieb-Mattis forbids for a "
              "bipartite 8/7 graph. The sector construction is wrong and nothing here holds.")
        out["verdict"] = "void"
    elif rnd["random_start_misses"] > 0:
        print("  VOID: a random start also misses the ground state in %d of %d seeds, so this is "
              "about the solver rather than about the warm start." % (rnd["random_start_misses"], SEEDS))
        out["verdict"] = "void"
    else:
        findings = []
        if abs(rnd["warm_start_error_at_s1"]) > 1e-6:
            findings.append("the warm-started walk sits %+.4f from the ground state at s=1.0, while a "
                            "random start finds it in %d of %d seeds"
                            % (rnd["warm_start_error_at_s1"], SEEDS, SEEDS))
        if rnd["multiplet_spans_both_sectors"]:
            findings.append("the ground multiplet spans S_z = -1/2 and -3/2, so it carries S >= 3/2 "
                            "and the diagnostic is not the same on every member of it")
        if findings:
            print("  ON THE RANDOM GRAPH: " + "; and ".join(findings) + ".")
            print("  The tree is clean on both counts, which is what Lieb-Mattis requires of it.")
            out["verdict"] = "random_graph_row_is_affected"
        else:
            print("  NOTHING FOUND: the warm start stays on the ground state and the sector is forced.")
            out["verdict"] = "clean"

    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("  receipt: %s" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
