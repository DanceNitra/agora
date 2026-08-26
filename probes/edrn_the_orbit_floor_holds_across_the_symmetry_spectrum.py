"""E(s=1) is a between-orbit quantity on every graph, not a coincidence of the four we had.

WHY THIS EXISTS. On 2026-08-23 we sent @luoxuejian000 the mechanism his manuscript listed as open:
at the uniform point the contradiction edge carries J = 1 like every other bond, so H(s=1) is the
plain Heisenberg Hamiltonian on the graph, E(1) cannot know which edge was labelled, and on a
symmetry-carrying ground state the within-orbit part of the correlation dispersion vanishes, leaving
E(1) as a pure between-orbit floor -- a property of Aut(G).

He has now written that the paper's single central message is "the reproducible non-monotonic valley
and its orbit-resolved mechanism", and the manuscript is with Chinese Physics Letters. So the claim
carrying the paper is the one we supplied on FOUR graphs. Four cases is an observation. A referee
will ask whether it is a theorem, and that is the right question.

THE CLAIM, stated so it can fail:

    Let rho be the projector onto the ground manifold at s = 1, divided by its degeneracy, and let
    c_e = Tr(rho S^z_a S^z_b) for edge e = (a,b). Then edges in the same Aut(G)-orbit carry EQUAL
    c_e, so Var(c) is entirely between-orbit, and E(1) = sqrt(Var_between).

It is not an empirical regularity, and saying so is the point. Every automorphism commutes with
H(s=1), so it permutes the ground eigenspace and commutes with its projector; rho is therefore
exactly Aut-invariant even when no single eigenvector is. That is why the MANIFOLD AVERAGE is the
right object and a single Lanczos vector is not: one vector picks an arbitrary point of a degenerate
manifold and breaks the symmetry that the manifold itself keeps. The ring is the sharpest case --
edge-transitive means ONE orbit, so Var_between = 0 and E(1) = 0 exactly.

THREE CONTROLS, because a within-orbit variance of zero is easy to produce by accident:

  1. VACUITY. On a graph with trivial Aut every orbit has size one, so within-orbit variance is zero
     by construction and the graph proves nothing. Those rows are measured, reported, and EXCLUDED
     from the evidence set, which is stated in the receipt rather than left for a reader to notice.

  2. THE PARTITION CONTROL, which is the one that can actually fail. Shuffle the edges into random
     blocks of exactly the same sizes as the real orbits. If within-block variance vanishes there
     too, then all correlations are simply equal and the orbit structure explains nothing. The real
     partition has to be special, not merely a partition.

  3. THE INSTRUMENT RESPONDS. Weaken one bond and H no longer carries Aut(G), so the within-orbit
     dispersion measured against the SAME orbits must become nonzero. A decomposition that returns
     zero everywhere is broken, not profound. The weakened edge is taken from a NON-SINGLETON orbit:
     the first version weakened edge 0 blindly and failed on a tree whose one nontrivial
     automorphism FIXES edge 0, where the symmetry correctly survived and the control was reporting
     its own premise.

MEASURED, 31 graphs, 3 seconds:

    13 edge-transitive   Var(c) itself is 1e-33..1e-31, i.e. every edge carries ONE value, E(1) = 0
    16 multi-orbit       within-orbit <= 7.9e-30 against between-orbit >= 7.5e-03
     2 trivial Aut       excluded: within-orbit is zero by construction and proves nothing

Twenty-seven orders of magnitude between the within-orbit and between-orbit parts, and the random
partition control does not vanish (>= 1.4e-02), so the orbit partition is not merely a partition.

TWO VERDICTS FAILED ON THE FIRST RUN AND BOTH WERE THE CHECK, NOT THE PHYSICS. A within/total RATIO
over an edge-transitive graph is 0/0 -- both parts are machine zero -- and came back as 1.0, failing
a correct result; the thresholds are absolute now. And control 3 is the tree case above.

Requires numpy, scipy, networkx. No network, no model, no credits. Exact diagonalisation in the
HALF-FILLED sector, n_up = n // 2. That is S^z = 0 only for EVEN n; the seven odd-n graphs here --
the paper's own 15-site gasket among them -- sit at S^z = -1/2. This file said "S^z = 0 sector" in
two places and it was false for 7 of 31 rows, including the one graph the correspondent cares about.
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time

import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import eigsh

HERE = os.path.dirname(os.path.abspath(__file__))
T0 = time.time()
RNG = np.random.default_rng(20260826)

# The L2 gasket from the manuscript, so the sweep contains the paper's own graph.
L2_EDGES = [(0, 6), (0, 8), (1, 9), (1, 11), (2, 12), (2, 14), (3, 6), (3, 7), (3, 9), (3, 10),
            (4, 10), (4, 11), (4, 12), (4, 13), (5, 7), (5, 8), (5, 13), (5, 14),
            (6, 7), (7, 8), (9, 10), (10, 11), (12, 13), (13, 14), (6, 8), (9, 11), (12, 14)]


def build_H(n, edges, j, n_up):
    basis = list(itertools.combinations(range(n), n_up))
    idx = {s: i for i, s in enumerate(basis)}
    H = lil_matrix((len(basis), len(basis)))
    for (a, b), J in zip(edges, j):
        for k, s in enumerate(basis):
            H[k, k] += J * (1 if a in s else -1) * (1 if b in s else -1)
            ua, ub = a in s, b in s
            if ua and not ub:
                H[k, idx[tuple(sorted(set(s) - {a} | {b}))]] += 2 * J
            elif ub and not ua:
                H[k, idx[tuple(sorted(set(s) - {b} | {a}))]] += 2 * J
    return csr_matrix(H), basis


def sp_table(basis, edges):
    return np.array([[(1 if a in s else -1) * (1 if b in s else -1) for s in basis]
                     for (a, b) in edges], float)


def ground_manifold(H, tol=1e-9, kmax=12):
    k = min(kmax, H.shape[0] - 1)
    w, v = eigsh(H, k=k, which="SA", tol=0,
                 v0=RNG.standard_normal(H.shape[0]), maxiter=400000)
    o = np.argsort(w)
    w, v = w[o], v[:, o]
    gaps = np.nonzero(np.diff(w) > tol)[0]
    d = int(gaps[0] + 1) if len(gaps) else k
    return d, v[:, :d], float(w[0])


def manifold_corr(V, sp):
    """Tr(rho S^z S^z) with rho the ground-manifold projector over its degeneracy.

    Averaging the DENSITIES, not the amplitudes: rho is basis-independent inside the manifold and is
    exactly Aut-invariant, which is the whole reason this object and not a single eigenvector.
    """
    return np.mean([sp @ (np.abs(V[:, i]) ** 2) for i in range(V.shape[1])], axis=0)


def edge_orbits(G):
    gm = nx.algorithms.isomorphism.GraphMatcher(G, G)
    autos = list(gm.isomorphisms_iter())
    E = [tuple(sorted(e)) for e in G.edges()]
    lab = {e: e for e in E}
    changed = True
    while changed:
        changed = False
        for a in autos:
            for e in E:
                m = tuple(sorted((a[e[0]], a[e[1]])))
                if lab[m] < lab[e]:
                    lab[e] = lab[m]; changed = True
                elif lab[e] < lab[m]:
                    lab[m] = lab[e]; changed = True
    orb = {}
    for e in E:
        orb.setdefault(lab[e], []).append(e)
    return len(autos), list(orb.values()), E


def decompose(c, E_order, blocks):
    pos = {e: i for i, e in enumerate(E_order)}
    n = len(E_order)
    within, means = 0.0, []
    for ob in blocks:
        ix = [pos[e] for e in ob]
        sub = c[ix]
        within += len(ix) * np.var(sub)
        means.append((len(ix), sub.mean()))
    gm = c.mean()
    between = sum(k * (m - gm) ** 2 for k, m in means) / n
    return float(np.var(c)), float(within / n), float(between)


def random_blocks(E_order, sizes):
    """A partition with the SAME block sizes as the orbits, drawn at random."""
    perm = list(RNG.permutation(len(E_order)))
    out, i = [], 0
    for s in sizes:
        out.append([E_order[perm[k]] for k in range(i, i + s)])
        i += s
    return out


def tree_of(n, seed):
    try:
        return nx.random_labeled_tree(n, seed=seed)
    except AttributeError:
        return nx.random_tree(n, seed=seed)


GRAPHS = {
    # --- edge-transitive: ONE orbit, so the claim predicts E(1) = 0 exactly -------------------
    "C8 cycle": nx.cycle_graph(8),
    "C10 cycle": nx.cycle_graph(10),
    "C12 cycle": nx.cycle_graph(12),
    "K4 complete": nx.complete_graph(4),
    "K5 complete": nx.complete_graph(5),
    "K6 complete": nx.complete_graph(6),
    "K3,3 bipartite": nx.complete_bipartite_graph(3, 3),
    "K4,4 bipartite": nx.complete_bipartite_graph(4, 4),
    "Q3 cube": nx.hypercube_graph(3),
    "Petersen": nx.petersen_graph(),
    "octahedron": nx.complete_multipartite_graph(2, 2, 2),
    "star K1,7": nx.star_graph(7),
    # --- several orbits, nontrivial Aut: the informative middle ------------------------------
    "triangular prism": nx.circular_ladder_graph(3),
    "ladder L4": nx.circular_ladder_graph(4),
    "wheel W7": nx.wheel_graph(7),
    "path P8": nx.path_graph(8),
    "path P10": nx.path_graph(10),
    "bull+": nx.barbell_graph(4, 2),
    "gasket L2 (the paper's)": nx.Graph(L2_EDGES),
    "prism CL5": nx.circular_ladder_graph(5),
    "wheel W5": nx.wheel_graph(5),
    "grid 2x4": nx.grid_2d_graph(2, 4),
    "grid 2x5": nx.grid_2d_graph(2, 5),
    "K1,2,3 tripartite": nx.complete_multipartite_graph(1, 2, 3),
    "lollipop 5+4": nx.lollipop_graph(5, 4),
    "tadpole C6+3": nx.Graph(list(nx.cycle_graph(6).edges())
                             + [(0, 6), (6, 7), (7, 8)]),
    "cycle C8 + chord": nx.Graph(list(nx.cycle_graph(8).edges()) + [(0, 4)]),
    "two triangles bridged": nx.barbell_graph(3, 3),
    # --- trivial or near-trivial Aut: VACUOUS, reported and excluded --------------------------
    "random G(12,0.35) a": nx.gnp_random_graph(12, 0.35, seed=7),
    "random G(12,0.35) b": nx.gnp_random_graph(12, 0.35, seed=11),
    "random tree n=12": tree_of(12, 5),
}


def distinct_pairs() -> list:
    """Isomorphic duplicates among the fixtures, so a row count is never reported as a graph count.

    `ladder L4` is `circular_ladder_graph(4)`, which is the cube Q3, already in the set under its
    own name. Saying "31 graphs" when two rows are the same graph inflates the sweep, and it is the
    kind of number a referee checks first.
    """
    import itertools
    out = []
    for a, b in itertools.combinations(list(GRAPHS), 2):
        ga, gb = GRAPHS[a], GRAPHS[b]
        if (ga.number_of_nodes() == gb.number_of_nodes()
                and ga.number_of_edges() == gb.number_of_edges()
                and nx.is_isomorphic(ga, gb)):
            out.append([a, b])
    return out


def main() -> int:
    rows, skipped = [], []
    print(f"  {len(GRAPHS)} graphs, exact diagonalisation in the half-filled sector (Sz=0 even n, -1/2 odd)\n")
    for name, G0 in GRAPHS.items():
        G = nx.convert_node_labels_to_integers(nx.Graph(G0))
        n = G.number_of_nodes()
        if n > 15 or n < 4:
            skipped.append((name, f"n={n} outside the exact-diagonalisation range"))
            continue
        t = time.time()
        naut, orbits, E = edge_orbits(G)
        j = np.ones(len(E))
        H, basis = build_H(n, E, j, n // 2)
        deg, V, e0 = ground_manifold(H)
        sp = sp_table(basis, E)
        c = manifold_corr(V, sp)
        tot, win, btw = decompose(c, E, orbits)
        sizes = sorted((len(o) for o in orbits), reverse=True)
        # CONTROL 2: same block sizes, random membership.
        r_tot, r_win, r_btw = decompose(c, E, random_blocks(E, [len(o) for o in orbits]))
        # CONTROL 3: break the symmetry, measure against the SAME orbits. The perturbed edge must
        # come from a NON-SINGLETON orbit. Weakening edge 0 blindly failed here on a tree whose one
        # nontrivial automorphism FIXES edge 0: the symmetry survived, within-orbit stayed at 2e-33,
        # and the control reported a defect that was its own premise. An edge the group moves is the
        # only edge whose weakening is guaranteed to split an orbit.
        big = max(orbits, key=len)
        pert = E.index(big[0]) if len(big) > 1 else 0
        j2 = j.copy(); j2[pert] = 0.5
        H2, b2 = build_H(n, E, j2, n // 2)
        d2, V2, _ = ground_manifold(H2)
        c2 = manifold_corr(V2, sp_table(b2, E))
        _, win2, _ = decompose(c2, E, orbits)

        rows.append({"graph": name, "n": n, "edges": len(E), "aut_order": naut,
                     "orbit_sizes": sizes, "n_orbits": len(orbits), "degeneracy": deg,
                     "E1": float(np.sqrt(max(btw, 0.0))),
                     "var_total": tot, "var_within": win, "var_between": btw,
                     "within_share": (win / tot) if tot > 0 else 0.0,
                     "ctrl_random_blocks_within": r_win,
                     "ctrl_random_blocks_within_share": (r_win / tot) if tot > 0 else 0.0,
                     "ctrl_broken_symmetry_within": win2, "ctrl_perturbed_edge": list(E[pert]),
                     "edge_transitive": len(orbits) == 1,
                     "vacuous_all_orbits_size_1": all(s == 1 for s in sizes),
                     "seconds": round(time.time() - t, 1)})
        r = rows[-1]
        print(f"  {name:26s} n={n:2d} |Aut|={naut:5d} orbits={str(sizes)[:18]:18s} "
              f"deg={deg} E(1)={r['E1']:.6f} within/tot={r['within_share']:.1e} "
              f"[{r['seconds']}s]")

    # ---- the evidence set: graphs where the claim is not automatic ------------------------------
    informative = [r for r in rows if not r["vacuous_all_orbits_size_1"]]
    et = [r for r in informative if r["edge_transitive"]]
    multi = [r for r in informative if not r["edge_transitive"]]
    vac = [r for r in rows if r["vacuous_all_orbits_size_1"]]

    v: dict = {}
    v["CONTROL_the_sweep_actually_ran"] = len(rows) >= 15
    v["CONTROL_there_are_informative_graphs_at_all"] = len(informative) >= 10 and len(multi) >= 4
    # THE CLAIM.
    # ABSOLUTE, not a ratio. On an edge-transitive graph the total variance is machine zero too, so
    # within/total is 0/0 and came back as 1.0 -- a number with no content that failed this check
    # over a result that is exactly right.
    v["within_orbit_dispersion_vanishes_on_every_informative_graph"] = all(
        r["var_within"] < 1e-20 for r in informative)
    v["edge_transitive_graphs_carry_ONE_correlation_value"] = all(
        r["var_total"] < 1e-24 for r in et) and bool(et)
    v["edge_transitive_graphs_give_E1_zero"] = all(r["E1"] < 1e-10 for r in et) and bool(et)
    v["multi_orbit_graphs_give_a_NONZERO_orbit_floor"] = all(
        r["E1"] > 1e-6 for r in multi) and bool(multi)
    # CONTROL 2 -- the one that can fail.
    v["CONTROL_random_blocks_do_NOT_vanish"] = all(
        r["ctrl_random_blocks_within_share"] > 1e-6 for r in multi)
    # CONTROL 3 -- the instrument responds.
    v["CONTROL_breaking_the_symmetry_makes_within_orbit_NONZERO"] = all(
        r["ctrl_broken_symmetry_within"] > 1e-12 for r in multi)
    # And the vacuous rows must be recognised as vacuous rather than counted as support.
    v["CONTROL_trivial_Aut_rows_are_excluded_not_counted"] = all(
        r["within_share"] == 0.0 for r in vac) and len(vac) >= 1

    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print(f"\n  informative graphs : {len(informative)}  "
          f"({len(et)} edge-transitive, {len(multi)} multi-orbit)")
    print(f"  excluded as vacuous: {len(vac)} (trivial Aut, within-orbit zero by construction)")
    if multi:
        print(f"  worst within-orbit variance, informative set: "
              f"{max(r['var_within'] for r in informative):.2e}")
        print(f"  smallest between-orbit variance, multi-orbit: "
              f"{min(r['var_between'] for r in multi):.2e}")
        print(f"  smallest random-block within/total (control): "
              f"{min(r['ctrl_random_blocks_within_share'] for r in multi):.2e}")
    print(f"  elapsed: {time.time() - T0:.0f}s")

    # ---- the correspondent's own ring, measured rather than covered by proxy -----------------
    # C8/C10/C12 are in the sweep and edge-transitive, but their ground states are NON-DEGENERATE,
    # so they cannot speak to the question that actually matters: does a single solver vector
    # differ from the multiplet average? Only a degenerate ring can answer that, so measure his.
    Gr = nx.cycle_graph(15)
    Er = [tuple(sorted(e)) for e in Gr.edges()]
    Hr, br = build_H(15, Er, [1.0] * len(Er), 15 // 2)
    dr, Vr, _ = ground_manifold(Hr)
    spr = sp_table(br, Er)
    rng = np.random.default_rng(7)
    real_vals, cplx_vals = [], []
    for _ in range(200):
        x = rng.standard_normal(dr); x /= np.linalg.norm(x)
        real_vals.append(float(np.sqrt(np.var(spr @ (np.abs(Vr @ x) ** 2)))))
        z = rng.standard_normal(dr) + 1j * rng.standard_normal(dr); z /= np.linalg.norm(z)
        cplx_vals.append(float(np.sqrt(np.var(spr @ (np.abs(Vr @ z) ** 2)))))
    ring = {"graph": "C15 (the correspondent's ring)", "n": 15, "sz_sector": "-1/2",
            "degeneracy": dr,
            "E1_at_rho": float(np.sqrt(np.var(manifold_corr(Vr, spr)))),
            "real_vectors_min": min(real_vals), "real_vectors_max": max(real_vals),
            "real_vectors_spread": max(real_vals) - min(real_vals),
            "complex_vectors_min": min(cplx_vals), "complex_vectors_max": max(cplx_vals),
            "n_trials_each": 200,
            "note": "every REAL vector gives ONE value, so a real-arithmetic solver has no spread "
                    "to give; only complex superpositions move. Do NOT explain a reported error "
                    "bar with solver scatter on this evidence -- that mechanism was retracted "
                    "for the gasket on 2026-08-22 and it fails here for the same reason."}
    v["RING_multiplet_average_is_zero"] = ring["E1_at_rho"] < 1e-10
    v["RING_real_vectors_do_NOT_spread"] = ring["real_vectors_spread"] < 1e-12
    v["RING_complex_vectors_DO_spread"] = ring["complex_vectors_min"] < 0.5 * ring["real_vectors_max"]
    print("\n  ring C15: deg=%d E(1)@rho=%.2e real=[%.6f,%.6f] spread=%.1e complex_min=%.4f"
          % (dr, ring["E1_at_rho"], ring["real_vectors_min"], ring["real_vectors_max"],
             ring["real_vectors_spread"], ring["complex_vectors_min"]))
    for _k in ("RING_multiplet_average_is_zero", "RING_real_vectors_do_NOT_spread",
               "RING_complex_vectors_DO_spread"):
        print("  %s  %s" % ("YES" if v[_k] else "no ", _k))

    _dups = distinct_pairs()
    json.dump({"probe": os.path.basename(__file__),
               "rows_are_not_graphs": {
                   "rows": len(GRAPHS), "distinct_graphs": len(GRAPHS) - len(_dups),
                   "isomorphic_pairs": _dups,
                   "note": "report distinct graphs, never the row count"}, "verdicts": v, "rows": rows, "ring": ring,
               "skipped": skipped,
               "claim": "with rho the ground-manifold projector over its degeneracy, edges in one "
                        "Aut(G)-orbit carry equal Tr(rho SzSz), so Var(c) is entirely between-orbit "
                        "and E(1)=sqrt(Var_between); edge-transitive graphs give E(1)=0 exactly",
               "why_the_manifold_average": "every automorphism commutes with H(s=1), so it permutes "
                                           "the ground eigenspace and commutes with its projector. "
                                           "rho is Aut-invariant even where no single eigenvector "
                                           "is, which is why a lone Lanczos vector does not show "
                                           "this and the multiplet average does.",
               "informative": len(informative), "edge_transitive": len(et),
               "multi_orbit": len(multi), "excluded_vacuous": len(vac),
               "elapsed_s": round(time.time() - T0, 1),
               "platform": sys.platform},
              open(os.path.join(HERE, "edrn_the_orbit_floor_holds_across_the_symmetry_spectrum"
                                      ".result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
