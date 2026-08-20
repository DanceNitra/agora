"""The same scan with a bond observable that a degeneracy cannot corrupt.

The manuscript's observable is the dispersion across edges of <sz_i sz_j>. That quantity is not
invariant inside a degenerate ground multiplet: different Sz members of one spin multiplet carry
different <sz sz>, so a single Lanczos vector reports a number that depends on which member the
solver happened to land on.

<sigma_i . sigma_j> = <sx sx + sy sy + sz sz> is a SCALAR under SU(2), so it takes the SAME value in
every member of a multiplet. Averaging <sz sz> over a full multiplet gives exactly (1/3)<sigma.sigma>
by isotropy, so this is the manuscript's observable with the artefact removed, up to a constant
factor that cancels in any statement about WHERE a minimum sits.

Worked in the Sz=+1/2 sector (dim 6435 instead of 32768), which also shrinks the degeneracy: a spin
multiplet contributes exactly one state per Sz value, so what remains degenerate there is orbital,
and that is averaged explicitly.

Guard carried from the run this replaces: for 15 spin-1/2 the total spin is half-integer, so every
FULL-SPACE multiplet has even dimension. An odd count means ARPACK returned an incomplete space --
that is how a 6-fold tree multiplet was silently read as 5 and half a curve came out wrong.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import time

import json

import numpy as np
from scipy.sparse.linalg import eigsh

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("edrn", HERE / "edrn_valley_is_the_uniform_point.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

N = 15
Z = P._z_table(N)
SZ = Z.sum(axis=0)
IDX = np.nonzero(SZ == 1)[0]                       # Sz = +1/2
POS = -np.ones(1 << N, dtype=np.int64)
POS[IDX] = np.arange(IDX.size)
ZI = Z[:, IDX].astype(np.float64)


def sector_ground(edges, coup, k=6, tol=1e-8):
    h = P.hamiltonian(N, edges, coup, Z).tocsr()[IDX][:, IDX]
    w, v = eigsh(h, k=k, which="SA", tol=0, maxiter=300000,
                 v0=np.random.default_rng(20260818).standard_normal(IDX.size))
    o = np.argsort(w); w, v = w[o], v[:, o]
    j = np.nonzero(np.diff(w) > tol)[0]
    if not j.size:
        raise RuntimeError("multiplet not resolved at k=%d" % k)
    return float(w[0]), int(j[0] + 1), v[:, : int(j[0] + 1)]


def sigma_dot_sigma(vecs, edges):
    """<sigma_i . sigma_j> averaged over the (orbital) ground space, per edge."""
    out = np.zeros(len(edges))
    for a in range(vecs.shape[1]):
        psi = vecs[:, a]
        p = psi ** 2
        for m, (i, j) in enumerate(edges):
            diag = float(p @ (ZI[i] * ZI[j]))
            anti = np.nonzero(ZI[i] != ZI[j])[0]
            partner = POS[IDX[anti] ^ ((1 << i) | (1 << j))]
            out[m] += diag + 2.0 * float(psi[anti] @ psi[partner])
    return out / vecs.shape[1]


def main():
    graphs = {"fractal_L2": P.sierpinski_sieve(2), "ring15": P.ring(15),
              "tree15": P.binary_tree(15), "random15": P.random_graph()}
    grid = np.arange(0.05, 3.0001, 0.05)
    t0 = time.time()
    out = {}
    for name, (n, e) in graphs.items():
        tgt = next(i for i, (u, v) in enumerate(e) if u == 0) if name == "fractal_L2" else 0
        curve, degs = [], []
        for s in grid:
            c = [1.0] * len(e); c[tgt] = float(s)
            _, d, V = sector_ground(e, c)
            corr = sigma_dot_sigma(V, e)
            curve.append(float(corr.std())); degs.append(d)
        curve = np.array(curve)
        i = int(np.argmin(curve))
        at1 = float(curve[np.argmin(np.abs(grid - 1.0))])
        print("%-11s edge %-7s min at s=%.2f (E=%.6f) | E(s=1)=%.6f | range=%.6f | sector degeneracies %s | %.0fs"
              % (name, str(e[tgt]), grid[i], curve[i], at1, curve.max() - curve.min(),
                 sorted(set(degs)), time.time() - t0), flush=True)
        near = [(round(float(g), 2), round(float(c), 6)) for g, c in zip(grid, curve) if 0.85 <= g <= 1.15]
        print("      around s=1: %s" % near, flush=True)
        out[name] = {"edge": list(e[tgt]), "s": [round(float(x), 4) for x in grid],
                     "E": [float(x) for x in curve], "sector_degeneracy": degs,
                     "argmin_s": float(grid[i])}
    (HERE / "edrn_su2_invariant_scan.result.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote receipt", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
