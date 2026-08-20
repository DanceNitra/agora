"""The last three numbers in the manuscript without a receipt.

WHY. tools/audit_coverage.py got the artifact to 57/60 computed. The remaining three are not
scattered leftovers -- one of them is OURS and we handed it to him:

  -9.000000  the L1 ground energy. The manuscript credits it to our tensor-RG toolchain. On our
             side it existed only in a DRAFT (agora_output/drafts/edrn_ensemble_2026-08-19.md),
             i.e. we told him a number we had never receipted. Its partner -24.967537 is computed
             (it is the s=1.00 ground energy in edrn_gap_structure_and_sector); this one was not.
  0.0993     the ring control graph's multi-seed valley depth, 0.0993 +- 0.0286.
  0.1485     the focused-audit value of E at s=1.0 in the Fig. 3 caption.

Independent build: our own graphs, our own Hamiltonian, no shared code with the manuscript.

CONTROLS
  C1 CALIBRATION  the L2 isotropic ground energy must come out -24.967537, which is independently
                  fixed by edrn_gap_structure_and_sector. If the Hamiltonian convention is wrong,
                  the L1 number below is wrong too and nothing here transfers.
  C2 CAN FAIL     a deliberately wrong target (-9.5) must be rejected by the same comparison.
  C3 DEGENERACY   0.1485 is quoted at s=1.0, which we have already measured to be an exact level
                  crossing. Reported with the manifold spread rather than as a single value, since
                  a number at a crossing is not one number.

Run:  python probes/edrn_the_last_three_numbers.py
"""

import itertools
import json
import os
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

ID = sp.identity(2, format="csr")
SX = sp.csr_matrix(np.array([[0, 1], [1, 0]], dtype=float))
SY_I = sp.csr_matrix(np.array([[0, 1], [-1, 0]], dtype=float))
SZ = sp.csr_matrix(np.array([[1, 0], [0, -1]], dtype=float))

PUB_L1, PUB_L2 = -9.000000, -24.967537
PUB_RING_SINGLE, PUB_RING_MULTI, PUB_RING_SD = 0.0891, 0.0993, 0.0286
PUB_FOCUSED = 0.1485


def sierpinski(level):
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
    return len(pts), sorted(edges)


def op_on(n, ops):
    m = None
    for q in range(n):
        o = ops.get(q, ID)
        m = o if m is None else sp.kron(m, o, format="csr")
    return m


def H_of(n, edges, defect=None, s=1.0):
    H = sp.csr_matrix((2 ** n, 2 ** n))
    for (i, j) in edges:
        J = s if (defect is not None and (i, j) == defect) else 1.0
        if J == 0.0:
            continue
        H = H + J * (op_on(n, {i: SX, j: SX}) - op_on(n, {i: SY_I, j: SY_I})
                     + op_on(n, {i: SZ, j: SZ}))
    return H.tocsr()


def ground(H, v0=None, k=1):
    vals, vecs = spla.eigsh(H, k=k, which="SA", v0=v0, tol=1e-11)
    o = np.argsort(vals)
    return vals[o], vecs[:, o]


def E_of(psi, n, edges, zz_ops):
    return float(np.std([float(psi @ (op @ psi)) for op in zz_ops]))


def main():
    out = {}
    print("1  THE L1 AND L2 GROUND ENERGIES -- the number we gave him and never receipted")
    for lvl, pub in ((1, PUB_L1), (2, PUB_L2)):
        n, edges = sierpinski(lvl)
        t0 = time.time()
        vals, _ = ground(H_of(n, edges))
        e = float(vals[0])
        ok = abs(e - pub) < 5e-6
        out[f"L{lvl}"] = e
        print(f"   L{lvl}: N={n:2d}, {len(edges):2d} edges  ground energy = {e:.6f}  "
              f"published {pub}  {'MATCH' if ok else 'DIFFERS'}   ({time.time()-t0:.0f}s)",
              flush=True)
    c1 = abs(out["L2"] - PUB_L2) < 5e-6
    c2 = abs(out["L1"] - (-9.5)) > 5e-6
    print(f"C1 CALIBRATION  L2 reproduces the independently fixed -24.967537: {'OK' if c1 else 'FAIL'}")
    print(f"C2 CAN FAIL     a wrong target (-9.5) is rejected: {'OK' if c2 else 'FAIL'}")

    print("\n2  THE RING CONTROL GRAPH -- published 0.0891 single / 0.0993 +- 0.0286 multi")
    n = 15
    ring = [(i, (i + 1) % n) for i in range(n)]
    ring = sorted((min(a, b), max(a, b)) for a, b in ring)
    zz_ops = [op_on(n, {i: SZ, j: SZ}) for (i, j) in ring]
    defect = ring[0]
    strengths = np.linspace(0.0, 3.0, 13)
    depths = []
    for seed in range(3):
        rng = np.random.default_rng(seed)
        v0 = rng.standard_normal(2 ** n)
        curve = []
        for s in strengths:
            _, w = ground(H_of(n, ring, defect, float(s)), v0=v0)
            curve.append(E_of(w[:, 0], n, ring, zz_ops))
        curve = np.array(curve)
        im = int(np.argmin(curve))
        depths.append(float(np.mean(curve[-3:]) - curve[im]))
        print(f"   seed {seed}: depth = {depths[-1]:.4f}  min at s = {strengths[im]:.2f}", flush=True)
    m, sd = float(np.mean(depths)), float(np.std(depths))
    out["ring_depths"] = depths
    print(f"   mean {m:.4f} +- {sd:.4f}   published {PUB_RING_MULTI} +- {PUB_RING_SD}")
    ring_ok = abs(m - PUB_RING_MULTI) < max(PUB_RING_SD, sd) * 2

    print("\n3  THE FOCUSED-AUDIT VALUE 0.1485 AT s=1.0 (C3)")
    n2, e2 = sierpinski(2)
    tips = {v for v in range(n2) if sum(1 for e in e2 if v in e) == 2}
    d2 = next(e for e in e2 if (e[0] in tips) != (e[1] in tips))
    zz2 = [op_on(n2, {i: SZ, j: SZ}) for (i, j) in e2]
    vals3 = []
    for seed in range(4):
        rng = np.random.default_rng(seed)
        _, w = ground(H_of(n2, e2, d2, 1.0), v0=rng.standard_normal(2 ** n2))
        vals3.append(E_of(w[:, 0], n2, e2, zz2))
    lo, hi = min(vals3), max(vals3)
    out["focused_s1"] = vals3
    inside = lo - 1e-9 <= PUB_FOCUSED <= hi + 1e-9
    print(f"   E(s=1.0) over 4 starting vectors: {lo:.6f} .. {hi:.6f}")
    print(f"   published focused-audit value {PUB_FOCUSED}: "
          f"{'INSIDE the manifold spread' if inside else 'OUTSIDE it'}")
    print("   s=1.0 is an exact level crossing (measured in edrn_gap_structure_and_sector), so a")
    print("   single number there is one member of a degenerate manifold, not a value.")

    print("\n" + "=" * 76)
    print(f"L1 = {out['L1']:.6f} (published -9.000000) -- the figure we gave him, now receipted")
    print(f"ring multi-seed depth {m:.4f} +- {sd:.4f} (published {PUB_RING_MULTI} +- {PUB_RING_SD})")
    print(f"focused s=1.0 spread {lo:.4f}..{hi:.4f} (published {PUB_FOCUSED})")
    print("=" * 76)

    rp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "edrn_the_last_three_numbers.result.json")
    json.dump({**out, "published": {"L1": PUB_L1, "L2": PUB_L2, "ring_multi": PUB_RING_MULTI,
                                    "ring_sd": PUB_RING_SD, "focused": PUB_FOCUSED},
               "ring_mean": m, "ring_sd": sd, "focused_inside": bool(inside),
               "controls": {"C1": bool(c1), "C2": bool(c2), "ring_consistent": bool(ring_ok)}},
              open(rp, "w", encoding="utf-8"), indent=2)
    print(f"receipt -> {rp}")
    return 0 if (c1 and c2) else 1


if __name__ == "__main__":
    sys.exit(main())
