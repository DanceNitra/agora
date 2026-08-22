"""At s = 1.0 the SG(2) ground state is degenerate. Which half of the 27-edge scan survives that?

THE CLAIM (@luoxuejian000, edrn-dmrg-verification#2, replacing the withdrawn (0,1) control-edge
claim): all 27 edges of SG(2) show a valley at s = 1.0, the global and local diagnostics are compared
edge by edge, and the conclusion drawn is that the phenomenon is "a structural property of the entire
graph".

THE COMPUTATION IS RIGHT and the labelling is right. The 27 global ranges take exactly five values
-- 0.143538 x6, 0.158573 x6, 0.172919 x6, 0.121280 x6, 0.077438 x3 -- and this probe confirms
independently that SG(2) has |Aut| = 6 with edge orbits of sizes 6, 6, 6, 6, 3. The arithmetic
reproduces here to the last published digit, and our earlier disagreement about (0,1) was two
labellings of the same graph.

WHAT THIS FILE WAS WRITTEN TO SHOW, AND FAILED TO. The diagnostic takes ONE Lanczos vector,
`eigsh(H, k=1, which='SA', v0=v0)` with `v0` from `default_rng(0)`, so the hypothesis was that the
published numbers move with the seed. They do not: ten seeds agree to 3e-15. The file keeps its name
so the refutation stays attached to it.

WHAT IS ACTUALLY THERE, and it splits the result in two.

At s = 1.0 every coupling equals 1, so setting the scanned edge to 1.0 changes nothing: the
Hamiltonian is the SAME MATRIX for all 27 edges. And at that one point of the grid -- at no other --
the ground state is TWO-FOLD DEGENERATE. Any single ground vector then breaks the graph's own
symmetry: correlations that must be equal within an orbit differ by 0.42.

  * The GLOBAL diagnostic SURVIVES this, and that is a real result rather than a failed control.
    Rotating inside the two-dimensional ground space acts like the graph's 3-fold rotation, which
    permutes edges within their orbits, so the multiset of 27 correlations -- and hence its standard
    deviation -- cannot move. Measured across 181 directions: width below 1e-9. The global number is
    a property of H.

  * The LOCAL diagnostic DOES NOT. A radius-2 neighbourhood is not closed under that rotation, so it
    reads a symmetry-broken state through a window the symmetry moves, and returns whatever the
    eigensolver's arbitrary direction happens to place inside it.

THE TELL IS IN THE POSTED DATA FILE, before any re-run. The six tip edges are one orbit, and E_local
at s = 1.00 reads 0.120543 / 0.085621 / 0.217784 / 0.217669 for the first four of them. Four
different numbers, one state, isomorphic neighbourhoods. That cannot be a property of the graph.

CONTROLS, because a probe that cannot fail has measured nothing:
  * POSITIVE: seed 0 must reproduce the published E_global at s = 1.0 (0.159658), or this is not the
    same computation and nothing below is about that result;
  * NEGATIVE: a uniform 15-ring is edge-transitive, so its ground-space-averaged diagnostic must be
    0 to machine precision -- if it is not, the averaging is wrong and its verdict is void;
  * TWO-SIDED: under rotation inside the ground space the global width must be ~0 AND the local
    width must be non-zero. Either one passing alone would prove nothing;
  * DISCRIMINATING: at a NON-degenerate point (s = 1.5) the single-vector and averaged diagnostics
    must coincide, or the averaging measures something else and its verdict at s = 1 means nothing.

Run:  python probes/edrn_his_valley_bottom_is_a_start_vector.py
"""
from __future__ import annotations
import itertools
import json
import os
import sys
import time

import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import eigsh

HERE = os.path.dirname(os.path.abspath(__file__))

HIS_EDGES = [(0, 6), (0, 8), (1, 9), (1, 11), (2, 12), (2, 14),
             (3, 6), (3, 7), (3, 9), (3, 10), (4, 10), (4, 11), (4, 12), (4, 13),
             (5, 7), (5, 8), (5, 13), (5, 14),
             (6, 7), (7, 8), (9, 10), (10, 11), (12, 13), (13, 14),
             (6, 8), (9, 11), (12, 14)]
N, N_UP = 15, 7                      # his N_up, not ours
HIS_PUBLISHED_AT_S1 = 0.159658       # posted data file, every edge, s = 1.00
HIS_TIP_LOCAL_AT_S1 = [0.120543, 0.085621, 0.217784, 0.217669]   # (0,6) (0,8) (1,9) (1,11)
SMALLEST_REPORTED_RANGE = 0.077438


# --------------------------------------------------------------- his construction, unchanged
def build_hamiltonian(n, edges, j_vals, n_up):
    basis_states = list(itertools.combinations(range(n), n_up))
    state_to_idx = {st: i for i, st in enumerate(basis_states)}
    H = lil_matrix((len(basis_states), len(basis_states)), dtype=float)
    for (i, j), J in zip(edges, j_vals):
        for idx, state in enumerate(basis_states):
            si = 1 if i in state else -1
            sj = 1 if j in state else -1
            H[idx, idx] += J * si * sj
        for idx, state in enumerate(basis_states):
            i_up, j_up = i in state, j in state
            if i_up and not j_up:
                ns = list(state)
                ns.remove(i)
                ns.append(j)
                H[idx, state_to_idx[tuple(sorted(ns))]] += 2 * J
            elif j_up and not i_up:
                ns = list(state)
                ns.remove(j)
                ns.append(i)
                H[idx, state_to_idx[tuple(sorted(ns))]] += 2 * J
    return csr_matrix(H), basis_states


def _sp_table(basis, edges):
    return np.array([[(1 if i in st else -1) * (1 if j in st else -1) for st in basis]
                     for (i, j) in edges], dtype=np.float64)


def single_vector_density(H, seed=0):
    """His psi**2: one Lanczos vector, start vector the only free parameter."""
    rng = np.random.default_rng(seed)
    _, evecs = eigsh(H, k=1, which="SA", v0=rng.standard_normal(H.shape[0]))
    return np.abs(evecs[:, 0]) ** 2


def ground_space(H, tol=1e-8, k=10):
    rng = np.random.default_rng(20260822)
    w, v = eigsh(H, k=k, which="SA", tol=0, v0=rng.standard_normal(H.shape[0]), maxiter=200000)
    o = np.argsort(w)
    w, v = w[o], v[:, o]
    jumps = np.diff(w)
    big = np.nonzero(jumps > tol)[0]
    if not big.size:
        raise RuntimeError("ground multiplet not resolved at k=%d" % k)
    d = int(big[0] + 1)
    return float(w[0]), d, v[:, :d], float(jumps[big[0]])


def mixture_density(vecs):
    """Uniform mixture over the ground space: invariant under any rotation inside it."""
    return (vecs ** 2).mean(axis=1)


def local_edges_r2(edge, radius=2):
    import networkx as nx
    g = nx.Graph()
    g.add_nodes_from(range(N))
    g.add_edges_from(HIS_EDGES)
    nu = set(nx.single_source_shortest_path_length(g, edge[0], cutoff=radius))
    nv = set(nx.single_source_shortest_path_length(g, edge[1], cutoff=radius))
    keep = nu | nv
    return [e for e in g.edges() if e[0] in keep and e[1] in keep]


def edge_orbits(edges, n):
    """Edge orbits under the full automorphism group, via VF2.

    The first draft of this walked itertools.permutations(range(15)) -- 1.3 trillion candidates --
    which is not a slow probe, it is a probe that never returns an answer.
    """
    import networkx as nx
    from networkx.algorithms.isomorphism import GraphMatcher
    g = nx.Graph()
    g.add_nodes_from(range(n))
    g.add_edges_from(edges)
    autos = [tuple(m[v] for v in range(n)) for m in GraphMatcher(g, g).isomorphisms_iter()]
    idx = {frozenset(e): k for k, e in enumerate(edges)}
    orb, seen = [], set()
    for k, e in enumerate(edges):
        if k in seen:
            continue
        o = {idx[frozenset((p[e[0]], p[e[1]]))] for p in autos}
        orb.append(sorted(o))
        seen |= o
    return orb, len(autos)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    t0 = time.time()
    ok = True
    res = {}

    orbits, n_auto = edge_orbits(HIS_EDGES, N)
    print("SG(2): %d edges, |Aut| = %d, edge orbit sizes = %s"
          % (len(HIS_EDGES), n_auto, [len(o) for o in orbits]), flush=True)
    res["orbit_sizes"], res["automorphisms"] = [len(o) for o in orbits], n_auto

    print("building the Hamiltonian at the uniform point (dim = C(15,7) = 6435) ...", flush=True)
    H1, basis = build_hamiltonian(N, HIS_EDGES, np.ones(len(HIS_EDGES)), N_UP)
    sp = _sp_table(basis, HIS_EDGES)
    print("  built in %.1fs" % (time.time() - t0), flush=True)

    # ---- CONTROL (positive): reproduce his published number ------------------------------------
    q_single = single_vector_density(H1, 0)
    corr_single = sp @ q_single
    e_single = float(np.std(corr_single))
    match = abs(e_single - HIS_PUBLISHED_AT_S1) < 5e-6
    print("\nCONTROL published E_global(s=1) = %.6f ; here = %.6f  %s"
          % (HIS_PUBLISHED_AT_S1, e_single, "PASS" if match else "FAIL"), flush=True)
    res["his_published_s1"], res["reproduced_s1"] = HIS_PUBLISHED_AT_S1, e_single
    if not match:
        print("this is not the same computation; nothing below is about that result")
        return 1

    # ---- the start-vector hypothesis this file is named after, REFUTED --------------------------
    vals = [float(np.std(sp @ single_vector_density(H1, s_))) for s_ in range(10)]
    spread_seed = max(vals) - min(vals)
    print("seeds 0-9 -> E_global spread = %.3e   START-VECTOR HYPOTHESIS REFUTED" % spread_seed,
          flush=True)
    res["seed_spread_s1"] = spread_seed
    res["start_vector_hypothesis"] = "REFUTED: 10 seeds agree to %.1e" % spread_seed

    # ---- 1. degeneracy, and whether it is specific to the valley bottom -------------------------
    e_gs, d, vecs, gap = ground_space(H1)
    print("\nground state at s = 1: E0 = %.9f  degeneracy = %d  gap = %.3e" % (e_gs, d, gap),
          flush=True)
    res["degeneracy_uniform"], res["gap_uniform"] = d, gap

    print("degeneracy across his own s grid:", flush=True)
    degs = []
    for sv in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0):
        jj = np.ones(len(HIS_EDGES))
        jj[0] = sv
        Hs, _b = build_hamiltonian(N, HIS_EDGES, jj, N_UP)
        _e, dd, _v, gg = ground_space(Hs)
        degs.append({"s": sv, "degeneracy": dd, "gap": gg})
        print("  s = %-5.2f degeneracy = %d   gap = %.3e" % (sv, dd, gg), flush=True)
    res["degeneracy_by_s"] = degs
    only_at_one = (all(r["degeneracy"] == 1 for r in degs if r["s"] != 1.0)
                   and next(r for r in degs if r["s"] == 1.0)["degeneracy"] > 1)
    print("  degenerate at s = 1 and nowhere else on his grid: %s" % only_at_one, flush=True)
    res["degenerate_only_at_s1"] = bool(only_at_one)

    # ---- 2. TWO-SIDED control: rotate inside the ground space -----------------------------------
    q_mix = mixture_density(vecs)
    thetas = np.linspace(0.0, np.pi, 181)
    sp_loc0 = _sp_table(basis, local_edges_r2(HIS_EDGES[0]))
    g_sweep, l_sweep = [], []
    for th in thetas:
        psi = np.cos(th) * vecs[:, 0] + np.sin(th) * vecs[:, 1]
        psi /= np.linalg.norm(psi)
        q = psi ** 2
        g_sweep.append(float(np.std(sp @ q)))
        l_sweep.append(float(np.std(sp_loc0 @ q)))
    gw, lw = max(g_sweep) - min(g_sweep), max(l_sweep) - min(l_sweep)
    print("\nrotating inside the %d-fold ground space (181 directions, every one a ground state):"
          % d, flush=True)
    print("  E_global %.6f .. %.6f   width %.3e  -> INVARIANT, a property of H"
          % (min(g_sweep), max(g_sweep), gw), flush=True)
    print("  E_local  %.6f .. %.6f   width %.6f  -> NOT invariant"
          % (min(l_sweep), max(l_sweep), lw), flush=True)
    c_glob, c_loc = gw < 1e-9, lw > 1e-3
    print("  CONTROL global invariant: %s    CONTROL local moves: %s"
          % ("PASS" if c_glob else "FAIL", "PASS" if c_loc else "FAIL"), flush=True)
    ok = ok and c_glob and c_loc
    res["rot_global_width"], res["rot_local_width"] = gw, lw
    res["rot_local_min"], res["rot_local_max"] = min(l_sweep), max(l_sweep)

    # ---- 3. the six tip edges are ONE orbit: one state must score them alike --------------------
    tip = [e for e in HIS_EDGES if min(e) < 3]
    his_loc, mix_loc = [], []
    for e in tip:
        spl = _sp_table(basis, local_edges_r2(e))
        his_loc.append(float(np.std(spl @ q_single)))
        mix_loc.append(float(np.std(spl @ q_mix)))
    print("\nthe six tip edges form ONE symmetry orbit, so one state must score them alike:",
          flush=True)
    print("  his file      : %s" % ", ".join("%.6f" % v for v in HIS_TIP_LOCAL_AT_S1), flush=True)
    print("  single vector : %s" % ", ".join("%.6f" % v for v in his_loc), flush=True)
    print("  ground-space  : %s" % ", ".join("%.6f" % v for v in mix_loc), flush=True)
    orb_s, orb_m = max(his_loc) - min(his_loc), max(mix_loc) - min(mix_loc)
    print("  spread within the orbit: single %.6f   mixture %.3e" % (orb_s, orb_m), flush=True)
    c_orb = orb_m < 1e-9 < orb_s
    print("  CONTROL mixture orbit-constant AND single vector not: %s"
          % ("PASS" if c_orb else "FAIL"), flush=True)
    ok = ok and c_orb
    res["tip_local_single"], res["tip_local_mixture"] = his_loc, mix_loc
    res["tip_orbit_spread_single"], res["tip_orbit_spread_mixture"] = orb_s, orb_m

    corr_mix = sp @ q_mix
    worst = max(float(corr_single[o].max() - corr_single[o].min()) for o in orbits)
    worst_m = max(float(corr_mix[o].max() - corr_mix[o].min()) for o in orbits)
    print("  largest within-orbit spread of the 27 correlations: single %.6f  mixture %.3e"
          % (worst, worst_m), flush=True)
    res["within_orbit_spread_single"], res["within_orbit_spread_mixture"] = worst, worst_m

    # ---- 4. CONTROL (negative): a uniform ring must give exactly zero ---------------------------
    ring = [(i, (i + 1) % 15) for i in range(15)]
    Hr, br = build_hamiltonian(15, ring, np.ones(15), N_UP)
    _e, dr, vr, _g = ground_space(Hr)
    e_ring = float(np.std(_sp_table(br, ring) @ mixture_density(vr)))
    ring_ok = e_ring < 1e-9
    print("\nCONTROL uniform 15-ring, ground-space diagnostic = %.3e (degeneracy %d)  %s"
          % (e_ring, dr, "PASS" if ring_ok else "FAIL"), flush=True)
    res["ring_value"], res["ring_degeneracy"] = e_ring, dr
    ok = ok and ring_ok

    # ---- 5. CONTROL (discriminating): where the state is unique the two must agree --------------
    j2 = np.ones(len(HIS_EDGES))
    j2[0] = 1.5
    H2, b2 = build_hamiltonian(N, HIS_EDGES, j2, N_UP)
    sp2 = _sp_table(b2, HIS_EDGES)
    e_s2 = float(np.std(sp2 @ single_vector_density(H2, 0)))
    _e2, d2, v2, _g2 = ground_space(H2)
    e_m2 = float(np.std(sp2 @ mixture_density(v2)))
    agree = abs(e_s2 - e_m2) < 1e-8
    print("CONTROL at s = 1.5 (degeneracy %d): single %.9f  ground-space %.9f  %s"
          % (d2, e_s2, e_m2, "PASS" if agree else "FAIL"), flush=True)
    res["s15_single"], res["s15_mixture"], res["degeneracy_s15"] = e_s2, e_m2, d2
    ok = ok and agree

    e_mix1 = float(np.std(corr_mix))
    res["global_s1_single"], res["global_s1_mixture"] = e_single, e_mix1
    res["smallest_reported_range"] = SMALLEST_REPORTED_RANGE

    print("\n" + "=" * 92)
    print("GLOBAL at s = 1: single vector %.6f, ground-space average %.6f. Both well defined --"
          % (e_single, e_mix1))
    print("  two different states, not two different solvers. The global claim stands.")
    print("LOCAL at s = 1: spans %.6f across ground states that are all legitimate, and scores"
          % lw)
    print("  six symmetry-equivalent edges %.6f apart. That is not a property of the graph," % orb_s)
    print("  and the local-vs-global comparison is the half that rests on it.")
    print("=" * 92)

    res["all_controls_pass"] = bool(ok)
    out = os.path.join(HERE, "edrn_his_valley_bottom_is_a_start_vector.result.json")
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1)
    print("receipt -> " + out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
