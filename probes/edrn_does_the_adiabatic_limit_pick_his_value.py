"""The red team's attack on our own finding: is his s = 1 value the ADIABATIC LIMIT of his own scan?

WHY THIS EXISTS. We measured that at s = 1.0 the SG(2) ground state is two-fold degenerate, that the
global diagnostic is invariant inside that space (6.7e-16) but the local one spans 0.134, and that his
own file scores six symmetry-equivalent edges 0.132 apart. The remedy we were about to propose was to
average over the ground multiplet.

The adversarial pass refused that remedy, and the objection is good: averaging over the multiplet is
OUR prescription, not the canonical one. For a SCAN there is a better-defined choice -- the adiabatic
limit lim(s -> 1-) and lim(s -> 1+), the state his own curve is continuously approaching from either
side. If his s = 1 point sits on the smooth continuation of his own data, then the 0.134 span we
measured describes states his calculation never visited, and the finding weakens from "artifact" to
"unstated prescription".

So this probe hands the objection the chance to kill our claim:

  1. Walk the local diagnostic in to s = 1 from BOTH sides at 0.9 / 0.99 / 0.999 / 0.9999 and the
     mirror above, where the ground state is NON-degenerate and every value is unambiguous.
  2. Compare the two one-sided limits with each other, with his published s = 1 value, and with the
     ground-space average.

The outcomes are not symmetric, and each one changes what we may say:
  * both limits agree AND match his value -> his number is the adiabatic one. Our remedy is wrong,
    the local finding drops to "state your prescription", and we say so.
  * the two limits DISAGREE -> no adiabatic prescription exists at that point either. The quantity is
    genuinely ambiguous, and his value is one of at least three defensible answers.
  * both limits agree with each other but NOT with his value -> his number is neither the adiabatic
    limit nor the invariant average, and the artifact reading survives.

SEPARATE QUESTION, also raised: is the degeneracy SU(2) or spatial? He diagonalises at FIXED
magnetisation (N_up = 7), and each SU(2) multiplet contributes exactly one state to a fixed-Sz
sector, so SU(2) cannot produce it. This probe checks that directly by measuring total S^2 on the
ground space -- if both vectors carry the same S, the degeneracy is spatial, which is what makes a
LOCAL window orbit-incomplete and a GLOBAL one orbit-complete.

CONTROLS:
  * the approach points must be NON-degenerate, or the limit is not being taken through unambiguous
    values -- asserted, not assumed;
  * the global diagnostic must have a continuous, matching limit from both sides, since it is
    invariant on the ground space -- if the global one also jumps, the sweep is measuring a
    discontinuity of the STATE rather than of the observable, and the local verdict is void.

Run:  python probes/edrn_does_the_adiabatic_limit_pick_his_value.py
"""
from __future__ import annotations
import itertools
import json
import os
import sys

import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import eigsh

HERE = os.path.dirname(os.path.abspath(__file__))

HIS_EDGES = [(0, 6), (0, 8), (1, 9), (1, 11), (2, 12), (2, 14),
             (3, 6), (3, 7), (3, 9), (3, 10), (4, 10), (4, 11), (4, 12), (4, 13),
             (5, 7), (5, 8), (5, 13), (5, 14),
             (6, 7), (7, 8), (9, 10), (10, 11), (12, 13), (13, 14),
             (6, 8), (9, 11), (12, 14)]
N, N_UP = 15, 7
HIS_LOCAL_AT_S1_EDGE0 = 0.120543      # his file, edge (0,6), s = 1.00
HIS_GLOBAL_AT_S1 = 0.159658           # his file, every edge, s = 1.00
GROUND_SPACE_LOCAL = 0.105706         # our multiplet average, all six tip edges
GROUND_SPACE_GLOBAL = 0.110269


def build(n, edges, j_vals, n_up):
    basis = list(itertools.combinations(range(n), n_up))
    index = {st: i for i, st in enumerate(basis)}
    H = lil_matrix((len(basis), len(basis)), dtype=float)
    for (i, j), J in zip(edges, j_vals):
        for a, st in enumerate(basis):
            si = 1 if i in st else -1
            sj = 1 if j in st else -1
            H[a, a] += J * si * sj
        for a, st in enumerate(basis):
            iu, ju = i in st, j in st
            if iu and not ju:
                ns = list(st)
                ns.remove(i)
                ns.append(j)
                H[a, index[tuple(sorted(ns))]] += 2 * J
            elif ju and not iu:
                ns = list(st)
                ns.remove(j)
                ns.append(i)
                H[a, index[tuple(sorted(ns))]] += 2 * J
    return csr_matrix(H), basis


def sp_table(basis, edges):
    return np.array([[(1 if i in st else -1) * (1 if j in st else -1) for st in basis]
                     for (i, j) in edges], dtype=np.float64)


def spectrum(H, k=8):
    rng = np.random.default_rng(20260822)
    w, v = eigsh(H, k=k, which="SA", tol=0, v0=rng.standard_normal(H.shape[0]), maxiter=200000)
    o = np.argsort(w)
    return w[o], v[:, o]


def local_edges_r2(edge, radius=2):
    import networkx as nx
    g = nx.Graph()
    g.add_nodes_from(range(N))
    g.add_edges_from(HIS_EDGES)
    nu = set(nx.single_source_shortest_path_length(g, edge[0], cutoff=radius))
    nv = set(nx.single_source_shortest_path_length(g, edge[1], cutoff=radius))
    keep = nu | nv
    return [e for e in g.edges() if e[0] in keep and e[1] in keep]


def total_s2(vec, basis, n):
    """<S^2> for a state in a fixed-Sz sector, built from the same hopping structure."""
    index = {st: i for i, st in enumerate(basis)}
    # S^2 = sum_ij (S^z_i S^z_j + 1/2 (S+_i S-_j + S-_i S+_j))
    out = 0.0
    # diagonal S^z part
    for a, st in enumerate(basis):
        sz = sum(0.5 if i in st else -0.5 for i in range(n))
        out += (vec[a] ** 2) * sz * sz
    # exchange part: for i != j, 1/2(S+_i S-_j + h.c.) acting between states
    acc = np.zeros_like(vec)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            for a, st in enumerate(basis):
                if (j in st) and (i not in st):
                    ns = list(st)
                    ns.remove(j)
                    ns.append(i)
                    # coefficient 1, not 1/2: summing 1/2(S+_i S-_j + S-_i S+_j) over UNORDERED
                    # pairs is the same as summing S+_i S-_j over ORDERED ones, which is this loop.
                    # At 1/2 the first run returned <S^2> = 4.25 -- not S(S+1) for any half-integer
                    # S -- and the equality control still PASSED, because both members were equally
                    # wrong. A control that compares two numbers cannot see a shared defect.
                    acc[index[tuple(sorted(ns))]] += 1.0 * vec[a]
    out += float(vec @ acc)
    # S^2 = (S^z_tot)^2 + sum_{i != j} 1/2(S+_i S-_j + h.c.) + sum_i 1/2(S+_i S-_i + S-_i S+_i),
    # and the last sum is n/2 because S+S- + S-S+ = 1 on a spin-1/2 site.
    out += 0.5 * n
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    res = {}
    ok = True
    loc = local_edges_r2(HIS_EDGES[0])
    print("radius-2 window of edge (0,6): %d edges" % len(loc), flush=True)

    offsets = [0.1, 0.01, 0.001, 0.0001]
    rows = []
    print("\n%-10s %-6s %-12s %-12s %-12s" % ("s", "deg", "gap", "E_local", "E_global"), flush=True)
    for sign in (-1, +1):
        for off in sorted(offsets, reverse=True):
            s = 1.0 + sign * off
            j = np.ones(len(HIS_EDGES))
            j[0] = s
            H, basis = build(N, HIS_EDGES, j, N_UP)
            w, v = spectrum(H)
            gap = float(w[1] - w[0])
            deg = 1 if gap > 1e-8 else 2
            q = v[:, 0] ** 2
            el = float(np.std(sp_table(basis, loc) @ q))
            eg = float(np.std(sp_table(basis, HIS_EDGES) @ q))
            rows.append({"s": s, "deg": deg, "gap": gap, "e_local": el, "e_global": eg})
            print("%-10.4f %-6d %-12.3e %-12.6f %-12.6f" % (s, deg, gap, el, eg), flush=True)

    res["approach"] = rows
    # CONTROL: every approach point must be non-degenerate
    nd = all(r["deg"] == 1 for r in rows)
    print("\nCONTROL every approach point is non-degenerate: %s" % ("PASS" if nd else "FAIL"),
          flush=True)
    ok = ok and nd

    below = [r for r in rows if r["s"] < 1.0]
    above = [r for r in rows if r["s"] > 1.0]
    lim_lo_l = min(below, key=lambda r: 1.0 - r["s"])["e_local"]
    lim_hi_l = min(above, key=lambda r: r["s"] - 1.0)["e_local"]
    lim_lo_g = min(below, key=lambda r: 1.0 - r["s"])["e_global"]
    lim_hi_g = min(above, key=lambda r: r["s"] - 1.0)["e_global"]
    res["limit_local_below"], res["limit_local_above"] = lim_lo_l, lim_hi_l
    res["limit_global_below"], res["limit_global_above"] = lim_lo_g, lim_hi_g

    print("\nE_local  : from below %.6f   from above %.6f   |diff| %.6f"
          % (lim_lo_l, lim_hi_l, abs(lim_lo_l - lim_hi_l)), flush=True)
    print("E_global : from below %.6f   from above %.6f   |diff| %.6f"
          % (lim_lo_g, lim_hi_g, abs(lim_lo_g - lim_hi_g)), flush=True)

    # CONTROL: the global limit must be continuous, since the observable is invariant on the space
    g_cont = abs(lim_lo_g - lim_hi_g) < 5e-3
    print("CONTROL the GLOBAL limit is continuous through s=1: %s (%.3e)"
          % ("PASS" if g_cont else "FAIL", abs(lim_lo_g - lim_hi_g)), flush=True)
    ok = ok and g_cont

    print("\ncandidate values for the s = 1 LOCAL point:", flush=True)
    cands = {"his published": HIS_LOCAL_AT_S1_EDGE0,
             "adiabatic from below": lim_lo_l,
             "adiabatic from above": lim_hi_l,
             "ground-space average": GROUND_SPACE_LOCAL}
    for k, v in cands.items():
        print("  %-24s %.6f" % (k, v), flush=True)
    res["candidates"] = cands

    two_sided_agree = abs(lim_lo_l - lim_hi_l) < 1e-3
    his_is_adiabatic = (abs(HIS_LOCAL_AT_S1_EDGE0 - lim_lo_l) < 1e-3
                        or abs(HIS_LOCAL_AT_S1_EDGE0 - lim_hi_l) < 1e-3)
    res["two_sided_limits_agree"] = bool(two_sided_agree)
    res["his_value_is_an_adiabatic_limit"] = bool(his_is_adiabatic)

    print("\n" + "=" * 88)
    if two_sided_agree and his_is_adiabatic:
        verdict = ("OUR REMEDY IS WRONG: his value IS the adiabatic limit. Drop the artifact "
                   "reading; ask only that the prescription be stated.")
    elif not two_sided_agree:
        verdict = ("NO adiabatic prescription exists at s=1 either: the two one-sided limits "
                   "disagree by %.6f. The local quantity is genuinely ambiguous there."
                   % abs(lim_lo_l - lim_hi_l))
    else:
        verdict = ("His value is NEITHER the adiabatic limit NOR the invariant average. The "
                   "artifact reading survives the objection.")
    print(verdict)
    print("=" * 88, flush=True)
    res["verdict"] = verdict

    # ---- is the degeneracy spatial rather than SU(2)? -------------------------------------------
    j = np.ones(len(HIS_EDGES))
    H1, basis1 = build(N, HIS_EDGES, j, N_UP)
    w1, v1 = spectrum(H1)
    print("\nground doublet at s=1: E = %.9f, %.9f  (split %.3e)"
          % (w1[0], w1[1], w1[1] - w1[0]), flush=True)
    print("computing <S^2> on both ground vectors (slow, one pass each) ...", flush=True)
    s2 = [total_s2(v1[:, i], basis1, N) for i in (0, 1)]
    print("  <S^2> = %.6f and %.6f" % (s2[0], s2[1]), flush=True)
    same_s = abs(s2[0] - s2[1]) < 1e-6
    # QUANTIZATION control: <S^2> must equal S(S+1) for a half-integer S, or the operator is wrong
    # and the equality above is two matching wrong numbers.
    def _spin_of(x):
        return (-1.0 + (1.0 + 4.0 * x) ** 0.5) / 2.0
    spins = [_spin_of(x) for x in s2]
    quantized = all(abs(sp * 2 - round(sp * 2)) < 1e-6 for sp in spins)
    print("  implied S = %.6f, %.6f ; half-integer: %s"
          % (spins[0], spins[1], "PASS" if quantized else "FAIL"), flush=True)
    res["implied_spin"] = spins
    ok = ok and quantized
    print("  both members carry the same total spin: %s -> the degeneracy is SPATIAL, not SU(2)"
          % same_s, flush=True)
    res["s2_ground_doublet"], res["degeneracy_is_spatial"] = s2, bool(same_s)
    ok = ok and same_s

    res["all_controls_pass"] = bool(ok)
    out = os.path.join(HERE, "edrn_does_the_adiabatic_limit_pick_his_value.result.json")
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1)
    print("\nreceipt -> " + out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
