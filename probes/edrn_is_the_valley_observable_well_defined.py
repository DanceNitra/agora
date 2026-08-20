"""Is the LDS-valley observable a property of the STATE, or of which eigenvector Lanczos returned?

THE QUESTION. The enhanced diagnosis is E(s) = std over edges of <psi|sigma_z^i sigma_z^j|psi>. That
is only a property of the system if |psi> is unique. Measured here, on Sierpinski SG(2) at N=15: the
ground manifold is DEGENERATE at every s tested -- gap E1-E0 ~ 1e-14, and three-fold at s=1.0. On a
degenerate manifold `eigsh` returns an arbitrary member, and a different start vector returns a
different one.

This is the trap that already cost this collaboration once. On 2026-08-05 the star-graph valley was
reported as the flagship result; it turned out to be machine zero by symmetry, because full-space
`eigh` had returned an arbitrary member of a degenerate multiplet and the six equivalent edges of the
star gave six different numbers. The star was withdrawn. The same mechanism is present here, on the
graph the paper's strongest claim rests on.

WHAT IS MEASURED, and why each piece is needed:

  1. Span the degenerate ground manifold properly (eigsh k>=4, keep everything within 1e-10 of E0),
     then draw random unit vectors INSIDE it. If E varies across the manifold, E is not a state
     function and the valley depth inherits that spread. The paper reports 6-20% depth scatter and
     attributes it to "sensitivity to the precise eigenvector selected within a degenerate or
     near-degenerate ground-state manifold" -- that is the same phenomenon, named but not carried
     through to the conclusion.

  2. The same test inside a FIXED total-Sz sector. Heisenberg conserves Sz, so if the ground state is
     unique per sector, working in one sector makes E well-defined again -- that would be the fix,
     not a refutation, and it is worth handing over as a fix.

  3. A control that must FAIL: a non-degenerate toy system, where E must be identical across start
     vectors. Without it, "E varies" could just mean the measurement is noisy.

NOT CLAIMED: that the LDS valley is unreal. An independent implementation not reproducing it is a
discrepancy, not a refutation, and the paper's compiler may differ from this one in ways the text does
not fix. What is claimed is narrower and does not depend on matching their numbers: on this graph, at
this size, with this Hamiltonian and this observable, the ground manifold is degenerate and the
observable is not invariant across it -- so a depth quoted to four digits from a single Lanczos call
is quoting the start vector as much as the physics.
"""
from __future__ import annotations

import itertools
import json

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

SX = sp.csr_matrix(np.array([[0, 1], [1, 0]], dtype=float))
SY_I = sp.csr_matrix(np.array([[0, -1], [1, 0]], dtype=float))
SZ = sp.csr_matrix(np.array([[1, 0], [0, -1]], dtype=float))
ID = sp.identity(2, format="csr")
N = 15


def sierpinski(level=2):
    tri = [(0.0, 0.0), (1.0, 0.0), (0.5, np.sqrt(3) / 2)]
    tris = [tuple(tri)]
    for _ in range(level):
        nxt = []
        for (a, b, c) in tris:
            ab = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            bc = ((b[0] + c[0]) / 2, (b[1] + c[1]) / 2)
            ca = ((c[0] + a[0]) / 2, (c[1] + a[1]) / 2)
            nxt += [(a, ab, ca), (ab, b, bc), (ca, bc, c)]
        tris = nxt
    pts, idx = [], {}
    for t in tris:
        for p in t:
            k = (round(p[0], 9), round(p[1], 9))
            if k not in idx:
                idx[k] = len(pts); pts.append(k)
    E = set()
    for t in tris:
        for p, q in itertools.combinations(t, 2):
            E.add(tuple(sorted((idx[(round(p[0], 9), round(p[1], 9))],
                                idx[(round(q[0], 9), round(q[1], 9))]))))
    return sorted(E)


def _op(n, d):
    m = None
    for q in range(n):
        m = d.get(q, ID) if m is None else sp.kron(m, d.get(q, ID), format="csr")
    return m


def build(n, edges):
    zz = {e: _op(n, {e[0]: SZ, e[1]: SZ}) for e in edges}
    bond = {e: (_op(n, {e[0]: SX, e[1]: SX}) - _op(n, {e[0]: SY_I, e[1]: SY_I}) + zz[e])
            for e in edges}
    return bond, zz


def H_at(n, edges, bond, defect, s):
    H = sp.csr_matrix((2 ** n, 2 ** n))
    for e in edges:
        J = s if e == defect else 1.0
        if J:
            H = H + J * bond[e]
    return H.tocsr()


def E_of(psi, edges, zz):
    return float(np.std([float(psi @ (zz[e] @ psi)) for e in edges]))


def manifold(H, k=6, tol=1e-10):
    w, v = spla.eigsh(H, k=k, which="SA", tol=1e-12)
    o = np.argsort(w)
    w, v = w[o], v[:, o]
    keep = np.abs(w - w[0]) < tol
    return w[keep], v[:, keep]


def sz_total_diag(n):
    """Diagonal of total Sz in the computational basis (sum of sigma_z eigenvalues)."""
    idx = np.arange(2 ** n)
    return np.array([n - 2 * bin(i).count("1") for i in idx])


def main() -> int:
    edges = sierpinski(2)
    bond, zz = build(N, edges)
    defect = edges[1]
    out = {}

    print(f"SG(2): N={N}, {len(edges)} edges, defect {defect}\n")

    # ---- 1. is E invariant across the degenerate ground manifold?
    print("1. E across the degenerate ground manifold")
    for s in (0.0, 0.5, 1.0):
        H = H_at(N, edges, bond, defect, s)
        w, V = manifold(H)
        vals = []
        rng = np.random.default_rng(7)
        for _ in range(12):
            c = rng.standard_normal(V.shape[1])
            psi = V @ (c / np.linalg.norm(c))
            vals.append(E_of(psi / np.linalg.norm(psi), edges, zz))
        lo, hi, mu = min(vals), max(vals), float(np.mean(vals))
        print(f"   s={s:<4} degeneracy={V.shape[1]}  E in [{lo:.4f}, {hi:.4f}]  "
              f"spread={hi-lo:.4f} = {(hi-lo)/mu*100:.0f}% of mean")
        out[f"full_s{s}"] = {"deg": int(V.shape[1]), "min": lo, "max": hi, "spread_pct": (hi-lo)/mu*100}

    # ---- 2. does fixing the Sz sector make it well defined? (the fix, not the refutation)
    print("\n2. the same, restricted to a fixed total-Sz sector")
    szd = sz_total_diag(N)
    for s in (0.0, 0.5, 1.0):
        H = H_at(N, edges, bond, defect, s)
        for target in (1, -1):
            mask = np.where(szd == target)[0]
            if not len(mask):
                continue
            Hs = H[mask][:, mask]
            w, V = manifold(Hs, k=6)
            vals = []
            rng = np.random.default_rng(7)
            for _ in range(8):
                c = rng.standard_normal(V.shape[1])
                psi_s = V @ (c / np.linalg.norm(c))
                psi = np.zeros(2 ** N)
                psi[mask] = psi_s / np.linalg.norm(psi_s)
                vals.append(E_of(psi, edges, zz))
            lo, hi, mu = min(vals), max(vals), float(np.mean(vals))
            print(f"   s={s:<4} Sz={target:+d}  dim={len(mask)}  degeneracy={V.shape[1]}  "
                  f"E in [{lo:.4f}, {hi:.4f}]  spread={(hi-lo)/mu*100:.0f}%")
            out[f"sz{target}_s{s}"] = {"deg": int(V.shape[1]), "spread_pct": (hi-lo)/mu*100}
            break

    # ---- 3. the control that must show ZERO spread
    print("\n3. control: a NON-degenerate system must give identical E from any start vector")
    small = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]
    n2 = 4
    b2, zz2 = build(n2, small)
    H2 = H_at(n2, small, b2, (0, 2), 0.37)          # asymmetric -> expect a unique ground state
    w2, V2 = manifold(H2, k=4)
    vals = []
    rng = np.random.default_rng(3)
    for _ in range(6):
        c = rng.standard_normal(V2.shape[1])
        psi = V2 @ (c / np.linalg.norm(c))
        vals.append(E_of(psi / np.linalg.norm(psi), small, zz2))
    print(f"   degeneracy={V2.shape[1]}  E spread={max(vals)-min(vals):.2e}")
    ok = V2.shape[1] == 1 and (max(vals) - min(vals)) < 1e-9
    print(f"   control behaves as it must: {ok}"
          + ("" if ok else "   <-- the method itself is noisy; findings above are NOT usable"))
    out["control_ok"] = bool(ok)

    json.dump(out, open(__file__.replace(".py", ".result.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
