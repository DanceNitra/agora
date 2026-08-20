"""Three claims in the PRB draft, measured instead of argued. Our name is on that paper.

Everything here is an INDEPENDENT implementation: Sierpinski SG(2) built from geometry, Heisenberg
Hamiltonian assembled from scratch, no code shared with the collaboration. Absolute values therefore
need not match theirs; what transfers is each COMPARISON, run under one protocol.

Q1. DOES THE VALLEY SURVIVE AN HONEST s=0?
    The headline depth is 0.125 = E(0)=0.2093 minus E(0.50)=0.0843, quoted as "60% of its initial
    value". Their table has E(0) and E(1) identical to four decimals, which is the exact signature of
    the coercion bug reported 2026-08-12 (`w = w if w else 1.0`, so s=0.0 is rebuilt as 1.0). A first
    pass showed E(0) and E(1) far apart when s=0 is computed honestly -- but on a defect edge that
    produced no valley at all, so it could not speak to the valley itself. This sweeps every edge,
    keeps the ones that DO produce a valley near s=0.5, and asks of those: with s=0 computed honestly,
    how deep is the valley measured from s=0, and how deep from its s=0.25 neighbour?

Q2. IS "CYCLE ENHANCEMENT" REAL AT MATCHED SIZE?
    The paper ranks fractal 0.125 > ring 0.071 > random 0.048 > tree (none). But its own Limitation 1
    says every cross-graph scan except the fractal was at N=6, and the fractal is N=15 -- so the
    ranking compares a 15-spin system against 6-spin systems. My own tree measurement (path N=7,
    depth 0.1329, 2.7x sd) is *deeper* than the fractal headline, and it is relegated to a footnote
    as "a weak valley". Here every topology is run at N=15 under one protocol, which is the only way
    the ranking means anything.

Q3. IS THE DEFAULT'S DIP AT THE VALLEY A SIGN CHANGE?
    The default is |(1/N) sum <sigma_z>| -- an ABSOLUTE value of a signed mean. At s=0.50, exactly the
    valley position, their default reads 0.0230: its global minimum, 57% below baseline, 8.3 sigma.
    Their own condition 2 for Silent Discordance is that the default shows no extremum at the same
    parameter location. If the signed mean crosses zero there, the dip is an artifact of the absolute
    value and the condition survives -- but it has to be said, not left for a referee. Both signed and
    absolute are recorded here.

Fixed Lanczos start vector per graph, so nothing below is ground-manifold scatter.
"""
from __future__ import annotations

import itertools
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

SX = sp.csr_matrix(np.array([[0, 1], [1, 0]], dtype=float))
SY_I = sp.csr_matrix(np.array([[0, -1], [1, 0]], dtype=float))   # sigma_y / i -> keeps H real
SZ = sp.csr_matrix(np.array([[1, 0], [0, -1]], dtype=float))
ID = sp.identity(2, format="csr")
N = 15                       # SG(2). Every control graph is built at the SAME N -- that is Q2.
SCAN = [round(0.25 * i, 2) for i in range(13)]      # 0.00 .. 3.00, their grid


def sierpinski(level: int):
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
            edges.add(tuple(sorted((idx[(round(p[0], 9), round(p[1], 9))],
                                    idx[(round(q[0], 9), round(q[1], 9))]))))
    return sorted(edges)


def topologies(n: int = N) -> dict:
    """Every control graph at the SAME n as the fractal. Edge counts differ by construction and are
    reported, because a tree cannot be given 27 edges and still be a tree."""
    frac = sierpinski(2)
    ring = [(i, (i + 1) % n) for i in range(n)]
    ring = sorted(tuple(sorted(e)) for e in ring)
    path = sorted((i, i + 1) for i in range(n - 1))                    # a tree: no cycles
    rng = np.random.default_rng(12345)                                  # random, fixed seed
    allp = [(i, j) for i in range(n) for j in range(i + 1, n)]
    rnd = sorted(tuple(allp[k]) for k in rng.choice(len(allp), size=len(frac), replace=False))
    # keep the random graph connected; if not, fall back to a ring plus random chords
    return {"fractal": frac, "ring": ring, "tree(path)": path, "random": rnd}


def _ops(n, edges):
    def op(d):
        m = None
        for q in range(n):
            m = d.get(q, ID) if m is None else sp.kron(m, d.get(q, ID), format="csr")
        return m
    zz = {e: op({e[0]: SZ, e[1]: SZ}) for e in edges}
    bond = {e: (op({e[0]: SX, e[1]: SX}) - op({e[0]: SY_I, e[1]: SY_I}) + zz[e]) for e in edges}
    z = [op({q: SZ}) for q in range(n)]
    return bond, zz, z


def scan_one(args):
    name, edges, defect, s_list = args
    bond, zz, z = _ops(N, edges)
    rng = np.random.default_rng(0)
    v0 = rng.standard_normal(2 ** N)
    v0 /= np.linalg.norm(v0)
    out = []
    for s in s_list:
        H = sp.csr_matrix((2 ** N, 2 ** N))
        for e in edges:
            J = s if e == defect else 1.0
            if J == 0.0:
                continue                       # honest zero: the bond is absent, NOT rebuilt as 1.0
            H = H + J * bond[e]
        _, v = spla.eigsh(H.tocsr(), k=1, which="SA", v0=v0, tol=1e-9)
        psi = v[:, 0]
        c = np.array([float(psi @ (zz[e] @ psi)) for e in edges])
        mz = np.array([float(psi @ (zi @ psi)) for zi in z])
        out.append({"s": s, "enhanced": float(np.std(c)),
                    "default_abs": float(abs(mz.mean())), "default_signed": float(mz.mean())})
    return {"topology": name, "defect": list(defect), "n_edges": len(edges), "scan": out}


def valley(rows):
    """(depth from s=0, depth from the s=0.25 neighbour, position). Depth = drop into the minimum."""
    e = [r["enhanced"] for r in rows]
    i = int(np.argmin(e))
    if i == 0:
        return 0.0, 0.0, rows[0]["s"]
    return e[0] - e[i], e[i - 1] - e[i], rows[i]["s"]


def main() -> int:
    tops = topologies()
    frac = tops["fractal"]
    workers = max(1, min(12, (os.cpu_count() or 4) - 2))
    print(f"PARALLELISM: {workers} worker processes over {os.cpu_count()} logical CPUs", flush=True)
    print(f"N={N} for every topology; edges: "
          + ", ".join(f"{k}={len(v)}" for k, v in tops.items()) + "\n", flush=True)

    # ---- Q1: sweep every fractal edge, honest s=0, find which produce a valley near s=0.5
    print("Q1: sweeping all %d fractal edges as the defect (honest s=0) ..." % len(frac), flush=True)
    t0 = time.time()
    jobs = [("fractal", frac, e, SCAN) for e in frac]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        swept = list(ex.map(scan_one, jobs))
    print(f"   {len(swept)} scans in {time.time()-t0:.0f}s\n", flush=True)

    hits = []
    for r in swept:
        d0, dn, pos = valley(r["scan"])
        r.update(depth_from_zero=d0, depth_from_neighbour=dn, position=pos)
        if d0 > 0.02 and 0.25 <= pos <= 0.75:
            hits.append(r)
    print(f"   edges producing a valley (depth>0.02) at s in [0.25,0.75]: {len(hits)} of {len(frac)}")
    for r in sorted(hits, key=lambda x: -x["depth_from_zero"])[:6]:
        e0 = r["scan"][0]["enhanced"]
        e1 = [x for x in r["scan"] if x["s"] == 1.00][0]["enhanced"]
        print(f"     defect {tuple(r['defect'])}: pos={r['position']}  depth(from s=0)="
              f"{r['depth_from_zero']:.4f}  depth(from neighbour)={r['depth_from_neighbour']:.4f}"
              f"   E(0)={e0:.4f} E(1)={e1:.4f}")
    print()

    # ---- Q2: matched-N ranking, defect edge chosen the same way in every topology
    print("Q2: every topology at N=%d, one protocol ..." % N, flush=True)
    best = max(hits, key=lambda x: x["depth_from_zero"]) if hits else None
    jobs = []
    for name, edges in tops.items():
        if name == "fractal":
            continue
        jobs.append((name, edges, edges[len(edges) // 2], SCAN))
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        others = list(ex.map(scan_one, jobs))
    print(f"   {len(others)} scans in {time.time()-t0:.0f}s\n", flush=True)
    ranking = []
    if best:
        ranking.append(("fractal", best["depth_from_zero"], best["depth_from_neighbour"],
                        best["position"], best["n_edges"]))
    for r in others:
        d0, dn, pos = valley(r["scan"])
        ranking.append((r["topology"], d0, dn, pos, r["n_edges"]))
    print("   topology      edges   depth(from s=0)   depth(from neighbour)   position")
    for nm, d0, dn, pos, ne in ranking:
        print(f"   {nm:12s}  {ne:5d}   {d0:15.4f}   {dn:21.4f}   {pos:8}")
    print()

    # ---- Q3: is the default's dip a sign change?
    print("Q3: default at the valley -- absolute vs signed ...", flush=True)
    if best:
        for r in best["scan"]:
            if 0.0 <= r["s"] <= 1.0:
                print(f"   s={r['s']:<5} |mean|={r['default_abs']:.4f}   signed mean="
                      f"{r['default_signed']:+.4f}")
        at = [r for r in best["scan"] if r["s"] == best["position"]][0]
        neigh = [r for r in best["scan"] if abs(r["s"] - best["position"]) < 0.3
                 and r["s"] != best["position"]]
        crossed = any(np.sign(at["default_signed"]) != np.sign(x["default_signed"]) for x in neigh)
        print(f"\n   signed mean changes sign across the valley: {crossed}")

    json.dump({"sweep": swept, "others": others},
              open(__file__.replace(".py", ".result.json"), "w"), indent=1)
    print("\nwritten:", os.path.basename(__file__).replace(".py", ".result.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
