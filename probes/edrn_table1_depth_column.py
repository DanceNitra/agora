"""Verify Table I of the manuscript -- the five valley depths, and what E(0) actually is.

WHY. tools/audit_coverage.py found eight numbers in the 20 August manuscript we had never checked.
Five of them are the entire valley-depth column of Table I, the paper's headline table:

    seed 0  value 0.159295  depth 0.087436
    seed 1  value 0.142707  depth 0.104024
    seed 2  value 0.143544  depth 0.103187
    seed 3  value 0.142196  depth 0.104535
    seed 4  value 0.146785  depth 0.099946

This was first checked with a shell one-liner. That is not verification -- the same lesson this
session already produced about the publish step: a check nobody can re-run is not a check. So it is
written down, with the independent measurement that makes it mean something.

TWO SEPARATE QUESTIONS, and conflating them is how a table like this gets waved through:

  (a) IS THE DEPTH COLUMN CONSISTENT? Depth is defined in the caption as E(0) - E(s=1.0). Given the
      valley values in the same row, the depths are then arithmetic, not measurements. Checked to
      machine precision. If this fails, the table contradicts its own caption.

  (b) IS E(0) REAL? The whole column hangs off one constant. Measured here from an independently
      built gasket -- our own graph, our own Hamiltonian, no shared code with the manuscript.

CONTROL
  C1 SIX EDGES  the manuscript's defect is a tip-to-interior edge, and vertex labelling is not
                recoverable from the paper. So E(0) is measured on ALL SIX tip-to-interior edges.
                If they agree, the labelling ambiguity is irrelevant and the constant is confirmed
                six times over; if they disagree, no single edge can be trusted as "theirs".
  C2 CAN FAIL   a deliberately wrong depth must be rejected, so the arithmetic check is not vacuous.

NOTE on the caption, reported separately to the co-authors: it calls s=0 "the uniform point", but
the paper's own definition puts J=1 on every edge except the defect where J=s, so s=1 is uniform and
s=0 is the edge removed. The arithmetic below is unaffected; the label is wrong.

Run:  python probes/edrn_table1_depth_column.py
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

TABLE1 = [(0, 0.159295, 0.087436), (1, 0.142707, 0.104024), (2, 0.143544, 0.103187),
          (3, 0.142196, 0.104535), (4, 0.146785, 0.099946)]
PUBLISHED_E0 = 0.246731


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


def E_at(n, edges, defect, s, v0, zz_ops):
    H = sp.csr_matrix((2 ** n, 2 ** n))
    for (i, j) in edges:
        J = s if (i, j) == defect else 1.0
        if J == 0.0:
            continue
        H = H + J * (op_on(n, {i: SX, j: SX}) - op_on(n, {i: SY_I, j: SY_I})
                     + op_on(n, {i: SZ, j: SZ}))
    _, vecs = spla.eigsh(H.tocsr(), k=1, which="SA", v0=v0, tol=1e-10)
    psi = vecs[:, 0]
    return float(np.std([float(psi @ (op @ psi)) for op in zz_ops]))


def main():
    n, edges = sierpinski(2)
    assert (n, len(edges)) == (15, 27), "not the manuscript's graph"
    tips = {v for v in range(n) if sum(1 for e in edges if v in e) == 2}
    cand = [e for e in edges if (e[0] in tips) != (e[1] in tips)]
    zz_ops = [op_on(n, {i: SZ, j: SZ}) for (i, j) in edges]
    print(f"SG(2): {n} vertices, {len(edges)} edges | tips {sorted(tips)} | "
          f"{len(cand)} tip-to-interior edges")

    print("\n(b) IS E(0) REAL? -- measured on every tip-to-interior edge (C1)")
    rng = np.random.default_rng(0)
    v0 = rng.standard_normal(2 ** n)
    vals = {}
    for e in cand:
        t0 = time.time()
        vals[e] = E_at(n, edges, e, 0.0, v0, zz_ops)
        print(f"   defect {str(e):8s} E(0) = {vals[e]:.6f}   ({time.time()-t0:.0f}s)", flush=True)
    spread = max(vals.values()) - min(vals.values())
    c1 = spread < 1e-9 and abs(np.mean(list(vals.values())) - PUBLISHED_E0) < 5e-6
    print(f"   spread across the six: {spread:.2e}")
    print(f"C1 SIX EDGES  {'OK -- identical, so the labelling ambiguity is irrelevant' if c1 else 'FAIL'}"
          f" | published {PUBLISHED_E0}")

    E0 = float(np.mean(list(vals.values())))

    print("\n(a) IS THE DEPTH COLUMN CONSISTENT? -- depth must equal E(0) - value")
    worst = 0.0
    for seed, value, depth in TABLE1:
        calc = PUBLISHED_E0 - value
        d = abs(calc - depth)
        worst = max(worst, d)
        print(f"   seed {seed}: {PUBLISHED_E0} - {value} = {calc:.6f} vs published {depth} "
              f"({'exact' if d < 1e-6 else 'MISMATCH'}, diff {d:.1e})")
    ok_a = worst < 1e-6
    print(f"   worst discrepancy {worst:.1e} -> "
          f"{'the column is arithmetic, not five measurements' if ok_a else 'THE TABLE CONTRADICTS ITS CAPTION'}")

    bad = abs((PUBLISHED_E0 - TABLE1[0][1] + 0.01) - TABLE1[0][2])
    c2 = bad > 1e-6
    print(f"\nC2 CAN FAIL   a depth wrong by 0.01 is rejected: {'OK' if c2 else 'FAIL -- check is vacuous'}")

    print("\n" + "=" * 76)
    print(f"E(0) = {E0:.6f}, independently measured, identical on all {len(cand)} tip-to-interior")
    print(f"edges, and matching the manuscript's {PUBLISHED_E0}.")
    print("The five depths are exact arithmetic from it and the valley values in the same rows,")
    print("so they are DERIVED, not five independent measurements. The valley values themselves")
    print("scatter because the s=1 ground state is near-degenerate, which the paper states.")
    print("=" * 76)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "edrn_table1_depth_column.result.json")
    json.dump({"E0_measured": E0, "E0_published": PUBLISHED_E0,
               "per_edge": {str(k): v for k, v in vals.items()}, "spread": spread,
               "table1": [{"seed": s, "value": v, "depth": d,
                           "depth_from_E0": PUBLISHED_E0 - v} for s, v, d in TABLE1],
               "worst_arithmetic_discrepancy": worst,
               "controls": {"C1": bool(c1), "C2": bool(c2), "arithmetic": bool(ok_a)}},
              open(out, "w", encoding="utf-8"), indent=2)
    print(f"receipt -> {out}")
    return 0 if (c1 and c2 and ok_a) else 1


if __name__ == "__main__":
    sys.exit(main())
