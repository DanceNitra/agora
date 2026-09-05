"""The ground manifold's reachable diagnosis is an INTERVAL, and a real rotation test reports a point.

WHY THIS EXISTS, and it is a correction of my own measurement made an hour ago. Two probes written
today rotated a degenerate ground eigenspace with REAL orthogonal matrices (`np.linalg.qr` of a real
Gaussian) and concluded that on the L2 gasket at s = 1 the enhanced diagnosis is the same for every
member of the two-fold manifold, spread 1.8e-15. From that I was about to tell a first author that
four of his five published Table 1 values cannot come from the ground manifold.

That is wrong, and our own thread already says so. Comment 5380781829, sent on 2026-08-31, records
that every ground state gives a value on E(r) = sqrt(a^2 + r^2 b^2), so the reachable set is a closed
interval and his five values sit inside it at r = 1.00, 0.78, 0.80, 0.78 and 0.84. The states that
move the diagnosis are COMPLEX superpositions, the chiral combination among them. A real rotation of
a real basis cannot reach them, so my test could only ever return the endpoint it started from.

THE FIX, and it is the one this repository already wrote down after the ring: compute the extrema,
do not sample. For a two-dimensional manifold the diagnosis is a quadratic form on a disc, so the
range can be obtained exactly rather than approached.

    psi = cos(theta) v0 + e^{i phi} sin(theta) v1, with v0, v1 the real ARPACK basis
    c_e = m_e + u p_e + t q_e,  u = cos 2theta,  t = sin 2theta cos phi,  u^2 + t^2 <= 1

so the per-edge correlations trace a disc in an affine plane, and the diagnosis is the norm of a
centred vector over that disc. Its extrema are computed in closed form and cross-checked on a grid.

CONTROLS, each able to fail:
  * THE REAL-ROTATION ARM IS RUN AS A NEGATIVE CONTROL and must MISS the range. If real rotations
    reproduce the interval, then the blindness this probe exists to document is not real.
  * TWO INDEPENDENT ROUTES TO THE RANGE: the closed form and a dense grid over the disc. They must
    agree, or neither is reported.
  * THE PUBLISHED FIVE MUST LIE INSIDE. Table 1's five values are checked against the computed
    interval. If any falls outside, the interval does not explain them and the probe says so.
  * THE RECORDED PARAMETERS ARE THE TARGET. Our own sent comment states a = 0.110269137 and
    b = 0.115461995. The probe recomputes them and compares, so this is a re-derivation of a number
    we have already published rather than a fresh assertion.
  * THE ENDPOINT MUST BE A REAL EIGENSTATE. The r = 0 minimiser is checked as an eigenvector by its
    residual, so "reachable" means a state of the system, not a point in a parametrisation.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "agora_output", "edrn_submission"))
OUT = os.path.join(HERE,
                   "the_manifold_reachable_set_is_an_interval_and_real_rotations_cannot_see_it"
                   ".result.json")

HIS_EDGES = [(0, 6), (0, 8), (1, 9), (1, 11), (2, 12), (2, 14),
             (3, 6), (3, 7), (3, 9), (3, 10), (4, 10), (4, 11), (4, 12), (4, 13),
             (5, 7), (5, 8), (5, 13), (5, 14),
             (6, 7), (7, 8), (9, 10), (10, 11), (12, 13), (13, 14),
             (6, 8), (9, 11), (12, 14)]
CONTRA = (0, 6)
N_UP = 7
S_VALLEY = 1.0
PUBLISHED_FIVE = [0.159295, 0.142707, 0.143544, 0.142196, 0.146785]
RECORDED = {"a": 0.110269137, "b": 0.115461995}      # from our own comment 5380781829
GRID = 1441
REAL_ROTATIONS = 400


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def main():
    import numpy as np
    from scipy.sparse.linalg import eigsh
    from regenerate_edge_8_14 import build_H, sector_basis

    print("  serial: one 6435-dimensional sector, a closed form, a %dx%d grid and %d real rotations"
          % (GRID, GRID // 4, REAL_ROTATIONS))

    basis = sector_basis(15, N_UP)
    H = build_H(HIS_EDGES, CONTRA, S_VALLEY, basis)
    w, v = eigsh(H, k=4, which="SA")
    o = np.argsort(w)
    w, v = w[o], v[:, o]
    deg = int(sum(1 for x in w if abs(x - w[0]) < 1e-9))
    if deg != 2:
        refuse("the ground level is %d-fold, not the two-fold level this parametrisation assumes"
               % deg)
    v0, v1 = v[:, 0], v[:, 1]

    # Per-edge zz operators, diagonal in this basis.
    Z = np.empty((len(HIS_EDGES), len(basis)))
    for i, (a, b) in enumerate(HIS_EDGES):
        Z[i] = np.array([(1.0 if (st >> a) & 1 else -1.0) * (1.0 if (st >> b) & 1 else -1.0)
                         for st in basis])

    A = Z @ (v0 ** 2)
    B = Z @ (v1 ** 2)
    C = Z @ (v0 * v1)
    m = 0.5 * (A + B)
    p = 0.5 * (A - B)
    q = C

    n = len(HIS_EDGES)
    M = m - m.mean()
    P = p - p.mean()
    Q = q - q.mean()

    def diag(u, t):
        d = M + u * P + t * Q
        return float(np.sqrt(np.mean(d * d)))

    # CLOSED FORM. |M + uP + tQ|^2 is a quadratic in (u,t) on the unit disc.
    G = np.array([[P @ P, P @ Q], [P @ Q, Q @ Q]])
    lin = np.array([M @ P, M @ Q])
    print("  cross terms: M.P = %.3e, M.Q = %.3e, P.Q = %.3e, |P|=%.6f, |Q|=%.6f"
          % (lin[0], lin[1], G[0, 1], np.sqrt(G[0, 0]), np.sqrt(G[1, 1])))

    # Extrema on the closed disc: interior stationary point plus the boundary circle.
    cands = []
    try:
        uv = np.linalg.solve(G, -lin)
        if uv @ uv <= 1.0:
            cands.append(tuple(uv))
    except np.linalg.LinAlgError:
        pass
    th = np.linspace(0, 2 * np.pi, 20001)
    for c, s in zip(np.cos(th), np.sin(th)):
        cands.append((c, s))
    vals = np.array([diag(u, t) for u, t in cands])
    closed_min, closed_max = float(vals.min()), float(vals.max())
    arg_min = cands[int(vals.argmin())]

    # GRID, as an independent route over the same disc.
    rs = np.linspace(0.0, 1.0, GRID // 4)
    ps = np.linspace(0.0, 2 * np.pi, GRID)
    gmin, gmax = np.inf, -np.inf
    for r in rs:
        u = r * np.cos(ps)
        t = r * np.sin(ps)
        d = M[:, None] + np.outer(P, u) + np.outer(Q, t)
        val = np.sqrt((d * d).mean(axis=0))
        gmin = min(gmin, float(val.min()))
        gmax = max(gmax, float(val.max()))
    print("  closed form: %.9f to %.9f" % (closed_min, closed_max))
    print("  dense grid : %.9f to %.9f" % (gmin, gmax))
    if abs(gmin - closed_min) > 1e-6 or abs(gmax - closed_max) > 1e-6:
        refuse("the two routes disagree (%.9f/%.9f against %.9f/%.9f)"
               % (closed_min, closed_max, gmin, gmax))

    # NEGATIVE CONTROL: real rotations only, the test that reported a point.
    rng = np.random.default_rng(0)
    space = np.column_stack([v0, v1])
    real_vals = []
    for _ in range(REAL_ROTATIONS):
        R, _r = np.linalg.qr(rng.standard_normal((2, 2)))
        rot = space @ R
        real_vals.append(float(np.std(Z @ (rot[:, 0] ** 2))))
    real_spread = max(real_vals) - min(real_vals)
    print("  real-rotation arm: %.9f to %.9f, spread %.3e"
          % (min(real_vals), max(real_vals), real_spread))
    interval = closed_max - closed_min
    if real_spread > 0.01 * interval:
        refuse("real rotations already span %.2e of the %.2e interval, so they are not blind and "
               "this probe's premise is wrong" % (real_spread, interval))
    print("  the real-rotation arm sees %.2e of an interval of %.6f, so it is blind to it"
          % (real_spread, interval))

    # THE RECORDED PARAMETERS: E(r) = sqrt(a^2 + r^2 b^2).
    a_meas, b_meas = closed_min, float(np.sqrt(max(closed_max ** 2 - closed_min ** 2, 0.0)))
    print("  recomputed a = %.9f (recorded %.9f), b = %.9f (recorded %.9f)"
          % (a_meas, RECORDED["a"], b_meas, RECORDED["b"]))
    a_ok = abs(a_meas - RECORDED["a"]) < 1e-5
    b_ok = abs(b_meas - RECORDED["b"]) < 1e-5

    # The minimiser has to be an actual eigenstate.
    u0, t0 = arg_min
    r0 = float(np.hypot(u0, t0))
    if r0 < 1e-9:
        theta, phi = np.pi / 4, np.pi / 2                   # the chiral combination
        psi = (np.cos(theta) * v0 + 1j * np.sin(theta) * v1)
    else:
        theta = 0.5 * np.arccos(np.clip(u0, -1, 1))
        cosphi = np.clip(t0 / max(np.sin(2 * theta), 1e-15), -1, 1)
        psi = np.cos(theta) * v0 + np.exp(1j * np.arccos(cosphi)) * np.sin(theta) * v1
    psi = psi / np.linalg.norm(psi)
    resid = float(np.linalg.norm(H @ psi - w[0] * psi))
    print("  minimiser at (u,t) = (%.4f, %.4f), r = %.4f, eigen-residual %.2e" % (u0, t0, r0, resid))
    if resid > 1e-9:
        refuse("the minimising state has residual %.2e, so it is not an eigenstate and 'reachable' "
               "would be a claim about a parametrisation rather than about the system" % resid)

    # THE PUBLISHED FIVE MUST LIE INSIDE.
    inside = [x for x in PUBLISHED_FIVE if closed_min - 1e-6 <= x <= closed_max + 1e-6]
    print()
    print("  Table 1's five values inside [%.6f, %.6f]: %d of %d"
          % (closed_min, closed_max, len(inside), len(PUBLISHED_FIVE)))
    for x in PUBLISHED_FIVE:
        r = float(np.sqrt(max((x ** 2 - closed_min ** 2), 0.0)) / b_meas) if b_meas else float("nan")
        print("     %.6f  ->  r = %.3f  %s" % (x, r, "inside" if x in inside else "OUTSIDE"))
    if len(inside) != len(PUBLISHED_FIVE):
        print("  NOT EXPLAINED: at least one published value lies outside the reachable interval.")

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "graph": "L2 Sierpinski gasket, his labelling", "edge": list(CONTRA),
        "sector_n_up": N_UP, "s": S_VALLEY, "ground_degeneracy": deg,
        "reachable_interval": [closed_min, closed_max],
        "grid_interval": [gmin, gmax],
        "a_recomputed": a_meas, "b_recomputed": b_meas, "recorded": RECORDED,
        "a_matches_record": a_ok, "b_matches_record": b_ok,
        "real_rotation_range": [min(real_vals), max(real_vals)], "real_rotation_spread": real_spread,
        "minimiser": {"u": u0, "t": t0, "r": r0, "eigen_residual": resid},
        "published_five": PUBLISHED_FIVE,
        "published_five_inside": len(inside),
        "controls": {
            "closed_form_and_grid_agree": True,
            "real_rotation_arm_run_as_a_negative_control": True,
            "minimiser_verified_as_an_eigenstate": True,
            "recorded_parameters_recomputed": bool(a_ok and b_ok),
            "published_values_checked_against_the_interval": True,
        },
        "supersedes": ["the_projection_average_makes_the_baseline_unique.result.json",
                       "does_the_baseline_defect_reach_the_papers_headline_number.result.json",
                       "where_table_1s_five_seed_values_come_from.result.json"],
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
