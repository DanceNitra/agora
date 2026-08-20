"""The small-world scan done exactly: full spectrum, exact degeneracy, continuous observable.

WHY THIS EXISTS. The manuscript's N=15 graph results come apart at s=1.000 because the observable --
the dispersion across edges of <sz_i sz_j> -- is evaluated on a ground space whose DIMENSION jumps
there, and a single Lanczos vector inside a degenerate space is not an observable at all. The
small-world system is different: N=10 is small enough to diagonalise in full (1024 states), so the
spectrum, the degeneracy and the multiplet average are all exact and there is nothing left to argue
about. This is the part of the work that can carry a paper, so it deserves the exact treatment.

Graph: networkx.watts_strogatz_graph(10, k=4, p=0.1, seed=42) -- verified to contain every edge the
manuscript's tables name.

WHAT IS REPORTED PER EDGE, and each of these can kill a valley:
  * s* -- the minimum of E(s), and whether it is INTERIOR (a minimum at a scan endpoint is not a
    valley; the manuscript already excludes edge (7,8) on exactly this ground);
  * whether the ground-space DIMENSION is constant in a neighbourhood of s*. If it jumps there, the
    observable is discontinuous at that point and the "valley" is the step between two averaging
    domains -- the N=15 failure mode;
  * the LOCAL depth, measured from the neighbouring local maxima, not from the global scan maximum.
    Measuring depth from the far end of a monotone descent inflates it: the manuscript quotes 0.0998
    for the fractal that way, where the local feature in its own data is ~0.004;
  * the energy gap at s*, so a near-degenerate point cannot pass unnoticed.

CONTROL: a uniform 10-ring is edge-transitive, so its dispersion is exactly zero. If that comes back
non-zero the observable is wrong and every number here is void.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import time
from concurrent.futures import ProcessPoolExecutor

import networkx as nx
import numpy as np

OUT = pathlib.Path(__file__).with_suffix(".result.json")
N = 10
DIM = 1 << N


def z_table(n=N):
    b = np.arange(1 << n, dtype=np.int64)
    return np.stack([1 - 2 * ((b >> k) & 1) for k in range(n)]).astype(np.int8)


Z = z_table()
ZF = Z.astype(np.float64)


def hamiltonian(edges, coup):
    h = np.zeros((DIM, DIM))
    diag = np.zeros(DIM)
    for (i, j), jij in zip(edges, coup):
        diag += jij * (ZF[i] * ZF[j])
        anti = np.nonzero(Z[i] != Z[j])[0]
        h[anti ^ ((1 << i) | (1 << j)), anti] += 2.0 * jij
    h[np.arange(DIM), np.arange(DIM)] += diag
    return h


def observable(edges, coup, tol=1e-9):
    """Exact ground multiplet, then <sz_i sz_j> averaged over it -- basis-independent."""
    w, v = np.linalg.eigh(hamiltonian(edges, coup))
    d = int(np.sum(w - w[0] < tol))
    gap = float(w[d] - w[0])
    p = (v[:, :d] ** 2).mean(axis=1)
    corr = np.array([p @ (ZF[i] * ZF[j]) for i, j in edges])
    return float(corr.std()), d, gap


def _task(t):
    edges, ei, svals = t
    out = []
    for s in svals:
        c = [1.0] * len(edges); c[ei] = float(s)
        E, d, gap = observable(edges, c)
        out.append((round(float(s), 4), E, d, gap))
    return ei, out


def local_depth(svals, E, i):
    """Depth from the neighbouring local maxima, not from the far end of a monotone run."""
    left = max(E[:i]) if i else None
    right = max(E[i + 1:]) if i + 1 < len(E) else None
    # nearest local maximum on each side
    def nearest_max(rng):
        best = None
        for k in rng:
            if 0 < k < len(E) - 1 and E[k] >= E[k - 1] and E[k] >= E[k + 1]:
                best = k; break
        return best
    lk = nearest_max(range(i - 1, 0, -1))
    rk = nearest_max(range(i + 1, len(E) - 1))
    if lk is None or rk is None:
        return None, lk, rk
    return float(min(E[lk], E[rk]) - E[i]), lk, rk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=float, default=0.01)
    ap.add_argument("--workers", type=int, default=min(16, (os.cpu_count() or 4) - 2))
    a = ap.parse_args()

    ring = [(i, (i + 1) % N) for i in range(N)]
    ctrl, dctrl, _ = observable(ring, [1.0] * N)
    print("CONTROL uniform 10-ring: degeneracy %d  E = %.3e  %s"
          % (dctrl, ctrl, "PASS" if ctrl < 1e-10 else "FAIL"), flush=True)
    if ctrl >= 1e-10:
        raise SystemExit("positive control failed -- observable is wrong")

    g = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
    edges = sorted(tuple(sorted(e)) for e in g.edges())
    svals = np.arange(0.0, 3.0 + a.step / 2, a.step)
    print("%d edges x %d points, exact 1024-dim diagonalisation, %d workers"
          % (len(edges), len(svals), a.workers), flush=True)

    t0 = time.time(); res = {}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for k, (ei, rowsq) in enumerate(ex.map(_task, [(edges, i, svals) for i in range(len(edges))]), 1):
            res[ei] = rowsq
            print("  %d/%d edges  %.0fs" % (k, len(edges), time.time() - t0), flush=True)

    report = []
    for ei in sorted(res):
        rowsq = res[ei]
        ss = [r[0] for r in rowsq]; E = [r[1] for r in rowsq]
        deg = [r[2] for r in rowsq]; gaps = [r[3] for r in rowsq]
        i = int(np.argmin(E))
        interior = 0 < i < len(E) - 1
        lo, hi = max(0, i - 3), min(len(E), i + 4)
        deg_const = len(set(deg[lo:hi])) == 1
        depth, lk, rk = local_depth(ss, E, i)
        report.append(dict(edge=list(edges[ei]), s_star=ss[i], interior=interior,
                           degeneracy_at_min=deg[i], degeneracy_constant_near_min=deg_const,
                           degeneracies_seen=sorted(set(deg)), gap_at_min=gaps[i],
                           local_depth=depth, full_range=max(E) - min(E), E_at_min=E[i]))
    OUT.write_text(json.dumps({"edges": [list(e) for e in edges], "step": a.step,
                               "control_ring10": ctrl, "report": report,
                               "curves": {str(ei): res[ei] for ei in sorted(res)}}, indent=1),
                   encoding="utf-8")

    print("\n%-8s %-7s %-9s %-11s %-13s %-10s %s" % ("edge", "s*", "interior", "deg at s*",
                                                     "deg constant", "gap", "local depth"))
    for r in report:
        print("%-8s %-7.2f %-9s %-11d %-13s %-10.4f %s"
              % (tuple(r["edge"]), r["s_star"], r["interior"], r["degeneracy_at_min"],
                 r["degeneracy_constant_near_min"], r["gap_at_min"],
                 "n/a" if r["local_depth"] is None else "%.6f" % r["local_depth"]))
    real = [r for r in report if r["interior"] and r["degeneracy_constant_near_min"]
            and r["local_depth"] is not None and r["local_depth"] > 1e-4]
    print("\n%d of %d edges have an INTERIOR minimum with a CONSTANT ground-space dimension around it"
          % (len(real), len(report)))
    print("manuscript claims 19 of 20 significant valleys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
