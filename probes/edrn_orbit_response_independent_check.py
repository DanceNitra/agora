"""Independent check of Li Guanghao's "Same Orbit Implies Same Response" (EDRN repo, 2026-09-24).

Our own exact diagonalization, written without his code. Full 2^N Hilbert space,
H(s) = sum_{(i,j) in E} J_ij sigma_i . sigma_j with the defect edge at coupling s and
every other edge at 1. A degenerate ground manifold (tolerance 1e-8) is averaged, as
in his scripts.

Checks:
  A. His N=7 single-combination table (full space, sorted <sz sz> vector,
     s in linspace(-1.5, 0, 11), values rounded to 12 digits): 6504 / 0 / 382 / 44142.
  B. Hellmann-Feynman: dE0/ds equals <sigma.sigma> on the defect edge, so
     p_S(s) = (1 - dE0/ds) / 4 and p_S never decreases in s (E0 is concave in s).
  C. Where p_S passes 1/2: a continuous root, or a jump over 1/2 at a ground-state
     change, per defect edge, on s in [-2, 2].
  D. The sector formula p_S = (1 - 3<sz sz>)/4 against the true (1 - <sigma.sigma>)/4
     for the lowest state of the Sz = -1/2 sector (N=7), split by total spin.

Run: python -X utf8 probes/edrn_orbit_response_independent_check.py [--workers 16]
Writes probes/edrn_orbit_response_independent_check.result.json and prints progress.
"""
import argparse
import itertools
import json
import os
import sys
import time
from functools import lru_cache
from multiprocessing import Pool

import networkx as nx
import numpy as np
from networkx.algorithms.isomorphism import GraphMatcher

DEG_TOL = 1e-8


@lru_cache(maxsize=None)
def connected_atlas(n):
    return [g for g in nx.graph_atlas_g() if g.number_of_nodes() == n and nx.is_connected(g)]


@lru_cache(maxsize=None)
def sdot_matrix(n, i, j):
    """sigma_i . sigma_j in the computational basis: +1 if bits equal, else -1 plus 2 * swap."""
    dim = 1 << n
    m = np.zeros((dim, dim))
    for b in range(dim):
        bi, bj = (b >> i) & 1, (b >> j) & 1
        if bi == bj:
            m[b, b] = 1.0
        else:
            m[b, b] = -1.0
            m[b ^ (1 << i) ^ (1 << j), b] += 2.0
    return m


def zz_diag(n, i, j):
    b = np.arange(1 << n)
    return np.where(((b >> i) & 1) == ((b >> j) & 1), 1.0, -1.0)


def ground(h):
    w, v = np.linalg.eigh(h)
    k = int(np.sum(np.abs(w - w[0]) < DEG_TOL))
    return w[0], v[:, :k], k


def edge_orbits(g, edges):
    orbit = {e: e for e in edges}
    for phi in GraphMatcher(g, g).isomorphisms_iter():
        for e in edges:
            f = tuple(sorted((phi[e[0]], phi[e[1]])))
            a, b = orbit[e], orbit[f]
            if a != b:
                lo, hi = min(a, b), max(a, b)
                for x in edges:
                    if orbit[x] == hi:
                        orbit[x] = lo
    return orbit


def check_A(args):
    n, gid = args
    g = connected_atlas(n)[gid]
    edges = [tuple(sorted(e)) for e in g.edges()]
    mats = {e: sdot_matrix(n, *e) for e in edges}
    zz = {e: zz_diag(n, *e) for e in edges}
    h0 = sum(mats.values())
    s_vals = np.linspace(-1.5, 0.0, 11)
    curves = {}
    for d in edges:
        c = []
        for s in s_vals:
            _, v, _ = ground(h0 + (s - 1.0) * mats[d])
            p = np.sum(np.abs(v) ** 2, axis=1) / v.shape[1]
            c.append(tuple(np.round(sorted(float(p @ zz[e]) for e in edges), 12)))
        curves[d] = tuple(c)
    orb = edge_orbits(g, edges)
    n_aut = sum(1 for _ in GraphMatcher(g, g).isomorphisms_iter())
    out = {"so_same": 0, "so_diff": 0, "do_same": 0, "do_diff": 0, "do_same_pairs": [], "n_aut": n_aut}
    for e1, e2 in itertools.combinations(edges, 2):
        same_o = orb[e1] == orb[e2]
        same_c = all(np.allclose(a, b, atol=1e-10) for a, b in zip(curves[e1], curves[e2]))
        key = ("so_" if same_o else "do_") + ("same" if same_c else "diff")
        out[key] += 1
        if key == "do_same":
            out["do_same_pairs"].append([list(e1), list(e2)])
    return gid, out


def total_spin(v, n):
    """S from <S^2> = (3N/4) + (1/4) sum_{i<j} <sigma_i . sigma_j> * 2 / 2, sigma convention."""
    s2 = 0.75 * n
    for i, j in itertools.combinations(range(n), 2):
        s2 += 0.5 * float(np.real(np.vdot(v, sdot_matrix(n, i, j) @ v)))
    return 0.5 * (np.sqrt(1.0 + 4.0 * s2) - 1.0)


def check_BC(args):
    n, gid = args
    g = connected_atlas(n)[gid]
    edges = [tuple(sorted(e)) for e in g.edges()]
    mats = {e: sdot_matrix(n, *e) for e in edges}
    h0 = sum(mats.values())
    grid = np.linspace(-2.0, 2.0, 201)
    res = []
    for d in edges:
        m = mats[d]
        e0s, ps = [], []
        for s in grid:
            e0, v, _ = ground(h0 + (s - 1.0) * m)
            sd = float(np.real(np.einsum("ik,ij,jk->", v.conj(), m, v))) / v.shape[1]
            e0s.append(e0)
            ps.append((1.0 - sd) / 4.0)
        ps = np.array(ps)
        # B: Hellmann-Feynman at three off-grid points, central difference h=1e-6
        hf = 0.0
        for s in (-1.234567, 0.345678, 1.456789):
            ep = ground(h0 + (s + 1e-6 - 1.0) * m)[0]
            em = ground(h0 + (s - 1e-6 - 1.0) * m)[0]
            _, v, k = ground(h0 + (s - 1.0) * m)
            if k == 1:
                sd = float(np.real(np.vdot(v[:, 0], m @ v[:, 0])))
                hf = max(hf, abs((ep - em) / 2e-6 - sd))
        worst_drop = float(np.max(np.maximum(0.0, ps[:-1] - ps[1:])))
        # C: how p_S passes 1/2 between consecutive grid points
        cont, jump = 0, 0
        for k in range(len(grid) - 1):
            a, b = ps[k] - 0.5, ps[k + 1] - 0.5
            if a < 0 <= b or a <= 0 < b:
                lo, hi = grid[k], grid[k + 1]
                for _ in range(60):
                    mid = 0.5 * (lo + hi)
                    e0, v, _ = ground(h0 + (mid - 1.0) * m)
                    pm = (1.0 - float(np.real(np.einsum("ik,ij,jk->", v.conj(), m, v))) / v.shape[1]) / 4.0
                    if pm < 0.5:
                        lo = mid
                    else:
                        hi = mid
                def p_at(s):
                    _, v, _ = ground(h0 + (s - 1.0) * m)
                    return (1.0 - float(np.real(np.einsum("ik,ij,jk->", v.conj(), m, v))) / v.shape[1]) / 4.0
                gap = p_at(hi + 1e-9) - p_at(lo - 1e-9)
                if gap > 1e-4:
                    jump += 1
                else:
                    cont += 1
        res.append({"edge": list(d), "hf_err": hf, "worst_drop": worst_drop,
                    "cont": cont, "jump": jump,
                    "pS_min": float(ps.min()), "pS_max": float(ps.max())})
    return gid, res


def check_H(args):
    """Hellmann-Feynman on a degenerate ground manifold (odd N): dE0/ds against the averaged
    <sigma.sigma>, only where the manifold size is the same at s-h, s and s+h (no crossing)."""
    n, gid = args
    g = connected_atlas(n)[gid]
    edges = [tuple(sorted(e)) for e in g.edges()]
    mats = {e: sdot_matrix(n, *e) for e in edges}
    h0 = sum(mats.values())
    worst, tested, skipped = 0.0, 0, 0
    for d in edges:
        m = mats[d]
        for s in (-1.234567, 0.345678, 1.456789):
            ep, _, kp = ground(h0 + (s + 1e-6 - 1.0) * m)
            em, _, km = ground(h0 + (s - 1e-6 - 1.0) * m)
            _, v, k = ground(h0 + (s - 1.0) * m)
            if not (k == kp == km):
                skipped += 1
                continue
            sd = float(np.real(np.einsum("ik,ij,jk->", v.conj(), m, v))) / k
            worst = max(worst, abs((ep - em) / 2e-6 - sd))
            tested += 1
    return gid, {"worst": worst, "tested": tested, "skipped": skipped}


def check_D(args):
    n, gid = args
    g = connected_atlas(n)[gid]
    edges = [tuple(sorted(e)) for e in g.edges()]
    dim = 1 << n
    sector = [b for b in range(dim) if bin(b).count("1") == n // 2]
    mats = {e: sdot_matrix(n, *e)[np.ix_(sector, sector)] for e in edges}
    h0 = sum(mats.values())
    full = {e: sdot_matrix(n, *e) for e in edges}
    out = []
    for d in edges:
        for s in (-1.5, -0.5, 0.5, 1.5):
            w, v = np.linalg.eigh(h0 + (s - 1.0) * mats[d])
            if abs(w[1] - w[0]) < DEG_TOL:
                continue
            psi = v[:, 0]
            zz = zz_diag(n, *d)[sector]
            p_zz = (1.0 - 3.0 * float(np.sum(np.abs(psi) ** 2 * zz))) / 4.0
            p_true = (1.0 - float(np.real(np.vdot(psi, mats[d] @ psi)))) / 4.0
            vec = np.zeros(dim, dtype=complex)
            vec[sector] = psi
            out.append({"S": round(2 * total_spin(vec, n)) / 2, "diff": abs(p_zz - p_true)})
    return gid, out


def run(pool, fn, n, label):
    ids = list(range(len(connected_atlas(n))))
    t0, done, results = time.time(), 0, {}
    for gid, r in pool.imap_unordered(fn, [(n, i) for i in ids], chunksize=4):
        results[gid] = r
        done += 1
        if done % 50 == 0 or done == len(ids):
            print(f"  {label} N={n}: {done}/{len(ids)} graphs, {time.time() - t0:.0f} s", flush=True)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--only", default="ABCD")
    a = ap.parse_args()
    print(f"workers={a.workers}", flush=True)
    assert len(connected_atlas(6)) == 112 and len(connected_atlas(7)) == 853
    g38 = sorted(tuple(sorted(e)) for e in connected_atlas(6)[38].edges())
    assert g38 == [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3), (2, 3)], g38
    out = {}
    with Pool(a.workers) as pool:
        if "A" in a.only:
            ra = run(pool, check_A, 7, "A")
            keys = ("so_same", "so_diff", "do_same", "do_diff")
            tot = {k: sum(r[k] for r in ra.values()) for k in keys}
            kept = {k: sum(r[k] for r in ra.values() if r["n_aut"] <= 500) for k in keys}
            out["A_N7_table_all_853"] = tot
            out["A_N7_table_skip_naut_gt_500"] = kept
            out["A_N7_graphs_with_naut_gt_500"] = sorted(g for g, r in ra.items() if r["n_aut"] > 500)
            out["A_N7_do_same_graphs"] = {str(g): len(r["do_same_pairs"]) for g, r in sorted(ra.items()) if r["do_same_pairs"]}
            print("A all 853:", tot, flush=True)
            print("A kept (n_aut<=500):", kept, flush=True)
        if "B" in a.only or "C" in a.only:
            for n in (6, 7):
                rb = run(pool, check_BC, n, "B/C")
                rows = [x for r in rb.values() for x in r]
                out[f"BC_N{n}"] = {
                    "edges": len(rows),
                    "hf_max_err": max(x["hf_err"] for x in rows),
                    "edges_with_pS_drop_gt_1e-9": sum(x["worst_drop"] > 1e-9 for x in rows),
                    "continuous_roots": sum(x["cont"] for x in rows),
                    "jumps_over_half": sum(x["jump"] for x in rows),
                    "edges_never_reaching_half": sum(x["cont"] + x["jump"] == 0 for x in rows),
                }
                print(f"B/C N={n}:", out[f"BC_N{n}"], flush=True)
        if "H" in a.only:
            for n in (6, 7):
                rh = run(pool, check_H, n, "H")
                out[f"H_N{n}"] = {"points_tested": sum(r["tested"] for r in rh.values()),
                                  "points_skipped_at_crossing": sum(r["skipped"] for r in rh.values()),
                                  "max_abs_err": max(r["worst"] for r in rh.values())}
                print(f"H N={n}:", out[f"H_N{n}"], flush=True)
        if "D" in a.only:
            rd = run(pool, check_D, 7, "D")
            rows = [x for r in rd.values() for x in r]
            byS = {}
            for x in rows:
                k = str(x["S"])
                byS.setdefault(k, {"states": 0, "max_diff": 0.0, "diff_gt_1e-9": 0})
                byS[k]["states"] += 1
                byS[k]["max_diff"] = max(byS[k]["max_diff"], x["diff"])
                byS[k]["diff_gt_1e-9"] += x["diff"] > 1e-9
            out["D_N7_sector_formula_by_S"] = byS
            print("D:", byS, flush=True)
    tag = "" if a.only == "ABCD" else "." + a.only
    path = os.path.splitext(__file__)[0] + tag + ".result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("wrote", path)


if __name__ == "__main__":
    sys.exit(main())
