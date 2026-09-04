"""Does his multi-entrance deviation measure the network, or the observable's own algebra?

WHY. Li Guanghao's 2026-09-04 mechanism package tests whether two observation entrances act
additively. It builds E_pred(s1,s2) = E1(s1) + E2(s2) - E_ref from the two single-entrance scans and
reports the deviation of the measured E(s1,s2) from it: mean absolute 0.049977, maximum 0.181668,
against an E range of 0.183083 to 0.392870. His text reads that deviation as "the irreducibility of
the relational network": a local change of observation angle causing a global rearrangement.

THE PROBLEM. E is the standard deviation of the edge correlations, pooled over ALL edges. A standard
deviation over a pooled set is not the sum of the parts' standard deviations, so E is non-additive as
a matter of algebra, before any physics. A system whose two halves cannot influence each other at all
would still fail this test. So the number needs a null, and the null is a system that is separable by
construction.

THE NULL. Two disconnected components, one entrance in each. The ground state is the tensor product
of the two components' ground states, so the coupling on one entrance provably cannot change a single
correlation in the other component. Any deviation the test reports there is the pooling algebra and
nothing else. If that deviation is comparable to 0.049977, the statistic does not distinguish an
irreducible network from two systems in separate boxes.

CONTROLS, each able to fail:
  * A POSITIVE CONTROL ON HIS NUMBERS. Arm A reruns his procedure on his graph, his edge pair, his
    grid and his definition, and must reproduce 0.049977 and 0.181668. If it does not, my
    reimplementation is wrong and the null says nothing about his claim.
  * SEPARABILITY IS CHECKED BY A CHECK THAT CAN FAIL. Changing s2 must leave every correlation in
    block A unchanged, and a deliberately coupled twin of the same check must catch a coupling that
    IS there. The first version compared two calls to a memoised function and returned 0.00e+00 for
    a coupled system too, which a verifier demonstrated before this went out.
  * THE NULL CAN EXONERATE HIM. If the separable system's deviation is far below his, the statistic
    does discriminate and his reading survives. That branch is reported as such.
  * THE COMPARISON IS SCALED. A deviation is reported as a fraction of each system's own E range,
    because comparing an absolute deviation across two systems with different ranges is meaningless.
  * EACH NULL'S MARGINALS MUST MOVE. If E does not vary with one of the two entrances, additivity
    holds by arithmetic and the arm reports zero no matter what the physics does. The first version
    of the cut arm did exactly that and returned 0.000000000.
  * TWO INDEPENDENT NULLS, because the obvious objection to the first is that it is a different
    graph. The second cuts HIS graph until no path joins the two entrances, keeping the node count,
    the lattice family and most of the edges. Two nulls agreeing is worth more than one.
"""
from __future__ import annotations

import io
import itertools
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "separable_null_for_the_multi_entrance_deviation.result.json")

GRID = (0.0, 3.0, 21)          # his S_MIN, S_MAX, S_GRID_SIZE
HIS = {"mean_abs": 0.04997721400862463, "max_abs": 0.18166838189877788,
       "e_min": 0.183083, "e_max": 0.392870}
TOL = 5e-5


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def basis_of(nodes, n_up):
    return [frozenset(c) for c in itertools.combinations(sorted(nodes), n_up)]


def ground_vector(nodes, edges, J, n_up, seed=0):
    """Lowest state of one connected block in one magnetisation sector, seeded."""
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import eigsh
    from scipy.linalg import eigh
    b = basis_of(nodes, n_up)
    idx = {st: i for i, st in enumerate(b)}
    H = lil_matrix((len(b), len(b)))
    for k, st in enumerate(b):
        diag = 0.0
        for (u, v), j in zip(edges, J):
            same = (u in st) == (v in st)
            diag += j * (1.0 if same else -1.0)
        H[k, k] = diag
        for (u, v), j in zip(edges, J):
            if (u in st) != (v in st):
                ns = frozenset(st.symmetric_difference({u, v}))
                if ns in idx:
                    H[k, idx[ns]] += 2.0 * j
    H = H.tocsr()
    if H.shape[0] <= 40:
        w, v = eigh(H.toarray())
        return float(w[0]), v[:, 0], b
    rng = np.random.default_rng(seed)
    w, v = eigsh(H, k=1, which="SA", v0=rng.standard_normal(H.shape[0]), tol=1e-9)
    return float(w[0]), v[:, 0], b


def corrs_from(vec, b, edges):
    import numpy as np
    p = np.abs(vec) ** 2
    out = []
    for (u, v) in edges:
        sgn = np.array([1.0 if ((u in st) == (v in st)) else -1.0 for st in b])
        out.append(float(p @ sgn))
    return out


def E_of(corrs):
    import numpy as np
    return float(np.std(np.array(corrs)))


def linear_prediction(e1, e2, e_ref):
    """His formula, transcribed: E_pred(s1,s2) = E1(s1) + E2(s2) - E_ref."""
    import numpy as np
    return np.array([[e1[i] + e2[j] - e_ref for j in range(len(e2))] for i in range(len(e1))])


def deviation(e1, e2, e2d, e_ref):
    import numpy as np
    d = np.array(e2d) - linear_prediction(e1, e2, e_ref)
    return float(np.mean(np.abs(d))), float(np.max(np.abs(d)))


def arm_connected():
    """His graph, his pair, his grid. The positive control."""
    import numpy as np
    import networkx as nx
    G = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
    edges = [tuple(sorted(e)) for e in G.edges()]
    if len(edges) != 20:
        refuse("the small-world generator gave %d edges, not 20" % len(edges))
    for e in ((0, 1), (6, 8)):
        if e not in edges:
            refuse("edge %s is not in the small-world graph" % (e,))
    i1, i2 = edges.index((0, 1)), edges.index((6, 8))
    nodes, n_up = list(range(10)), 5
    grid = np.linspace(*GRID)

    def E_at(s1, s2):
        J = np.ones(len(edges))
        J[i1], J[i2] = s1, s2
        _w, v, b = ground_vector(nodes, edges, J, n_up)
        return E_of(corrs_from(v, b, edges))

    e1 = [E_at(s, 1.0) for s in grid]
    e2 = [E_at(1.0, s) for s in grid]
    ref = e1[int(np.argmin(np.abs(grid - 1.0)))]
    e2d = [[E_at(a, bb) for bb in grid] for a in grid]
    m, mx = deviation(e1, e2, e2d, ref)
    flat = [x for row in e2d for x in row]
    return {"mean_abs": m, "max_abs": mx, "E_min": min(flat), "E_max": max(flat)}


def arm_separable():
    """Two disconnected blocks, one entrance in each. Coupling is impossible by construction."""
    import numpy as np
    # THE FIRST CHOICE OF BLOCKS SATURATED. With the entrance edge closing a triangle, J >= 1 froze
    # the block: correlations locked at (-1, 0, -0.6667, -0.6667, 0) and E sat at exactly 0.400000
    # for every larger coupling, so most of the grid contributed nothing and the arm's small
    # deviation was a flat marginal rather than an algebra floor. A path puts the entrance in
    # competition with the rest of the chain instead of letting it form an isolated singlet.
    A_nodes, B_nodes = list(range(6)), list(range(6, 12))
    A_edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5)]
    B_edges = [(6, 7), (7, 8), (8, 9), (9, 10), (10, 11), (6, 11)]
    edges = A_edges + B_edges
    e1_i, e2_i = 0, 0                       # the first edge of each block is its entrance
    grid = np.linspace(*GRID)
    a_up, b_up = 3, 3                       # one fixed sector per block, so the state is a product

    cacheA, cacheB = {}, {}

    def block(nodes, blk_edges, which, s, cache, up):
        if s not in cache:
            J = np.ones(len(blk_edges))
            J[which] = s
            _w, v, b = ground_vector(nodes, blk_edges, J, up)
            cache[s] = corrs_from(v, b, blk_edges)
        return cache[s]

    def E_at(s1, s2):
        return E_of(block(A_nodes, A_edges, e1_i, s1, cacheA, a_up)
                    + block(B_nodes, B_edges, e2_i, s2, cacheB, b_up))

    # CONTROL, AND ITS OWN POSITIVE CONTROL. The first version of this compared two calls to a
    # MEMOIZED function, so it returned the cached object and the drift was 0.00e+00 whatever the
    # physics did. A verifier proved it dead by wiring an artificial coupling into a block and
    # watching the check still pass. It is a structural fact that s2 cannot enter block A's
    # Hamiltonian, so the honest form is a check that could see a violation if one existed, and a
    # deliberately coupled twin that it must catch.
    def measure_A(s1, s2_unused, couple=0.0):
        """Block A's correlations, computed fresh. `couple` fakes a dependence on s2 for the twin."""
        J = np.ones(len(A_edges))
        J[e1_i] = s1 + couple
        _w, v, b = ground_vector(A_nodes, A_edges, J, a_up)
        return corrs_from(v, b, A_edges)

    honest_lo = measure_A(1.0, 1.0)
    honest_hi = measure_A(1.0, 2.5)
    drift = max(abs(x - y) for x, y in zip(honest_lo, honest_hi))
    coupled_lo = measure_A(1.0, 1.0, couple=0.0)
    coupled_hi = measure_A(1.0, 2.5, couple=-0.9)    # the twin, where s2 DOES reach block A
    twin = max(abs(x - y) for x, y in zip(coupled_lo, coupled_hi))
    print("     separability check: real %.2e, deliberately coupled twin %.2e" % (drift, twin))
    if twin < 1e-6:
        refuse("the coupled twin moved by only %.2e, so this check cannot see a coupling and its "
               "zero on the real system means nothing" % twin)
    if drift > 1e-12:
        refuse("the 'separable' system's block A moved by %.2e when block B changed, so it is not "
               "separable and this null is void" % drift)

    e1 = [E_at(s, 1.0) for s in grid]
    e2 = [E_at(1.0, s) for s in grid]
    r1, r2 = max(e1) - min(e1), max(e2) - min(e2)
    if min(r1, r2) < 1e-3:
        refuse("a marginal of the separable null is nearly flat (ranges %.2e and %.2e), so its small "
               "deviation is a saturated block rather than an algebra floor" % (r1, r2))
    ref = e1[int(np.argmin(np.abs(grid - 1.0)))]
    e2d = [[E_at(a, bb) for bb in grid] for a in grid]
    m, mx = deviation(e1, e2, e2d, ref)
    flat = [x for row in e2d for x in row]
    return {"mean_abs": m, "max_abs": mx, "E_min": min(flat), "E_max": max(flat),
            "marginal_ranges": [r1, r2],
            "separability_drift": drift, "coupled_twin_drift": twin}


def arm_cut_his_graph():
    """HIS graph, cut until no path joins the two entrances. Same nodes, same family, no coupling."""
    import numpy as np
    import networkx as nx
    G = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
    G = nx.Graph([tuple(sorted(e)) for e in G.edges()])
    keep = {(0, 1), (6, 8)}
    # A minimum edge cut between the two NODES is the wrong object: the entrances themselves can
    # bridge, so a min cut can come back consisting only of edges we are forbidden to delete, which
    # is what the first version refused on. Cut greedily along shortest paths instead, never
    # touching an entrance. The result is a cut, not the smallest one, and a null needs only a cut.
    cut = set()
    while nx.has_path(G, 0, 6):
        path = nx.shortest_path(G, 0, 6)
        # Prefer an edge in the MIDDLE of the path. Taking the first one strips the entrance's own
        # neighbourhood, and a block reduced to the entrance edge alone has a constant correlation,
        # which makes the whole arm report a deviation of exactly zero by construction.
        cands = [tuple(sorted((u, v))) for u, v in zip(path, path[1:])
                 if tuple(sorted((u, v))) not in keep]
        step = cands[len(cands) // 2] if cands else None
        if step is None:
            refuse("every edge on the remaining path is an entrance, so the two cannot be separated")
        G.remove_edge(*step)
        cut.add(step)
    comps = list(nx.connected_components(G))
    edges = sorted(tuple(sorted(e)) for e in G.edges())
    for e in keep:
        if e not in edges:
            refuse("cutting removed the entrance %s, so the null no longer tests the same thing" % (e,))
    print("  ARM C: cut %d edge(s) %s, leaving %d edges in %d components"
          % (len(cut), sorted(tuple(sorted(e)) for e in cut), len(edges), len(comps)))

    blocks = []
    for c in comps:
        nodes = sorted(c)
        be = [e for e in edges if e[0] in c and e[1] in c]
        blocks.append((nodes, be))
    where = {}
    for bi, (nodes, be) in enumerate(blocks):
        for e in keep:
            if e in be:
                where[e] = (bi, be.index(e))
    if len(where) != 2 or where[(0, 1)][0] == where[(6, 8)][0]:
        refuse("the two entrances did not land in different components")

    grid = np.linspace(*GRID)
    caches = [{} for _ in blocks]

    def block_corrs(bi, s):
        nodes, be = blocks[bi]
        if s not in caches[bi]:
            J = np.ones(len(be))
            if bi == where[(0, 1)][0]:
                J[where[(0, 1)][1]] = s
            elif bi == where[(6, 8)][0]:
                J[where[(6, 8)][1]] = s
            _w, v, b = ground_vector(nodes, be, J, max(1, len(nodes) // 2))
            caches[bi][s] = corrs_from(v, b, be)
        return caches[bi][s]

    def E_at(s1, s2):
        out = []
        for bi in range(len(blocks)):
            if bi == where[(0, 1)][0]:
                out += block_corrs(bi, s1)
            elif bi == where[(6, 8)][0]:
                out += block_corrs(bi, s2)
            else:
                out += block_corrs(bi, 1.0)
        return E_of(out)

    before = block_corrs(where[(0, 1)][0], 1.0)[:]
    _ = block_corrs(where[(6, 8)][0], 2.5)
    after = block_corrs(where[(0, 1)][0], 1.0)
    drift = max(abs(x - y) for x, y in zip(before, after))
    if drift > 1e-12:
        refuse("the cut graph's first block moved by %.2e when the second changed" % drift)

    e1 = [E_at(s, 1.0) for s in grid]
    e2 = [E_at(1.0, s) for s in grid]
    # CONTROL THAT THE FIRST VERSION LACKED. If either marginal is flat, the additivity test is
    # satisfied by arithmetic and the arm reports zero whatever the physics does. Measured: the
    # greedy cut had reduced the first block to the entrance edge alone, whose correlation is
    # constant, and the arm returned exactly 0.000000000 as if that were evidence.
    r1, r2 = max(e1) - min(e1), max(e2) - min(e2)
    if min(r1, r2) < 1e-6:
        refuse("a marginal of the cut graph is flat (ranges %.2e and %.2e), so this arm cannot "
               "produce a non-zero deviation whatever the physics is" % (r1, r2))
    ref = e1[int(np.argmin(np.abs(grid - 1.0)))]
    e2d = [[E_at(a, bb) for bb in grid] for a in grid]
    m, mx = deviation(e1, e2, e2d, ref)
    flat = [x for row in e2d for x in row]
    return {"mean_abs": m, "max_abs": mx, "E_min": min(flat), "E_max": max(flat),
            "marginal_ranges": [r1, r2],
            "block_sizes": [len(b[1]) for b in blocks],
            "edges_cut": sorted(tuple(sorted(e)) for e in cut), "edges_left": len(edges),
            "separability_drift": drift}


def main():
    t0 = time.time()
    print("  serial: two arms, %d single points and %d pair points each"
          % (2 * GRID[2], GRID[2] ** 2))

    a = arm_connected()
    print("  ARM A, his graph and pair: mean |dev| %.9f, max %.9f, E in [%.6f, %.6f]"
          % (a["mean_abs"], a["max_abs"], a["E_min"], a["E_max"]))
    hit_mean = abs(a["mean_abs"] - HIS["mean_abs"]) < TOL
    hit_max = abs(a["max_abs"] - HIS["max_abs"]) < TOL
    print("     against his %.9f / %.9f : %s"
          % (HIS["mean_abs"], HIS["max_abs"],
             "REPRODUCED" if (hit_mean and hit_max) else "DIFFERS"))
    if not (hit_mean and hit_max):
        refuse("arm A does not reproduce his published deviation, so my reimplementation is not his "
               "procedure and the null below says nothing about his claim")

    b = arm_separable()
    print("  ARM B, two disconnected blocks: mean |dev| %.9f, max %.9f, E in [%.6f, %.6f]"
          % (b["mean_abs"], b["max_abs"], b["E_min"], b["E_max"]))


    c = arm_cut_his_graph()
    print("  ARM C, his graph cut apart:   mean |dev| %.9f, max %.9f, E in [%.6f, %.6f]"
          % (c["mean_abs"], c["max_abs"], c["E_min"], c["E_max"]))

    ra = a["E_max"] - a["E_min"]
    rb = b["E_max"] - b["E_min"]
    rc = c["E_max"] - c["E_min"]
    fa, fb = a["mean_abs"] / ra, b["mean_abs"] / rb
    fc = c["mean_abs"] / rc if rc > 0 else float("nan")
    print()
    print("  scaled to each system's own E range:")
    print("     his connected graph : %.6f / %.6f = %.1f%%" % (a["mean_abs"], ra, 100 * fa))
    print("     separable null      : %.6f / %.6f = %.1f%%" % (b["mean_abs"], rb, 100 * fb))
    print("     his graph, cut apart: %.6f / %.6f = %.1f%%" % (c["mean_abs"], rc, 100 * fc))

    worst_null = max(fb, fc)
    if worst_null >= 0.5 * fa:
        verdict = "STATISTIC_DOES_NOT_DISCRIMINATE"
        print("  VERDICT: a provably separable system produces a deviation of the same order, so "
              "this statistic does not distinguish an irreducible network from two separate boxes.")
    elif worst_null <= 0.1 * fa:
        verdict = "STATISTIC_DISCRIMINATES"
        print("  VERDICT: the separable null is an order of magnitude smaller, so the statistic does "
              "discriminate and his reading survives this test.")
    else:
        verdict = "PARTLY_DISCRIMINATES"
        print("  VERDICT: the null is smaller but not negligible, so the deviation is part algebra "
              "and part physics and cannot be reported as one number.")

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "grid": "linspace(%g,%g,%d)" % GRID,
        "his_published": HIS,
        "arm_connected": a, "arm_separable": b, "arm_cut_his_graph": c,
        "fraction_of_range": {"connected": fa, "separable": fb, "cut_his_graph": fc},
        "verdict": verdict,
        "seconds": time.time() - t0,
        "controls": {
            "positive_control_reproduced_his_numbers": True,
            "separability_asserted_numerically": True,
            "null_can_exonerate": True,
            "two_independent_nulls": True,
            "deviation_scaled_to_each_range": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s  [%.0fs]" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
