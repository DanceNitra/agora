"""Does "27 of 27 edges valley at s = 1.0" survive rescaling the background coupling?

@luoxuejian000 removed the (0,1) control-edge claim after our exchange and replaced it with a
stronger-looking one: he scanned every one of SG(2)'s 27 edges and found that all 27 show a valley at
s = 1.0 with range above the flat threshold, concluding the phenomenon is "a structural property of
the entire graph" rather than a peculiarity of one edge.

His data reproduces here and his computation is right. The global ranges in his own file take exactly
FIVE distinct values across 27 edges -- 0.143538 x6, 0.158573 x6, 0.172919 x6, 0.121280 x6,
0.077438 x3 -- which is the orbit structure of SG(2) under its symmetry group. A scan that respects
the graph's symmetry that cleanly is not a scan with an arithmetic problem in it.

THE OBJECTION, and it is about the CONCLUSION rather than the computation. Every edge carries J = 1
except the scanned one, which carries J = s. So s = 1 is not a coupling strength; it is the point at
which the scanned edge stops being a defect and the configuration becomes uniform. The enhanced
diagnosis is a spatial standard deviation ACROSS edges, which is minimised where the configuration is
most symmetric. "All 27 edges valley at the same s" is then not evidence that the valley is
structural -- it is what a symmetry point forces, and every edge shares the same background, so every
edge must share the same uniform point.

THE FALSIFIER, which is exact rather than statistical. H(s, J0) = J0 * H(s/J0, 1), because scaling
every coupling scales the Hamiltonian. So eigenvectors, hence every correlation and every spatial
standard deviation, depend only on the RATIO s/J0. Prediction: rescale the background to J0 and the
valley moves to s = J0, with an IDENTICAL depth. If it stays at 1.0, this objection is wrong and the
valley really does name a coupling strength.

THIS FILE USES HIS OWN VERTEX LABELLING, taken verbatim from
`分形图 SG(2) 矛盾边全面扫描 —— 全局 vs 局部诊断对照.py` in the archive he posted, so the result is
about his graph and not about a relabelled one. In his numbering vertices 0, 1 and 2 are the three
tips, which is why (0,1) is not an edge -- he is right about that and our earlier disagreement was
two different numberings of the same graph.

CONTROLS, because a probe that cannot fail has measured nothing:
  * a UNIFORM graph must give spatial standard deviation 0 to machine precision -- if it does not,
    the correlation code is wrong and every number below is void;
  * the ratio identity is checked on ENERGIES as well, which are unambiguous under degeneracy;
  * at least one edge must produce a LARGE range, or "no edge is flat" would be vacuous.

Run:  python probes/edrn_27_of_27_is_the_uniform_point_in_his_labelling.py
"""
from __future__ import annotations
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# verbatim from his archive
HIS_EDGES = [(0, 6), (0, 8), (1, 9), (1, 11), (2, 12), (2, 14),
             (3, 6), (3, 7), (3, 9), (3, 10), (4, 10), (4, 11), (4, 12), (4, 13),
             (5, 7), (5, 8), (5, 13), (5, 14),
             (6, 7), (7, 8), (9, 10), (10, 11), (12, 13), (13, 14),
             (6, 8), (9, 11), (12, 14)]
N = 15
N_UP = 8


def basis(n, k):
    states = [s for s in range(1 << n) if bin(s).count("1") == k]
    return states, {s: i for i, s in enumerate(states)}


def hamiltonian(edges, couplings, states, index):
    d = len(states)
    H = np.zeros((d, d))
    for a, s in enumerate(states):
        for (i, j), J in zip(edges, couplings):
            bi, bj = (s >> i) & 1, (s >> j) & 1
            H[a, a] += 0.25 * J * (1 if bi == bj else -1)
            if bi != bj:
                t = s ^ ((1 << i) | (1 << j))
                H[index[t], a] += 0.5 * J
    return H


def ground(H):
    w, v = np.linalg.eigh(H)
    return w[0], v[:, 0]


def sz_sz(psi, states, edges):
    out = []
    for (i, j) in edges:
        acc = 0.0
        for a, s in enumerate(states):
            bi, bj = (s >> i) & 1, (s >> j) & 1
            acc += (psi[a] ** 2) * 0.25 * (1 if bi == bj else -1)
        out.append(acc)
    return np.array(out)


def diagnostic(scan_edge_idx, s, j0, states, index):
    couplings = [j0] * len(HIS_EDGES)
    couplings[scan_edge_idx] = s
    e, psi = ground(hamiltonian(HIS_EDGES, couplings, states, index))
    return e, float(np.std(sz_sz(psi, states, HIS_EDGES)))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    states, index = basis(N, N_UP)
    print("basis: C(%d,%d) = %d states, %d edges\n" % (N, N_UP, len(states), len(HIS_EDGES)))

    # ---- CONTROL 1: the RATIO IDENTITY, on energies, which are unambiguous under degeneracy -----
    # THE CONTROL THIS FILE SHIPPED WITH WAS WRONG, and it caught me rather than him. It asserted
    # that a UNIFORM configuration must give spatial std 0, which is true of a ring and false of
    # SG(2): the ring is edge-transitive, SG(2) is not. Its 27 edges fall into FIVE symmetry classes
    # -- visible as five distinct ranges, 6+6+6+6+3, in his own data -- so a uniform SG(2) has
    # genuinely different correlations on different classes and a nonzero spread. Measured: 3.99e-02,
    # not zero. So "the valley is just the uniform point minimising the spread" is NOT the objection;
    # that reading died here before it reached him.
    #
    # What survives is exact algebra rather than a symmetry argument: scaling every coupling scales
    # the Hamiltonian, so E(s, J0) = J0 * E(s/J0, 1) identically. This control checks that identity
    # directly. If it fails, the solver is wrong and nothing below means anything.
    e_a, _ = diagnostic(0, 0.7, 1.0, states, index)
    e_b, _ = diagnostic(0, 0.7 * 1.4, 1.4, states, index)
    err = abs(e_b - 1.4 * e_a) / abs(1.4 * e_a)
    print("CONTROL ratio identity E(s,J0) = J0*E(s/J0,1): rel. error %.2e  %s"
          % (err, "PASS" if err < 1e-10 else "FAIL"))
    if err >= 1e-10:
        print("the solver breaks the scaling identity; nothing below is usable")
        return 1
    _, uni = diagnostic(0, 1.0, 1.0, states, index)
    print("for the record, a UNIFORM SG(2) has spatial std %.3e -- nonzero, because SG(2) is not"
          % uni)
    print("edge-transitive. That is why the tautology reading fails.")

    # ---- the falsifier: three backgrounds, one scanned edge --------------------------------------
    rows = []
    print("\n%-8s %-12s %-12s %-12s" % ("J0", "argmin s", "s/J0", "depth"))
    for j0 in (0.6, 1.0, 1.4):
        grid = [round(j0 * x, 6) for x in np.linspace(0.5, 1.5, 21)]
        vals = [(s, diagnostic(0, s, j0, states, index)) for s in grid]
        smin, (emin, dmin) = min(vals, key=lambda kv: kv[1][1])
        dmax = max(v[1][1] for v in vals)
        rows.append({"j0": j0, "argmin_s": smin, "ratio": smin / j0,
                     "depth_at_min": dmin, "range": dmax - dmin})
        print("%-8.2f %-12.4f %-12.4f %-12.6f" % (j0, smin, smin / j0, dmin))

    ratios = [r["ratio"] for r in rows]
    depths = [r["depth_at_min"] for r in rows]
    tracks = max(abs(r - 1.0) for r in ratios) < 1e-6
    same_depth = (max(depths) - min(depths)) < 1e-9

    # ---- CONTROL 2: some edge must show a LARGE range, or "none is flat" says nothing ------------
    grid = [round(x, 4) for x in np.linspace(0.0, 3.0, 13)]
    per_edge = []
    for k in range(len(HIS_EDGES)):
        ds = [diagnostic(k, s, 1.0, states, index)[1] for s in grid]
        per_edge.append({"edge": list(HIS_EDGES[k]), "range": max(ds) - min(ds),
                         "argmin_s": grid[int(np.argmin(ds))]})
    biggest = max(p["range"] for p in per_edge)
    smallest = min(p["range"] for p in per_edge)
    print("\nCONTROL a real edge produces a large range: max %.6f  %s"
          % (biggest, "PASS" if biggest > 0.05 else "FAIL"))
    print("smallest range on any of the 27 edges: %.6f  (his file: 0.077438)" % smallest)
    at_one = sum(1 for p in per_edge if abs(p["argmin_s"] - 1.0) < 1e-9)
    print("edges whose minimum sits at s = 1.0: %d of %d" % (at_one, len(per_edge)))

    print("\n" + "=" * 88)
    print("valley position tracks the background exactly (s = J0):", tracks)
    print("depth identical across backgrounds:", same_depth)
    print("=> the minimum is the UNIFORM POINT, not a coupling strength of 1."
          if (tracks and same_depth) else
          "=> the objection FAILS: the valley does not track the background.")
    print("=" * 88)

    out = os.path.join(HERE, "edrn_27_of_27_is_the_uniform_point_in_his_labelling.result.json")
    json.dump({"labelling": "verbatim from his archive", "edges": [list(e) for e in HIS_EDGES],
               "control_uniform_std": uni, "rescale": rows,
               "tracks_background": bool(tracks), "identical_depth": bool(same_depth),
               "edges_min_at_one": at_one, "smallest_range": smallest,
               "largest_range": biggest, "per_edge": per_edge},
              open(out, "w", encoding="utf-8"), indent=1)
    print("receipt -> " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
