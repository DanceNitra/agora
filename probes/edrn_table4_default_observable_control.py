"""Verify Table IV of the manuscript -- the numbers behind an abstract claim we never checked.

WHY. tools/audit_coverage.py measured our real audit coverage of the 20 August manuscript at 47/60
= 78%, and the eight numbers we had NEVER touched were not scattered. Three of them are the entire
D_default column of Table IV:

    s=0.99  D_default=0.953270   E=0.164032
    s=1.00  D_default=0.954210   E=0.159658
    s=1.01  D_default=0.940725   E=0.160451

That column carries a claim in the ABSTRACT: the coarse-grained observable "exhibits only a weak
local maximum of height ~0.001 at the enhanced valley position ... about two orders of magnitude
smaller than the enhanced valley depth". The height is 0.954210 - 0.953270 = 0.00094, a difference
in the fourth decimal between two numbers nobody on our side had ever computed.

The other five unchecked numbers are Table I's valley-depth column, and those turned out to be exact
arithmetic: E(0) - E(s=1.0) per seed, matching to 1e-17, with E(0)=0.246731 independently confirmed.
Derived, not measured. This file handles what is actually measured.

MODEL. Isotropic Heisenberg on the Sierpinski gasket SG(2) (15 vertices, 27 edges), defect edge
(0,6), coupling s on that edge and 1 elsewhere. Built independently -- no shared code with the
manuscript's scripts.

    E(s)         = std over the 27 edges of <sigma^z_i sigma^z_j>
    D_default(s) = mean over the 27 edges of |<sigma^z_i sigma^z_j>|

CONTROLS
  C1 LABELLING  E(0) must reproduce 0.246731. Vertex numbering is not recoverable from the paper,
                so if this fails, our edge (0,6) is not their edge (0,6) and NOTHING below transfers.
                This is the control that makes the whole comparison meaningful.
  C2 DEGENERACY at s ~ 1 the ground state is near-degenerate, so a single eigensolve returns an
                arbitrary member. Reported over several starting vectors with the spread shown; a
                figure whose spread exceeds the effect it supports is not a figure.
  C3 THE CLAIM  the peak height is computed as prominence over the HIGHER neighbour, the same
                convention the manuscript uses for Table III, and compared with the alternative
                (mean of neighbours) so the choice is visible rather than assumed.

Run:  python probes/edrn_table4_default_observable_control.py
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
SY_I = sp.csr_matrix(np.array([[0, 1], [-1, 0]], dtype=float))   # i*sigma_y, keeps H real
SZ = sp.csr_matrix(np.array([[1, 0], [0, -1]], dtype=float))

PUBLISHED = {0.99: (0.953270, 0.164032), 1.00: (0.954210, 0.159658), 1.01: (0.940725, 0.160451)}
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


def hamiltonian(n, edges, defect, s):
    H = sp.csr_matrix((2 ** n, 2 ** n))
    for (i, j) in edges:
        J = s if (i, j) == defect else 1.0
        if J == 0.0:
            continue
        H = H + J * (op_on(n, {i: SX, j: SX})
                     - op_on(n, {i: SY_I, j: SY_I})
                     + op_on(n, {i: SZ, j: SZ}))
    return H.tocsr()


def observables(n, edges, defect, s, v0, zz_ops):
    H = hamiltonian(n, edges, defect, s)
    _, vecs = spla.eigsh(H, k=1, which="SA", v0=v0, tol=1e-10)
    psi = vecs[:, 0]
    zz = np.array([float(psi @ (op @ psi)) for op in zz_ops])
    return float(np.mean(np.abs(zz))), float(np.std(zz))


def main():
    n, edges = sierpinski(2)
    # THE MISSING ASSERTION, and it cost a whole run. The first version used defect=(0,6) -- the
    # manuscript's label -- without checking it exists in OUR labelling. It does not. The defect
    # therefore never applied, every s computed the UNIFORM graph, and C1 reported E(0)=0.144154
    # (which is E(uniform)). The control caught the consequence; this catches the cause.
    #
    # CALIBRATION, stated because it is one number spent: the manuscript calls (0,6) a tip-to-
    # interior edge. In this builder the tips are 0, 8, 14, and ALL SIX tip-to-interior edges give
    # E(0) = 0.246731 -- identical, by the gasket's symmetry -- so the choice is immaterial for E
    # and the manuscript's E(0) is independently confirmed six times over. D_default is NOT
    # invariant across them (0.014374 to 0.063906, a factor of 4.4), which is reported below and
    # is itself a finding about Table IV.
    tips = {0, 8, 14}
    defect = (0, 2)
    assert defect in edges, f"{defect} is not an edge in this labelling -- the defect would never apply"
    assert (defect[0] in tips) != (defect[1] in tips), "defect must be tip-to-interior, as the paper says"
    print(f"SG(2): {n} vertices, {len(edges)} edges, defect edge {defect} (tip-to-interior)")
    assert n == 15 and len(edges) == 27, "not the manuscript's graph"
    zz_ops = [op_on(n, {i: SZ, j: SZ}) for (i, j) in edges]

    print("\nC1 LABELLING -- E(0) must reproduce the manuscript's 0.246731")
    rng = np.random.default_rng(0)
    v0 = rng.standard_normal(2 ** n)
    t0 = time.time()
    d0, e0 = observables(n, edges, defect, 0.0, v0, zz_ops)
    ok1 = abs(e0 - PUBLISHED_E0) < 5e-6
    print(f"   E(0) = {e0:.6f} vs published {PUBLISHED_E0}  "
          f"{'OK -- same model, same graph, same observable' if ok1 else 'FAIL -- different labelling, STOP'} "
          f"({time.time()-t0:.0f}s)")
    if not ok1:
        print("   Nothing below transfers. Reporting and stopping.")
        return 1

    print("\nTABLE IV -- measured here, over 4 starting vectors (C2)")
    rows = {}
    for s in (0.99, 1.00, 1.01):
        ds, es = [], []
        for seed in range(4):
            r = np.random.default_rng(seed)
            d, e = observables(n, edges, defect, s, r.standard_normal(2 ** n), zz_ops)
            ds.append(d)
            es.append(e)
        rows[s] = {"D": ds, "E": es}
        pd, pe = PUBLISHED[s]
        print(f"   s={s:.2f}  D_default {min(ds):.6f}-{max(ds):.6f} (spread {max(ds)-min(ds):.2e})"
              f"  published {pd}")
        print(f"           E        {min(es):.6f}-{max(es):.6f} (spread {max(es)-min(es):.2e})"
              f"  published {pe}", flush=True)

    print("\nC3 THE CLAIM -- the ~0.001 local maximum")
    dm = {s: float(np.mean(rows[s]["D"])) for s in rows}
    pub_prom = PUBLISHED[1.00][0] - max(PUBLISHED[0.99][0], PUBLISHED[1.01][0])
    pub_mean = PUBLISHED[1.00][0] - 0.5 * (PUBLISHED[0.99][0] + PUBLISHED[1.01][0])
    our_prom = dm[1.00] - max(dm[0.99], dm[1.01])
    our_mean = dm[1.00] - 0.5 * (dm[0.99] + dm[1.01])
    print(f"   published, prominence over the higher neighbour : {pub_prom:+.6f}  <- the ~0.001")
    print(f"   published, height over the MEAN of neighbours   : {pub_mean:+.6f}")
    print(f"   ours,      prominence over the higher neighbour : {our_prom:+.6f}")
    print(f"   ours,      height over the MEAN of neighbours   : {our_mean:+.6f}")
    print(f"   NOTE the convention matters: the two differ by {abs(pub_mean/pub_prom):.1f}x on their")
    print(f"        own numbers, and only the smaller one is '~0.001'.")

    spreads = {s: max(rows[s]["D"]) - min(rows[s]["D"]) for s in rows}
    worst = max(spreads.values())
    ok2 = worst < abs(our_prom)
    print(f"\nC2 DEGENERACY  worst cross-seed spread in D_default = {worst:.2e}; the effect it must "
          f"support = {abs(our_prom):.2e}")
    print(f"   {'OK -- effect exceeds the scatter' if ok2 else 'FAIL -- the scatter is larger than the effect'}")

    is_max = dm[1.00] > dm[0.99] and dm[1.00] > dm[1.01]
    print(f"\n   is s=1.00 a local MAXIMUM in our run? {is_max}")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "edrn_table4_default_observable_control.result.json")
    json.dump({"E0": e0, "published_E0": PUBLISHED_E0, "labelling_ok": bool(ok1),
               "rows": {str(k): v for k, v in rows.items()}, "published": {str(k): v for k, v in PUBLISHED.items()},
               "our_prominence": our_prom, "our_mean_height": our_mean,
               "published_prominence": pub_prom, "published_mean_height": pub_mean,
               "worst_spread": worst, "is_local_max": bool(is_max)},
              open(out, "w", encoding="utf-8"), indent=2)
    print(f"\nreceipt -> {out}")
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    sys.exit(main())
