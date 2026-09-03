"""Does averaging over the ground manifold actually remove the baseline's arbitrariness?

CORRECTED 2026-09-03, AND THE CORRECTION IS THE POINT. An earlier version of this file rotated the
degenerate eigenspace with REAL orthogonal matrices only. On a real ARPACK basis that reaches one
point of the manifold, so it reported the diagnosis as basis independent when the reachable set is a
closed interval [0.110269, 0.159658] whose interior needs COMPLEX superpositions. The extrema are
computed, not sampled, in
`probes/the_manifold_reachable_set_is_an_interval_and_real_rotations_cannot_see_it.py`, which also
runs the real-rotation arm as a negative control and measures its blindness at 8.3e-16 of the
interval. Read that file's result before citing anything here about how far a single vector can move.

WHAT SURVIVES THAT CORRECTION AND WHAT DOES NOT. The manifold average is invariant under ANY unitary
change of basis of the eigenspace, complex included, because it is the diagonal of the spectral
projector, so the remedy result stands. The single-vector spread reported below is a LOWER BOUND: it
is what real rotations reach, not what the manifold contains.

WHY. E(0) for random edge (8,14) moves by 9.522e-02 across twelve Lanczos seeds, because the
sector's ground level at s = 0 is two-fold degenerate and the solver returns an arbitrary member.
The remedy we intend to recommend is to define E(0) on the whole manifold rather than on one vector.
That is easy to assert and it is the kind of assertion that should be shown, since the fix is the
part of a report a reader acts on.

THE TEST. Take the degenerate ground eigenspace, rotate its basis at random 200 times, and compute
the diagnosis two ways on every rotation: from a single basis vector, and averaged over the whole
eigenspace. A quantity that depends on the basis is not a property of the ground state.

CONTROLS, each able to fail:
  * THE SINGLE-VECTOR ARM MUST SCATTER. If it does not, the rotations are not reaching the
    freedom the seeds reach, the instrument is blind, and the flat projection arm proves nothing.
    Its range is also compared against the twelve-seed range already measured.
  * A NON-DEGENERATE CONTROL. The same rotation test at the valley, where the level is simple, must
    leave both arms flat. That separates "the average is stable" from "the average is constant".
  * THE EIGENSPACE IS VERIFIED BEFORE IT IS ROTATED: the probe asserts the ground level really is
    degenerate at the tolerance used, so a rotation of a one-dimensional space is not reported as
    evidence of anything.
  * THE ROTATIONS ARE ORTHONORMAL, checked numerically, so a badly conditioned draw cannot pass as
    a basis.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "the_projection_average_makes_the_baseline_unique.result.json")

N = 15
N_UP = 7
TOL = 1e-9
ROTATIONS = 200
CASES = [("baseline s=0", 0.0), ("valley s=1.20", 1.20)]
TWELVE_SEED_RANGE = [0.234140129, 0.329364953]   # measured, single vector, E(0)


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def main():
    import numpy as np
    import networkx as nx
    from scipy.sparse.linalg import eigsh
    from table_2_random_depth_is_a_seed_draw import his_basis, his_H

    print("  serial: %d rotations x %d cases, one eigendecomposition each case" % (ROTATIONS, 2))
    edges = [tuple(sorted(e)) for e in nx.gnm_random_graph(15, 27, seed=42).edges()]
    contra = (8, 14)
    basis = his_basis(N, N_UP)
    zz = {}
    for (a, b) in edges:
        zz[(a, b)] = np.array([(1 if a in st else -1) * (1 if b in st else -1) for st in basis],
                              dtype=float)

    out = {}
    for label, s in CASES:
        J = np.ones(len(edges))
        J[edges.index(contra)] = s
        H = his_H(N, edges, J, basis)
        w, v = eigsh(H, k=6, which="SA")
        o = np.argsort(w)
        w, v = w[o], v[:, o]
        deg = int(sum(1 for x in w if abs(x - w[0]) < TOL))
        space = v[:, :deg]
        print("  %-14s ground degeneracy %d, gap %.2e" % (label, deg, w[deg] - w[0]))

        single, averaged = [], []
        rng = np.random.default_rng(0)
        for _ in range(ROTATIONS):
            if deg > 1:
                q, _r = np.linalg.qr(rng.standard_normal((deg, deg)))
                if abs(np.abs(np.linalg.det(q)) - 1.0) > 1e-9:
                    refuse("a rotation was not orthonormal, so the basis draw is unusable")
                rot = space @ q
            else:
                rot = space
            p_first = np.abs(rot[:, 0]) ** 2
            corr_first, corr_avg = [], []
            for e in edges:
                corr_first.append(float(p_first @ zz[e]))
                vals = [float((np.abs(rot[:, k]) ** 2) @ zz[e]) for k in range(deg)]
                corr_avg.append(float(np.mean(vals)))
            single.append(float(np.std(corr_first)))
            averaged.append(float(np.std(corr_avg)))

        sp_single = max(single) - min(single)
        sp_avg = max(averaged) - min(averaged)
        out[label] = {"degeneracy": deg, "gap": float(w[deg] - w[0]),
                      "single_vector": {"min": min(single), "max": max(single), "spread": sp_single},
                      "manifold_average": {"min": min(averaged), "max": max(averaged),
                                           "spread": sp_avg}}
        print("     single vector    : %.9f to %.9f, spread %.3e"
              % (min(single), max(single), sp_single))
        print("     manifold average : %.9f to %.9f, spread %.3e"
              % (min(averaged), max(averaged), sp_avg))

    b = out["baseline s=0"]
    if b["degeneracy"] < 2:
        refuse("the baseline level is not degenerate at tolerance %g, so there is nothing to rotate"
               % TOL)
    if b["single_vector"]["spread"] < 1e-6:
        refuse("the single-vector arm did not scatter under rotation, so this test cannot see the "
               "freedom the seeds see and the flat average proves nothing")
    if b["manifold_average"]["spread"] > 1e-9:
        refuse("the manifold average is NOT basis independent (spread %.2e); the remedy we were "
               "about to recommend does not work" % b["manifold_average"]["spread"])

    v = out["valley s=1.20"]
    if v["single_vector"]["spread"] > 1e-9:
        refuse("the non-degenerate control scattered, so the rotation machinery is unsound")

    seen = b["single_vector"]
    covered = (seen["min"] <= TWELVE_SEED_RANGE[0] + 1e-6
               and seen["max"] >= TWELVE_SEED_RANGE[1] - 1e-6)
    print()
    print("  rotation range %.6f..%.6f against the twelve-seed range %.6f..%.6f: %s"
          % (seen["min"], seen["max"], TWELVE_SEED_RANGE[0], TWELVE_SEED_RANGE[1],
             "covers it" if covered else "does NOT cover it"))
    print("  VERDICT: the manifold average is basis independent; the single vector is not")

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "edge": list(contra), "sector_n_up": N_UP, "rotations": ROTATIONS,
        "cases": out,
        "twelve_seed_range": TWELVE_SEED_RANGE,
        "rotation_range_covers_the_seed_range": covered,
        "verdict": "MANIFOLD_AVERAGE_IS_BASIS_INDEPENDENT",
        "controls": {
            "single_vector_arm_scattered": True,
            "non_degenerate_control_stayed_flat": True,
            "degeneracy_verified_before_rotating": True,
            "rotations_checked_orthonormal": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
