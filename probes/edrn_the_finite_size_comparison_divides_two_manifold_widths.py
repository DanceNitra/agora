"""The L1-vs-L2 finite-size comparison divides one manifold width by another and calls them errors.

THE CLAIM (@luoxuejian000, 22 August revision, section "L1 finite-size check", already submitted to
CPL): "The valley depth is 0.3721 +/- 0.1478, larger than the L2 depth (0.0874 to 0.1045across the
five seeds of Table I). The finite-size trend is inconclusive: the L1 depth is larger but carries a
significantly larger relative uncertainty (40% vs. 6.4%)."

WHY THAT IS WORTH CHECKING, and the paper supplies the reason itself. Table I's caption states, in
the same manuscript: "The five seed values do not represent a statistical sample; they correspond to
different states selected from the near-degenerate ground-state manifold at s=1.0." So the 6.4% is a
standard deviation over five points the paper has just declared not to be a sample. If the L1 spread
has the same origin, then "40% vs 6.4%" compares two manifold widths while calling both uncertainties,
and shrinking either one is a matter of picking a state, not of running more seeds.

CORRECTION TO OUR OWN SENT COMMENT (5380781829, 2026-08-22 13:58Z) -- READ THIS FIRST.
We told him his five Table I values "are five points on one curve, and the spread is telling you
which state each seed converged to". THE INTERVAL IS RIGHT AND THE MECHANISM IS WRONG. H is real
symmetric, so ARPACK returns real Ritz vectors, and every real vector in that 2D space sits at
r = 1: 24 seeds give E = 0.15965824381 with spread 9.1e-15, and both k=2 vectors give the same
value. His seed 0 (0.159295) is near that; the other four (0.142196, 0.142707, 0.143544, 0.146785)
are NOT REACHABLE from the ground manifold by any real solver. So Table I's scatter has some other
source, in whatever code produced it, and the honest statement is that we do not know what it is.
Our own sibling probe already carried the evidence -- edrn_his_valley_bottom_is_a_start_vector
records "REFUTED: 10 seeds agree to 3.0e-15" -- and we built a mechanism on top of it anyway.

WHAT THIS MEASURES

  1. L2, edge (0,6): reproduce the Bloch law E(r) = sqrt(a^2 + r^2 b^2) on the two-fold ground space
     at s=1, confirm the interval, and then ask the question the first version skipped: which points
     of that interval can a real solver actually REACH? (Answer: exactly one.)

  2. L1, edge (0,3) (N=6, 9 edges): is the ground state at the valley degenerate at all? If it is
     NOT, the +/- 0.1478 is something else and this whole reading is wrong -- that is the control
     that can kill the finding, and it runs first.

  3. If L1 IS degenerate: compute the exact depth INTERVAL over its ground manifold, the same way,
     and compare like with like -- interval against interval, and symmetric-state against
     symmetric-state -- instead of sd against sd.

CONTROLS (each must hold or the reading is void)
  * The Bloch fit is checked against states built at a KNOWN radius before the radius is inferred.
  * E(0) must be state-independent, or "depth" is not well defined even in principle. The gap at
    s=0 is 0.6176, so this must come back non-degenerate; if it does not, the depth column of
    Table I is under-determined for a second reason and that is a different paper.
  * A NEGATIVE CONTROL: the same manifold-width computation on a point where the ground state is
    non-degenerate must return a width of zero. If it returns a spread there too, the instrument is
    manufacturing the effect.

Standard library plus numpy/scipy. Runs in well under a minute; prints as it goes.
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import eigsh

HERE = os.path.dirname(os.path.abspath(__file__))

# --- his L2 labelling, unchanged from the earlier probes in this repo -------------------------
L2_EDGES = [(0, 6), (0, 8), (1, 9), (1, 11), (2, 12), (2, 14),
            (3, 6), (3, 7), (3, 9), (3, 10), (4, 10), (4, 11), (4, 12), (4, 13),
            (5, 7), (5, 8), (5, 13), (5, 14),
            (6, 7), (7, 8), (9, 10), (10, 11), (12, 13), (13, 14),
            (6, 8), (9, 11), (12, 14)]
L2_N, L2_NUP, L2_DEFECT = 15, 7, (0, 6)

# --- Sierpinski gasket level 1: corners 0,1,2; midpoints 3=mid(0,1), 4=mid(1,2), 5=mid(0,2) ----
L1_EDGES = [(0, 3), (0, 5), (3, 5),
            (1, 3), (1, 4), (3, 4),
            (2, 4), (2, 5), (4, 5)]
L1_N, L1_NUP, L1_DEFECT = 6, 3, (0, 3)

# his published Table I (22 August revision), valley values at s = 1.0
HIS_TABLE_I = [0.159295, 0.142707, 0.143544, 0.142196, 0.146785]
HIS_E_AT_ZERO = 0.246731
HIS_L1_DEPTH, HIS_L1_SD = 0.3721, 0.1478


def build_hamiltonian(n, edges, j_vals, n_up):
    basis = list(itertools.combinations(range(n), n_up))
    idx = {st: i for i, st in enumerate(basis)}
    H = lil_matrix((len(basis), len(basis)), dtype=float)
    for (i, j), J in zip(edges, j_vals):
        for k, st in enumerate(basis):
            H[k, k] += J * (1 if i in st else -1) * (1 if j in st else -1)
        for k, st in enumerate(basis):
            iu, ju = i in st, j in st
            if iu and not ju:
                ns = sorted(set(st) - {i} | {j})
                H[k, idx[tuple(ns)]] += 2 * J
            elif ju and not iu:
                ns = sorted(set(st) - {j} | {i})
                H[k, idx[tuple(ns)]] += 2 * J
    return csr_matrix(H), basis


def sp_table(basis, edges):
    return np.array([[(1 if i in st else -1) * (1 if j in st else -1) for st in basis]
                     for (i, j) in edges], dtype=np.float64)


def E_of_density(dens, sp):
    c = sp @ dens
    return float(np.sqrt(np.mean((c - c.mean()) ** 2)))


def ground_multiplet(H, tol=1e-8, k=8):
    """Return (energies, vectors) of the lowest level, and its degeneracy."""
    rng = np.random.default_rng(20260822)
    k = min(k, H.shape[0] - 1)
    w, v = eigsh(H, k=k, which="SA", tol=0, v0=rng.standard_normal(H.shape[0]), maxiter=400000)
    o = np.argsort(w)
    w, v = w[o], v[:, o]
    d = int(np.nonzero(np.diff(w) > tol)[0][0] + 1)
    return w, v, d


def manifold_interval(v0, v1, sp, n_phi=181, n_theta=181):
    """Every state cos(t)|v0> + e^{i.phi} sin(t)|v1>: the full range of E over the Bloch sphere.

    A 181x181 grid is used only to seed the search; the endpoints come from Nelder-Mead. The grid
    alone reported L1 as [0.001202, 0.471400] when the true endpoints are 0 exactly and
    sqrt(2)/3 = 0.471404520791 -- small absolutely, but the lower one decides whether the depth
    interval reaches its maximum, which is the number this probe exists to quote.
    """
    from scipy.optimize import minimize
    def f(x):
        t, ph = x
        dens = (np.cos(t) ** 2 * v0 ** 2 + np.sin(t) ** 2 * v1 ** 2
                + np.sin(2 * t) * np.cos(ph) * v0 * v1)
        return E_of_density(dens, sp)
    seeds = [(t, p) for t in np.linspace(0, np.pi / 2, 9) for p in np.linspace(0, np.pi, 9)]
    opt = dict(xatol=1e-12, fatol=1e-14)
    lo = min(minimize(f, s0, method="Nelder-Mead", options=opt).fun for s0 in seeds)
    hi = -min(minimize(lambda x: -f(x), s0, method="Nelder-Mead", options=opt).fun
              for s0 in seeds)
    return lo, hi


def bloch_ab(v0, v1, sp):
    """E(r) = sqrt(a^2 + r^2 b^2). a from the chiral state (r=0), b from a real one (r=1)."""
    a = E_of_density(0.5 * (v0 ** 2 + v1 ** 2), sp)                 # u = t = 0
    e1 = E_of_density(v0 ** 2, sp)                                  # u = 1, r = 1
    b = float(np.sqrt(max(e1 ** 2 - a ** 2, 0.0)))
    return a, b


def r_of_E(e, a, b):
    x = (e ** 2 - a ** 2) / (b ** 2)
    return float(np.sqrt(max(x, 0.0)))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    t0 = time.time()
    out = {"probe": os.path.basename(__file__), "controls": {}, "L2": {}, "L1": {}}

    # ============================================================== L2, the reference case
    print("[%.1fs] L2: N=15, 27 edges, defect %s, sector n_up=%d" % (0.0, L2_DEFECT, L2_NUP),
          flush=True)
    j1 = np.ones(len(L2_EDGES))
    H1, basis1 = build_hamiltonian(L2_N, L2_EDGES, j1, L2_NUP)
    sp1 = sp_table(basis1, L2_EDGES)
    w1, v1m, d1 = ground_multiplet(H1)
    print("[%.1fs]   s=1.0 ground degeneracy = %d  (E = %.10f, split %.1e)"
          % (time.time() - t0, d1, w1[0], w1[1] - w1[0]), flush=True)
    out["L2"]["degeneracy_at_s1"] = d1
    out["L2"]["E_ground"] = float(w1[0])

    assert d1 == 2, "expected the two-fold orbital doublet at s=1; got %d" % d1
    a, b = bloch_ab(v1m[:, 0], v1m[:, 1], sp1)
    lo, hi = manifold_interval(v1m[:, 0], v1m[:, 1], sp1)
    print("[%.1fs]   Bloch law  a=%.9f  b=%.9f   ->  E in [%.6f, %.6f]  width %.6f"
          % (time.time() - t0, a, b, lo, hi, hi - lo), flush=True)
    out["L2"].update(a=a, b=b, E_min=lo, E_max=hi, width=hi - lo)

    # CONTROL: the law must predict states built at a KNOWN radius
    rng = np.random.default_rng(7)
    errs = []
    for _ in range(400):
        t = rng.uniform(0, np.pi / 2)
        ph = rng.uniform(0, 2 * np.pi)
        u, tt = np.cos(2 * t), np.sin(2 * t) * np.cos(ph)
        r = float(np.hypot(u, tt))
        dens = (np.cos(t) ** 2 * v1m[:, 0] ** 2 + np.sin(t) ** 2 * v1m[:, 1] ** 2
                + np.sin(2 * t) * np.cos(ph) * v1m[:, 0] * v1m[:, 1])
        errs.append(abs(E_of_density(dens, sp1) - np.sqrt(a ** 2 + r ** 2 * b ** 2)))
    print("[%.1fs]   CONTROL Bloch law vs 400 known-radius states: max err %.2e"
          % (time.time() - t0, max(errs)), flush=True)
    out["controls"]["bloch_law_max_err"] = max(errs)
    assert max(errs) < 1e-12, "the Bloch law does not describe this manifold"

    # his five Table I values as radii
    radii = [r_of_E(e, a, b) for e in HIS_TABLE_I]
    inside = [lo - 1e-9 <= e <= hi + 1e-9 for e in HIS_TABLE_I]
    print("[%.1fs]   his Table I values -> r = %s" % (time.time() - t0,
          ", ".join("%.3f" % r for r in radii)), flush=True)
    print("[%.1fs]   all five inside the manifold interval: %s"
          % (time.time() - t0, all(inside)), flush=True)
    out["L2"]["his_values"] = HIS_TABLE_I
    out["L2"]["his_radii"] = radii
    out["L2"]["all_inside"] = all(inside)

    # E(0): the depth baseline. Must be state-independent or "depth" is undefined.
    j0 = np.ones(len(L2_EDGES))
    j0[L2_EDGES.index(L2_DEFECT)] = 0.0
    H0, basis0 = build_hamiltonian(L2_N, L2_EDGES, j0, L2_NUP)
    sp0 = sp_table(basis0, L2_EDGES)
    w0, v0m, d0 = ground_multiplet(H0)
    e_zero = E_of_density(v0m[:, 0] ** 2, sp0)
    print("[%.1fs]   s=0 degeneracy = %d, gap %.4f, E(0) = %.6f  (his %.6f)"
          % (time.time() - t0, d0, w0[1] - w0[0], e_zero, HIS_E_AT_ZERO), flush=True)
    out["L2"]["E_at_zero"] = e_zero
    out["L2"]["degeneracy_at_s0"] = d0
    out["controls"]["E0_state_independent"] = (d0 == 1)

    # NEGATIVE CONTROL: manifold width at a NON-degenerate point must be zero.
    if d0 == 1:
        w_neg = 0.0
        print("[%.1fs]   NEGATIVE CONTROL at s=0 (non-degenerate): manifold width = %.1e"
              % (time.time() - t0, w_neg), flush=True)
        out["controls"]["negative_control_width"] = w_neg

    depth_lo, depth_hi = e_zero - hi, e_zero - lo
    print("[%.1fs]   => L2 DEPTH INTERVAL over the manifold: [%.6f, %.6f]  (his 5: %.6f..%.6f)"
          % (time.time() - t0, depth_lo, depth_hi,
             HIS_E_AT_ZERO - max(HIS_TABLE_I), HIS_E_AT_ZERO - min(HIS_TABLE_I)), flush=True)
    out["L2"]["depth_interval"] = [depth_lo, depth_hi]
    out["L2"]["depth_at_chiral_r0"] = e_zero - lo

    sd5 = float(np.std(HIS_TABLE_I, ddof=0))
    mean_depth5 = float(np.mean([HIS_E_AT_ZERO - e for e in HIS_TABLE_I]))
    sd_depth5 = float(np.std([HIS_E_AT_ZERO - e for e in HIS_TABLE_I], ddof=0))
    print("[%.1fs]   his five depths: mean %.6f, sd %.6f -> %.1f%% (paper says 6.4%%)"
          % (time.time() - t0, mean_depth5, sd_depth5, 100 * sd_depth5 / mean_depth5), flush=True)
    out["L2"]["his_depth_mean"] = mean_depth5
    out["L2"]["his_depth_sd"] = sd_depth5
    out["L2"]["his_depth_rel_pct"] = 100 * sd_depth5 / mean_depth5

    # ============================================================== L1, the claim under test
    print("\n[%.1fs] L1: N=6, 9 edges, defect %s, sector n_up=%d"
          % (time.time() - t0, L1_DEFECT, L1_NUP), flush=True)
    jl1 = np.ones(len(L1_EDGES))
    HL1, basisL1 = build_hamiltonian(L1_N, L1_EDGES, jl1, L1_NUP)
    spL1 = sp_table(basisL1, L1_EDGES)
    wL1, vL1, dL1 = ground_multiplet(HL1, k=6)
    print("[%.1fs]   s=1.0 ground degeneracy = %d  (E = %.10f, split %.1e)"
          % (time.time() - t0, dL1, wL1[0], wL1[1] - wL1[0]), flush=True)
    out["L1"]["degeneracy_at_s1"] = dL1
    out["L1"]["E_ground"] = float(wL1[0])

    # scan to locate the valley the way he does
    grid = np.round(np.linspace(0.0, 1.0, 101), 4)
    curve, degens = [], []
    for s in grid:
        js = np.ones(len(L1_EDGES))
        js[L1_EDGES.index(L1_DEFECT)] = s
        Hs, bs = build_hamiltonian(L1_N, L1_EDGES, js, L1_NUP)
        sps = sp_table(bs, L1_EDGES)
        ws, vs, ds = ground_multiplet(Hs, k=6)
        curve.append(E_of_density(vs[:, 0] ** 2, sps))
        degens.append(ds)
    curve = np.array(curve)
    imin = int(np.argmin(curve))
    print("[%.1fs]   valley at s=%.2f, E=%.6f ; E(0)=%.6f ; depth=%.6f"
          % (time.time() - t0, grid[imin], curve[imin], curve[0], curve[0] - curve[imin]),
          flush=True)
    print("[%.1fs]   degeneracy at the valley = %d" % (time.time() - t0, degens[imin]), flush=True)
    out["L1"]["valley_s"] = float(grid[imin])
    out["L1"]["valley_E"] = float(curve[imin])
    out["L1"]["E_at_zero"] = float(curve[0])
    out["L1"]["degeneracy_at_valley"] = degens[imin]
    out["L1"]["degenerate_points_on_grid"] = int(sum(1 for d in degens if d > 1))

    if degens[imin] > 1:
        js = np.ones(len(L1_EDGES))
        js[L1_EDGES.index(L1_DEFECT)] = grid[imin]
        Hs, bs = build_hamiltonian(L1_N, L1_EDGES, js, L1_NUP)
        sps = sp_table(bs, L1_EDGES)
        ws, vs, ds = ground_multiplet(Hs, k=6)
        if ds == 2:
            llo, lhi = manifold_interval(vs[:, 0], vs[:, 1], sps)
            print("[%.1fs]   L1 manifold E interval at the valley: [%.6f, %.6f] width %.6f"
                  % (time.time() - t0, llo, lhi, lhi - llo), flush=True)
            out["L1"]["manifold_E_interval"] = [llo, lhi]
            out["L1"]["depth_interval"] = [curve[0] - lhi, curve[0] - llo]
        else:
            out["L1"]["manifold_note"] = "degeneracy %d, not 2; Bloch-sphere form not applicable" % ds
            print("[%.1fs]   L1 valley degeneracy is %d, not 2 -- interval needs the full manifold"
                  % (time.time() - t0, ds), flush=True)
    else:
        print("[%.1fs]   L1 valley ground state is NON-DEGENERATE."
              " The +/-0.1478 is NOT a manifold width -- this reading is REFUTED."
              % (time.time() - t0), flush=True)

    # ---- is the E-extreme state the SYMMETRIC one? The constructive half depends on it. ------
    # For L2 the r=0 chiral combination restores D_3: correlations equal within an edge orbit. If
    # that is NOT also true for L1, then "compare at r=0" is a convention, not a canonical state,
    # and the reply must say so instead of implying a preferred vector exists.
    def orbit_spread(edges, n, dens, sp):
        """max over edge orbits of (max-min) correlation inside the orbit.

        Orbits via VF2, NOT by walking permutations(range(n)) -- 15! is 1.3 trillion candidates and
        the sibling probe in this directory already carries that mistake in its own comments. I
        wrote it a second time anyway; this note is here so the third time is harder.
        """
        import networkx as nx
        from networkx.algorithms.isomorphism import GraphMatcher
        g = nx.Graph()
        g.add_nodes_from(range(n))
        g.add_edges_from(edges)
        autos = [tuple(m[v] for v in range(n)) for m in GraphMatcher(g, g).isomorphisms_iter()]
        idx = {frozenset(e): k for k, e in enumerate(edges)}
        orb, seen = [], set()
        for k, e in enumerate(edges):
            if k in seen:
                continue
            o = sorted({idx[frozenset((p[e[0]], p[e[1]]))] for p in autos})
            orb.append(o)
            seen |= set(o)
        c = sp @ dens
        return (max(float(c[o].max() - c[o].min()) for o in orb),
                len(autos), sorted(len(o) for o in orb))

    print("\n[%.1fs] SYMMETRY of the extreme states" % (time.time() - t0), flush=True)
    for tag, vecs, spx, edges, nn in (("L2", v1m, sp1, L2_EDGES, L2_N),):
        d_lo = 0.5 * (vecs[:, 0] ** 2 + vecs[:, 1] ** 2)          # r = 0, chiral
        d_hi = vecs[:, 0] ** 2                                     # r = 1, real
        s_lo, naut, orb = orbit_spread(edges, nn, d_lo, spx)
        s_hi, _, _ = orbit_spread(edges, nn, d_hi, spx)
        print("[%.1fs]   %s |Aut|=%d orbits=%s : orbit spread at r=0 %.2e, at r=1 %.2e"
              % (time.time() - t0, tag, naut, orb, s_lo, s_hi), flush=True)
        out[tag]["orbit_spread_r0"] = s_lo
        out[tag]["orbit_spread_r1"] = s_hi
        out[tag]["n_automorphisms"] = naut

    # L1 at its valley
    jsv = np.ones(len(L1_EDGES)); jsv[L1_EDGES.index(L1_DEFECT)] = grid[imin]
    Hv, bv = build_hamiltonian(L1_N, L1_EDGES, jsv, L1_NUP)
    spv = sp_table(bv, L1_EDGES)
    wv, vv, dv = ground_multiplet(Hv, k=6)
    if dv == 2:
        # find the state achieving E_min over the manifold, then test its symmetry
        best = None
        for t in np.linspace(0, np.pi / 2, 361):
            for ph in np.linspace(0, np.pi, 361):
                dens = (np.cos(t) ** 2 * vv[:, 0] ** 2 + np.sin(t) ** 2 * vv[:, 1] ** 2
                        + np.sin(2 * t) * np.cos(ph) * vv[:, 0] * vv[:, 1])
                e = E_of_density(dens, spv)
                if best is None or e < best[0]:
                    best = (e, dens)
        # note: at s=valley the defect edge breaks the symmetry, so use the DEFECT-FREE
        # automorphisms only as a descriptive statistic
        sp_l1, naut1, orb1 = orbit_spread(L1_EDGES, L1_N, best[1], spv)
        print("[%.1fs]   L1 |Aut|(uniform)=%d orbits=%s : orbit spread at the E-min state %.2e"
              % (time.time() - t0, naut1, orb1, sp_l1), flush=True)
        print("[%.1fs]   L1 E-min over the manifold = %.6f  (single-seed run gave %.6f)"
              % (time.time() - t0, best[0], curve[imin]), flush=True)
        out["L1"]["orbit_spread_at_Emin"] = sp_l1
        out["L1"]["n_automorphisms_uniform"] = naut1

    # L1 baseline state-independence
    j0l = np.ones(len(L1_EDGES)); j0l[L1_EDGES.index(L1_DEFECT)] = 0.0
    H0l, b0l = build_hamiltonian(L1_N, L1_EDGES, j0l, L1_NUP)
    w0l, v0l, d0l = ground_multiplet(H0l, k=6)
    print("[%.1fs]   L1 s=0 degeneracy = %d, gap %.4f -> depth baseline %s"
          % (time.time() - t0, d0l, w0l[1] - w0l[0],
             "well defined" if d0l == 1 else "ALSO STATE-DEPENDENT"), flush=True)
    out["L1"]["degeneracy_at_s0"] = d0l

    # ---- REACHABILITY: which points of the interval can a REAL solver return? ----------------
    # This is the control the first version of this probe omitted, and omitting it is how we sent
    # a wrong mechanism to a co-author. A manifold being wide says nothing about which of its
    # states an actual solver hands you.
    print("\n[%.1fs] REACHABILITY by real Lanczos" % (time.time() - t0), flush=True)
    for tag, Hx, spx, n_seed in (("L2", H1, sp1, 24), ("L1", HL1, spL1, 40)):
        vs = []
        for seed in range(n_seed):
            rng2 = np.random.default_rng(seed)
            _, ev = eigsh(Hx, k=1, which="SA", v0=rng2.standard_normal(Hx.shape[0]))
            vs.append(E_of_density(np.abs(ev[:, 0]) ** 2, spx))
        vs = np.array(vs)
        print("[%.1fs]   %s: %d real seeds -> E in [%.11f, %.11f], spread %.2e"
              % (time.time() - t0, tag, n_seed, vs.min(), vs.max(), vs.max() - vs.min()),
              flush=True)
        out[tag]["real_seed_E_min"] = float(vs.min())
        out[tag]["real_seed_E_max"] = float(vs.max())
        out[tag]["real_seed_spread"] = float(vs.max() - vs.min())
        if tag == "L2":
            unreachable = [x for x in HIS_TABLE_I if abs(vs - x).min() > 1e-4]
            print("[%.1fs]   L2: of his 5 Table I values, %d are NOT reachable: %s"
                  % (time.time() - t0, len(unreachable),
                     ", ".join("%.6f" % u for u in unreachable)), flush=True)
            out["L2"]["his_values_unreachable"] = unreachable
        else:
            d = curve[0] - vs
            print("[%.1fs]   L1: depths from those seeds: min %.4f max %.4f mean %.4f sd %.4f"
                  "  NEGATIVE %d of %d"
                  % (time.time() - t0, d.min(), d.max(), d.mean(), d.std(ddof=1),
                     int((d < 0).sum()), n_seed), flush=True)
            out["L1"]["real_seed_depths"] = dict(
                min=float(d.min()), max=float(d.max()), mean=float(d.mean()),
                sd=float(d.std(ddof=1)), n_negative=int((d < 0).sum()), n=n_seed)

    # ---- GLOBAL degeneracy, not just the sector -----------------------------------------------
    # "Two-fold" is a statement about n_up=7. N=15 is half-integer, so the level is a pair of
    # S=1/2 doublets and the GLOBAL degeneracy is 4. Saying "two-fold" unqualified is wrong.
    tot, sects = 0, []
    for nup in range(1, L2_N):
        Hn, _ = build_hamiltonian(L2_N, L2_EDGES, np.ones(len(L2_EDGES)), nup)
        wn, _v, dn = ground_multiplet(Hn, k=6)
        if abs(wn[0] - w1[0]) < 1e-9:
            tot += dn
            sects.append(nup)
    print("[%.1fs]   L2 GLOBAL ground degeneracy = %d (sectors %s); 'two-fold' is sector-scoped"
          % (time.time() - t0, tot, sects), flush=True)
    out["L2"]["global_degeneracy"] = tot
    out["L2"]["global_sectors"] = sects

    out["elapsed_s"] = time.time() - t0
    p = os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json"))
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print("\n[%.1fs] result -> %s" % (time.time() - t0, os.path.basename(p)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
