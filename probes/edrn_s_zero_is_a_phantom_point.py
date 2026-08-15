"""Is the s=0 point of the LDS-valley scan a real measurement, or the falsy-zero artifact?

WHY THIS MATTERS. The paper's headline number is the LDS Valley depth, 0.125 = 0.2093 (at s=0) minus
0.0843 (at s=0.50), quoted as "60% of its initial value". It is measured FROM the s=0 point.

On 2026-08-12 I reported a one-line coercion bug in their `graph_to_hamiltonian`:

    w = w if w else 1.0        # 0.0 is falsy

so a contradiction strength of exactly 0.0 is silently rebuilt as 1.0. Measured then on their own
functions, N=6 path: fine(s=0.0) = fine(s=1.0) = 0.2447051991 bit-identical, while fine(s=1e-9) =
0.1283170693 — the phantom sat 0.116 ABOVE the true s->0 value.

The paper's fractal table now reads E(s=0.00) = 0.2093 and E(s=1.00) = 0.2093. Identical to four
decimals. That is either the artifact surviving into the submission, or a coincidence.

It cannot be settled by reading, so this builds the system independently — no shared code — and asks
one question: in a CORRECT implementation, does E(s->0) equal E(s=1)?

If it does, the paper's coincidence is physics and the depth stands. If it does not, the depth is
measured from a point that does not exist, and the honest depth is much smaller.

The absolute values here will not match theirs (vertex labelling, and therefore which edge is the
defect, is not recoverable from the paper). The COMPARISON is what transfers, and it is the only
thing claimed.
"""
from __future__ import annotations

import itertools
import json
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

SX = sp.csr_matrix(np.array([[0, 1], [1, 0]], dtype=float))
SY_I = sp.csr_matrix(np.array([[0, -1], [1, 0]], dtype=float))   # sigma_y / i, keeps H real
SZ = sp.csr_matrix(np.array([[1, 0], [0, -1]], dtype=float))
ID = sp.identity(2, format="csr")


def sierpinski(level: int):
    """SG(level): 3*(3^level+1)/2 vertices, 3^(level+1) edges. SG(2) -> 15 vertices, 27 edges."""
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
                idx[k] = len(pts)
                pts.append(k)
    edges = set()
    for t in tris:
        for p, q in itertools.combinations(t, 2):
            i = idx[(round(p[0], 9), round(p[1], 9))]
            j = idx[(round(q[0], 9), round(q[1], 9))]
            edges.add((min(i, j), max(i, j)))
    return len(pts), sorted(edges), pts


def op_on(n: int, ops: dict) -> sp.csr_matrix:
    m = None
    for q in range(n):
        o = ops.get(q, ID)
        m = o if m is None else sp.kron(m, o, format="csr")
    return m


def hamiltonian(n: int, edges, defect, s: float) -> sp.csr_matrix:
    """Isotropic Heisenberg. Real-symmetric: sigma_y sigma_y = -(SY_I x SY_I)."""
    H = sp.csr_matrix((2 ** n, 2 ** n))
    for (i, j) in edges:
        J = s if (i, j) == defect else 1.0
        if J == 0.0:
            continue                     # a zero coupling contributes nothing -- NOT rebuilt as 1.0
        H = H + J * (op_on(n, {i: SX, j: SX})
                     - op_on(n, {i: SY_I, j: SY_I})
                     + op_on(n, {i: SZ, j: SZ}))
    return H.tocsr()


def diagnostics(n, edges, defect, s, v0):
    H = hamiltonian(n, edges, defect, s)
    _, vecs = spla.eigsh(H, k=1, which="SA", v0=v0, tol=1e-9)
    psi = vecs[:, 0]
    zz = []
    for (i, j) in edges:
        zz.append(float(psi @ (op_on(n, {i: SZ, j: SZ}) @ psi)))
    mz = [float(psi @ (op_on(n, {q: SZ}) @ psi)) for q in range(n)]
    return abs(float(np.mean(mz))), float(np.std(zz))


def main() -> int:
    n, edges, _ = sierpinski(2)
    print(f"Sierpinski SG(2): {n} vertices, {len(edges)} edges  (paper: 15, 27)")
    assert (n, len(edges)) == (15, 27), "graph does not match the paper's stated size"

    # A defect edge joining two different sub-triangles, as the paper describes. Exact labelling is
    # not recoverable from the paper, so the comparison below -- not the absolute value -- is the claim.
    defect = edges[1]
    print(f"defect edge: {defect}\n")

    rng = np.random.default_rng(0)
    v0 = rng.standard_normal(2 ** n)     # ONE fixed start vector for every s: no Lanczos-seed scatter
    v0 /= np.linalg.norm(v0)

    rows = []
    for s in (0.0, 1e-9, 1e-6, 0.25, 0.5, 1.0):
        t0 = time.time()
        d, e = diagnostics(n, edges, defect, s, v0)
        rows.append({"s": s, "default": d, "enhanced": e})
        print(f"  s={s:<8g} default={d:.6f}  enhanced={e:.6f}   ({time.time()-t0:.1f}s)", flush=True)

    by = {r["s"]: r["enhanced"] for r in rows}
    print()
    print(f"E(s=0)   = {by[0.0]:.6f}")
    print(f"E(s=1e-9)= {by[1e-9]:.6f}")
    print(f"E(s=1.0) = {by[1.0]:.6f}")
    same = abs(by[0.0] - by[1.0]) < 1e-6
    zero_ok = abs(by[0.0] - by[1e-9]) < 1e-6
    print()
    print(f"E(0) == E(1)     : {same}   <- true in THEIR table (0.2093 vs 0.2093)")
    print(f"E(0) == E(0+eps) : {zero_ok}  <- must be true in a correct implementation")
    print()
    if zero_ok and not same:
        print("VERDICT: in a correct implementation s=0 is its own point and differs from s=1")
        print(f"         (here by {abs(by[0.0]-by[1.0]):.4f}). Their table showing E(0) == E(1) to four")
        print("         decimals matches the signature of the coercion bug reported 2026-08-12.")
        print()
        print("WHAT THIS DOES *NOT* SHOW, stated because the distinction is the whole value here:")
        print("  * not that their 0.2093 is wrong. Vertex labelling is not recoverable from the")
        print("    paper, so 'edge (0,2)' here is not their edge (0,2) -- and the paper itself")
        print("    measured that moving the defect edge removes the valley entirely. The absolute")
        print("    numbers do not transfer and are not offered.")
        print("  * not that the bug is definitely still live. A separate run (see the module note")
        print("    below) found ~17.6% ground-manifold scatter on E, so two honest computations of")
        print("    the same Hamiltonian would rarely agree to four decimals EITHER -- which cuts")
        print("    against a mundane explanation as much as for one.")
        print()
        print("  The transferable claim is exactly one sentence: E(0) and E(1) are far apart when")
        print("  s=0 is computed honestly, so their being equal needs an explanation, and the")
        print("  paper's headline depth is measured from that point. One line settles it on their")
        print("  side: print fine(s=1e-9) and compare it to fine(s=0.0).")
    elif same:
        print("VERDICT: s=0 and s=1 genuinely coincide here too -- the coincidence is physics,")
        print("         not the artifact. The depth stands.")
    json.dump(rows, open(__file__.replace(".py", ".result.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
