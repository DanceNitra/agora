"""Reference scan for the contradiction-edge experiment, with the two guards that were missing.

Drop-in for a per-edge scan of H = sum_edges J_ij (sx sx + sy sy + sz sz), all J=1 except one edge
carrying J=s. It answers the same question as before and refuses to answer it wrongly.

GUARD 1 -- THE SCANNED PAIR MUST BE AN EDGE.
    On the Sierpinski gasket the three tips are pairwise at distance 4, so no tip-tip pair is an edge.
    In the labelling this collaboration's own constructor produces, vertex 0 has neighbours 6 and 8;
    (0,1), (0,2) and (1,2) are all tip-tip and none of them is in the graph. Setting J on a pair that
    is not an edge either does nothing (if the code writes into an edge list) or silently ADDS a new
    bond (if it appends a coupling term). Both are invisible in the output: the first gives a
    perfectly flat curve, which reads as a clean null result.

GUARD 2 -- DO NOT COMPARE A VALUE ACROSS A CHANGE IN GROUND-SPACE DIMENSION.
    The observable is an average over the ground space. Where that space changes dimension the
    average jumps for a reason that is not physics, and a single Lanczos/DMRG vector inside a
    degenerate space is not an observable at all -- it is a property of the solver's start vector.
    On the L2 gasket the dimension goes 2 -> 4 -> 2 across s=1.000 and nowhere else, and that single
    point is the whole of the reported valley: the one-sided limits are 0.15966 from both directions
    while the average over the enlarged space is 0.11027.

Both guards are cheap. Guard 1 is one lookup; guard 2 is one extra eigenvalue.

    from scan_guard import sierpinski_gasket, scan_edge, positive_control
    positive_control()                                   # must pass before anything is believed
    G = sierpinski_gasket(2)                             # 15 vertices, 27 edges
    r = scan_edge(G, (0, 6), np.arange(0, 3.001, 0.01))  # (0,1) would raise
    print(r["discontinuous_at"])                         # s values you must not read as a feature
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh

DENSE_MAX_N = 13


def sierpinski_gasket(level: int) -> nx.Graph:
    """Level 1 -> 6 vertices / 9 edges, level 2 -> 15/27. Tips are the three degree-2 vertices."""
    G = nx.Graph()

    def rec(v1, v2, v3, d):
        if d == 0:
            G.add_edges_from([(v1, v2), (v2, v3), (v3, v1)])
            return
        m12 = max(G.nodes) + 1
        m23, m31 = m12 + 1, m12 + 2
        G.add_nodes_from([m12, m23, m31])
        rec(v1, m12, m31, d - 1)
        rec(v2, m23, m12, d - 1)
        rec(v3, m31, m23, d - 1)

    G.add_nodes_from([0, 1, 2])
    rec(0, 1, 2, level)
    return G


def check_edge(G: nx.Graph, pair) -> tuple:
    """GUARD 1. Refuse a pair that is not an edge, and say why in terms the caller can act on."""
    u, v = pair
    if u not in G or v not in G:
        raise ValueError("vertex %s is not in the graph (it has %d vertices)"
                         % (u if u not in G else v, G.number_of_nodes()))
    if not G.has_edge(u, v):
        raise ValueError(
            "(%s,%s) is NOT an edge of this graph, so scanning it measures nothing. "
            "deg(%s)=%d with neighbours %s ; deg(%s)=%d with neighbours %s ; graph distance %d. "
            "A scan of a non-edge returns a perfectly flat curve, which reads as a clean null."
            % (u, v, u, G.degree(u), sorted(G[u]), v, G.degree(v), sorted(G[v]),
               nx.shortest_path_length(G, u, v)))
    return (u, v)


def _z(n):
    b = np.arange(1 << n, dtype=np.int64)
    return np.stack([1 - 2 * ((b >> k) & 1) for k in range(n)]).astype(np.int8)


def _H(n, edges, coup, z, isotropic=True):
    """isotropic=True  -> sx sx + sy sy + sz sz (the manuscript's model).
    isotropic=False -> sx sx + sz sz, which is the XY model in a rotated frame and is what the
    tensor-RG toolchain in this directory actually computes. They are different models; whichever
    you run, say which one."""
    dim = 1 << n
    diag = np.zeros(dim)
    rows, cols, vals = [], [], []
    allb = np.arange(dim)
    for (i, j), w in zip(edges, coup):
        if w == 0.0:
            continue
        anti = np.nonzero(z[i] != z[j])[0]
        flip_all = allb ^ ((1 << i) | (1 << j))
        if isotropic:
            diag += w * (z[i].astype(np.float64) * z[j])
            rows.append(flip_all[anti])
            cols.append(anti)
            vals.append(np.full(anti.size, 2.0 * w))
        else:
            diag += w * (z[i].astype(np.float64) * z[j])
            rows.append(flip_all)
            cols.append(allb)
            vals.append(np.full(dim, w))
    r = np.concatenate(rows + [allb])
    c = np.concatenate(cols + [allb])
    v = np.concatenate(vals + [diag])
    return sp.csr_matrix((v, (r, c)), shape=(dim, dim))


def ground_multiplet(n, edges, coup, z, isotropic=True, tol=1e-8):
    """GUARD 2's input: the whole ground space with its dimension, not one vector from it."""
    h = _H(n, edges, coup, z, isotropic)
    if n <= DENSE_MAX_N:
        w, v = np.linalg.eigh(h.toarray())
    else:
        w = v = None
        prev = None
        for k in (12, 24, 48, 96):
            # A FIXED start vector. ARPACK's default is random, which makes the DEGENERACY COUNT
            # itself nondeterministic: measured, five identical calls returned two different counts,
            # and the odd one out reported 0.032 where the truth is 4e-16.
            wk, vk = eigsh(h, k=k, which="SA", tol=0, maxiter=300000,
                           v0=np.random.default_rng(0).standard_normal(1 << n))
            o = np.argsort(wk)
            wk, vk = wk[o], vk[:, o]
            jm = np.nonzero(np.diff(wk) > tol)[0]
            if jm.size:
                dk = int(jm[0] + 1)
                # For an ODD number of spin-1/2 the total spin is half-integer, so every multiplet
                # has EVEN dimension. An odd count means the solver returned an incomplete space --
                # that is how a 6-fold multiplet was once silently read as 5.
                bad_parity = (n % 2 == 1) and (dk % 2 == 1)
                if not bad_parity and dk <= k - 4 and (prev is None or prev == dk):
                    w, v = wk, vk
                    break
                prev = dk
            else:
                prev = None
        if w is None:
            raise RuntimeError("ground multiplet not resolved; raise k")
    d = int(np.sum(w - w[0] < tol))
    return float(w[0]), d, v[:, :d], float(w[d] - w[0])


def scan_edge(G, pair, svals, isotropic=True):
    edges = sorted(tuple(sorted(e)) for e in G.edges())
    target = edges.index(check_edge(G, tuple(sorted(pair))))
    n = G.number_of_nodes()
    z = _z(n)
    E, dims, gaps = [], [], []
    for s in svals:
        c = [1.0] * len(edges)
        c[target] = float(s)
        _, d, V, gap = ground_multiplet(n, edges, c, z, isotropic)
        p = (V ** 2).mean(axis=1)
        corr = np.array([p @ (z[i].astype(np.float64) * z[j]) for i, j in edges])
        E.append(float(corr.std()))
        dims.append(d)
        gaps.append(gap)
    # Two different things, and conflating them cries wolf on perfectly good points.
    # A TRANSITION is where the dimension changes between consecutive s -- normal, and only means
    # the two sides must not be compared as if they were one curve.
    # A SPIKE is a single s whose dimension differs from BOTH neighbours. That is the dangerous one:
    # the curve is continuous on either side and one isolated point sits somewhere else entirely.
    # On the L2 gasket at s=1.000 the spike IS the entire reported valley.
    transitions = [float(svals[k]) for k in range(1, len(svals)) if dims[k] != dims[k - 1]]
    spikes = [float(svals[k]) for k in range(1, len(svals) - 1)
              if dims[k] != dims[k - 1] and dims[k] != dims[k + 1] and dims[k - 1] == dims[k + 1]]
    return {"s": [float(x) for x in svals], "E": E, "dim": dims, "gap": gaps,
            "dim_transitions_at": transitions, "isolated_dim_spikes_at": spikes,
            "edge": list(edges[target]), "isotropic": isotropic}


def positive_control():
    """A uniform ring is edge-transitive, so its dispersion is exactly zero. If this fails the
    observable is wrong and no number produced by this module means anything."""
    R = nx.cycle_graph(10)
    r = scan_edge(R, (0, 1), [1.0])
    assert r["E"][0] < 1e-10, "positive control FAILED: uniform ring gave %.3e, expected 0" % r["E"][0]
    return r["E"][0]


if __name__ == "__main__":
    print("positive control (uniform 10-ring): E = %.3e  PASS" % positive_control())
    G = sierpinski_gasket(2)
    print("gasket L2: %d vertices, %d edges, tips %s"
          % (G.number_of_nodes(), G.number_of_edges(), [v for v in G if G.degree(v) == 2]))
    for bad in [(0, 1), (0, 2)]:
        try:
            check_edge(G, bad)
        except ValueError as ex:
            print("\nGUARD 1 on %s:\n  %s" % (str(bad), ex))
    r = scan_edge(G, (0, 6), [0.99, 1.00, 1.01])
    print("\nGUARD 2 on the real edge (0,6):")
    for s, e, d in zip(r["s"], r["E"], r["dim"]):
        print("   s=%.2f  E=%.8f  ground-space dimension %d" % (s, e, d))
    print("   isolated dimension spikes at: %s" % r["isolated_dim_spikes_at"])
    print("   -> the drop there is the step between two averaging domains, not a feature")
    print("\nsame tool on the small-world system, where nothing is degenerate:")
    W = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
    rw = scan_edge(W, (2, 5), np.arange(0.70, 0.801, 0.01))
    print("   dimensions %s ; spikes %s ; minimum at s=%.2f"
          % (sorted(set(rw["dim"])), rw["isolated_dim_spikes_at"] or "none",
             rw["s"][int(np.argmin(rw["E"]))]))
    print("   manuscript reports this edge's valley at s=0.750")
