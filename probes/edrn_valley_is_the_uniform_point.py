"""EDRN: is the valley a phenomenon, or is s=1 simply the uniform point?

WHAT THE MANUSCRIPT CLAIMS (luoxuejian000/edrn-dmrg-verification#2, revision of 2026-08-18):
a "reproducible non-monotonic feature" -- a sharp valley in E(s), the spatial standard deviation of
nearest-neighbour <sz sz> across edges -- located at s=1.000 in a Sierpinski L2 graph, and ALSO at
s=1.0 in a ring and in a tree. All other edges carry J=1; the scanned edge carries J=s.

THE OBJECTION THIS PROBE TESTS. s=1 is exactly the value at which the "contradiction edge" stops
being a defect and the coupling pattern becomes uniform. The manuscript states this in words -- "the
ring and tree valleys occur at s=1.0, where the contradiction edge strength equals the uniform
coupling" -- and then draws no consequence from it. Three checks decide whether the valley is a
finding or a restatement of uniformity, and none of them depends on his vertex labelling:

  A. RATIO IDENTITY. H(s, J0) = J0 * H(s/J0, 1), so eigenvectors -- hence every correlation -- depend
     only on the RATIO s/J0, never on s alone. If so, "s=1.000" names no special coupling strength;
     it names the uniform point, and the valley must MOVE to s=J0 when the background is rescaled.
     Prediction: argmin_s E(s; J0=0.6) = 0.6 * argmin_s E(s; J0=1.0), exactly.
  B. THE RING IS AN IDENTITY. A uniform ring is edge-transitive, so every edge carries the identical
     correlation and E(1) = 0 exactly. Its "valley depth 0.0891" is then the distance from a
     symmetry-forced zero -- textbook, not evidence.
  C. THE FLAT CONTROL. Sec. "control edge (0,1)" reports range 0.000000 and cross-seed std 1.4e-11
     over s in [0,1]. At s=0 that edge is SEVERED. Severing an edge of a connected graph changes the
     ground state, so a real edge cannot give exactly zero. Measured here across all 27 edges: the
     smallest range any real edge produces, versus what a NON-edge produces.

CONTROLS ON THIS PROBE ITSELF (a probe that cannot fail has measured nothing):
  * the ring at s=1 must return E=0 to machine precision -- if it does not, the correlation code is
    wrong and every number below is void;
  * a scan of a real edge must produce a large range -- if a real edge ever reads 0.000000, check C
    proves nothing;
  * the ratio identity is checked on ENERGIES too, which are unambiguous under degeneracy.

Labelling note: the vertex numbering below is OURS. The manuscript's adjacency list is promised in
supplementary material and has not been published, so no claim here is about his specific indices --
A and B are labelling-free, and C is stated over ALL edges.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh

OUT = pathlib.Path(__file__).with_suffix(".result.json")


# ---------------------------------------------------------------- graphs
def sierpinski_sieve(level: int):
    """Sierpinski sieve graph by exact integer subdivision. L1 -> 6 vertices/9 edges,
    L2 -> 15/27, matching the manuscript's stated sizes."""
    scale = 2 ** level
    tris = [((0, 0), (scale, 0), (0, scale))]
    for _ in range(level):
        nxt = []
        for a, b, c in tris:
            mab = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
            mac = ((a[0] + c[0]) // 2, (a[1] + c[1]) // 2)
            mbc = ((b[0] + c[0]) // 2, (b[1] + c[1]) // 2)
            nxt += [(a, mab, mac), (mab, b, mbc), (mac, mbc, c)]
        tris = nxt
    pts = sorted({p for t in tris for p in t})
    idx = {p: i for i, p in enumerate(pts)}
    edges = set()
    for t in tris:
        for u, v in itertools.combinations(t, 2):
            edges.add(tuple(sorted((idx[u], idx[v]))))
    return len(pts), sorted(edges)


def ring(n):
    return n, [(i, (i + 1) % n) for i in range(n)]


def binary_tree(n=15):
    import networkx as nx
    g = nx.balanced_tree(2, 3)
    return g.number_of_nodes(), sorted(tuple(sorted(e)) for e in g.edges())


def random_graph(n=15, m=27, seed=42):
    import networkx as nx
    g = nx.gnm_random_graph(n, m, seed=seed)
    return n, sorted(tuple(sorted(e)) for e in g.edges())


GRAPHS = {
    "fractal_L2": lambda: sierpinski_sieve(2),
    "fractal_L1": lambda: sierpinski_sieve(1),
    "ring15": lambda: ring(15),
    "tree15": lambda: binary_tree(15),
    "random15": lambda: random_graph(),
}


# ---------------------------------------------------------------- physics
def _z_table(n):
    b = np.arange(1 << n, dtype=np.int64)
    return np.stack([1 - 2 * ((b >> k) & 1) for k in range(n)]).astype(np.int8)


def hamiltonian(n, edges, couplings, z):
    """H = sum_e J_e (sx sx + sy sy + sz sz) in PAULI matrices. The xy part flips an
    anti-aligned pair with amplitude 2J."""
    dim = 1 << n
    diag = np.zeros(dim)
    rows, cols, vals = [], [], []
    for (i, j), jij in zip(edges, couplings):
        if jij == 0.0:
            continue
        diag += jij * (z[i].astype(np.float64) * z[j])
        anti = np.nonzero(z[i] != z[j])[0]
        flipped = anti ^ ((1 << i) | (1 << j))
        rows.append(flipped); cols.append(anti)
        vals.append(np.full(anti.size, 2.0 * jij))
    r = np.concatenate(rows + [np.arange(dim)])
    c = np.concatenate(cols + [np.arange(dim)])
    v = np.concatenate(vals + [diag])
    return sp.csr_matrix((v, (r, c)), shape=(dim, dim))


def ground(n, edges, couplings, z, seed=0):
    h = hamiltonian(n, edges, couplings, z)
    rng = np.random.default_rng(seed)
    v0 = rng.standard_normal(1 << n)
    w, vecs = eigsh(h, k=1, which="SA", v0=v0, tol=1e-10, maxiter=20000)
    return float(w[0]), vecs[:, 0]


def enhanced(psi, edges, z):
    p = psi ** 2
    corr = np.array([float(p @ (z[i].astype(np.float64) * z[j])) for i, j in edges])
    return float(corr.std()), corr


def scan_point(task):
    name, n, edges, target, s, j0, seed = task
    coup = [j0] * len(edges)
    coup[target] = s
    zt = _z_table(n)
    e0, psi = ground(n, edges, coup, zt, seed)
    val, _ = enhanced(psi, edges, zt)
    return dict(graph=name, edge=target, s=s, j0=j0, seed=seed, energy=e0, E=val)


def run(tasks, label, workers):
    t0 = time.time()
    out = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for k, r in enumerate(ex.map(scan_point, tasks), 1):
            out.append(r)
            if k % max(1, len(tasks) // 20) == 0 or k == len(tasks):
                print("  [%s] %d/%d  %.1fs" % (label, k, len(tasks), time.time() - t0), flush=True)
    return out


# ------------------------------------------- the solver-independent observable
def ground_space(n, edges, couplings, z, k=8, tol=1e-8):
    """The ground MULTIPLET, not one vector from it.

    Measured 2026-08-18: at the uniform point the ground state of both the 15-ring and the
    Sierpinski L2 is EXACTLY four-fold degenerate. A single Lanczos vector is then an arbitrary
    direction in a 4-dimensional space, so E computed from it is a property of the solver's starting
    vector, not of the Hamiltonian: five seeds gave 0.119/0.077/0.131/0.079/0.111 on the ring, a
    spread of 0.055 against a reported ring "valley depth" of 0.0891.

    Averaging over the whole eigenspace restores every symmetry of H and is invariant under any
    unitary rotation inside it, so it IS an observable. For the uniform ring it must return exactly
    zero -- that is this probe's positive control.
    """
    h = hamiltonian(n, edges, couplings, z)
    # ARPACK's start vector is RANDOM by default, and that made the degeneracy count itself
    # nondeterministic: measured 2026-08-18, five identical calls on the uniform ring returned d=4
    # four times and d=3 once, and the one d=3 draw reported E=3.2e-02 where the truth is 4.3e-16.
    # A probe whose answer depends on an unseeded start vector is the defect it is looking for.
    rng = np.random.default_rng(20260818)
    v0 = rng.standard_normal(1 << n)
    w, v = eigsh(h, k=k, which="SA", tol=0, v0=v0, maxiter=100000)
    order = np.argsort(w)
    w, v = w[order], v[:, order]
    # d = the size of the cluster before the first REAL gap, not a fixed absolute window
    jumps = np.diff(w)
    big = np.nonzero(jumps > tol)[0]
    d = int(big[0] + 1) if big.size else len(w)
    if d >= len(w):
        raise RuntimeError("ground multiplet not resolved: raise k above %d" % k)
    return float(w[0]), d, v[:, :d]


def enhanced_projected(vecs, edges, z):
    """<sz_i sz_j> under the uniform mixture over the degenerate ground space."""
    p = (vecs ** 2).mean(axis=1)
    corr = np.array([float(p @ (z[i].astype(np.float64) * z[j])) for i, j in edges])
    return float(corr.std()), corr


def scan_point_projected(task):
    name, n, edges, target, s, j0 = task
    coup = [j0] * len(edges)
    coup[target] = s
    zt = _z_table(n)
    e0, d, vecs = ground_space(n, edges, coup, zt)
    val, _ = enhanced_projected(vecs, edges, zt)
    return dict(graph=name, edge=target, s=round(s, 6), j0=j0, energy=e0, degeneracy=d, E=val)


def solve(n, edges, coup, z):
    """Resolve the ground multiplet, widening the window until a real gap appears."""
    for k in (12, 24, 48):
        try:
            return ground_space(n, edges, coup, z, k=k, tol=1e-6)
        except RuntimeError:
            continue
    raise RuntimeError("ground multiplet unresolved even at k=48")


def _task(t):
    kind, name, n, edges, target, s, j0 = t
    coup = [j0] * len(edges)
    coup[target] = s
    zt = _z_table(n)
    e0, d, vecs = solve(n, edges, coup, zt)
    val, _ = enhanced_projected(vecs, edges, zt)
    return dict(kind=kind, graph=name, edge=list(edges[target]), edge_index=target,
                s=round(s, 6), j0=j0, ratio=round(s / j0, 6), energy=e0, degeneracy=d, E=val)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=min(20, (os.cpu_count() or 4) - 2))
    a = ap.parse_args()
    z15 = _z_table(15)

    # ---- CONTROL. The uniform ring is edge-transitive, so its dispersion is identically zero.
    # If this ever returns non-zero, the observable is broken and nothing below means anything.
    rn, re_ = ring(15)
    _, rd, rv = ground_space(rn, re_, [1.0] * 15, z15, k=12, tol=1e-6)
    ring_zero, _ = enhanced_projected(rv, re_, z15)
    print("CONTROL uniform ring: degeneracy=%d  E=%.3e  %s"
          % (rd, ring_zero, "PASS" if ring_zero < 1e-10 else "FAIL"), flush=True)
    if ring_zero >= 1e-10:
        raise SystemExit("positive control failed -- the observable is wrong, stopping")

    fn, fe = sierpinski_sieve(2)
    tip_edge = next(i for i, (u, v) in enumerate(fe) if u == 0)          # tip -> interior

    tasks = []
    # EXP1  the ratio identity: E depends only on s/J0, so the valley must MOVE with the background
    for j0 in (1.0, 0.6, 1.4):
        for r in np.arange(0.50, 1.5001, 0.02):
            tasks.append(("ratio", "fractal_L2", fn, fe, tip_edge, float(r) * j0, j0))
    # EXP2  does the valley survive a solver-independent observable?
    for name, (n, e) in [("fractal_L2", (fn, fe)), ("ring15", ring(15)),
                         ("tree15", binary_tree(15)), ("random15", random_graph())]:
        tgt = tip_edge if name == "fractal_L2" else 0
        for s in np.arange(0.0, 3.0001, 0.05):
            tasks.append(("scan", name, n, e, tgt, float(s), 1.0))
    # EXP3  every edge of the L2 graph -- what range does a REAL edge produce?
    for ei in range(len(fe)):
        for s in np.arange(0.0, 1.0001, 0.1):
            tasks.append(("edges", "fractal_L2", fn, fe, ei, float(s), 1.0))

    print("%d solves on %d workers" % (len(tasks), a.workers), flush=True)
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for i, r in enumerate(ex.map(_task, tasks, chunksize=2), 1):
            rows.append(r)
            if i % 50 == 0 or i == len(tasks):
                print("  %d/%d  %.0fs" % (i, len(tasks), time.time() - t0), flush=True)

    OUT.write_text(json.dumps({"control_ring_uniform_E": ring_zero,
                               "fractal_L2_edges": [list(x) for x in fe],
                               "rows": rows}, indent=1), encoding="utf-8")
    print("wrote %s (%d rows, %.0fs)" % (OUT, len(rows), time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
