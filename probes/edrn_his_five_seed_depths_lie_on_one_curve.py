"""His Table I calls five numbers seed scatter. They are five points on a one-parameter curve.

WHAT CHANGED. The manuscript submitted to CPL on 2026-08-22 already contains the degeneracy
analysis, and it is right: "Both ground states carry total spin S=1/2, so the two-fold degeneracy is
orbital -- the D_3 symmetry of the uniform gasket -- and it is what produces the scatter in valley
depth", with the gap to the next distinct level given as 0.1857. We measure S = 1/2, |Aut| = 6, and
1.857e-01 independently. The local radius-2 diagnostic, which is what we had prepared a critique of,
is no longer in the manuscript. So this file is not a correction. It is the one thing we can add.

THE CLAIM. Table I reports five Lanczos seeds at the fractal edge (0,6), all with valley position
s = 1.0000 and valley values

    0.159295   0.142707   0.143544   0.142196   0.146785

described as reflecting "the choice of ground state within a near-degenerate manifold rather than
statistical uncertainty". That reading is correct and it can be made exact. Write the density of any
state in the two-dimensional ground space as

    rho = (A+B)/2 + u (A-B)/2 + t C ,   u = cos(2 theta),  t = sin(2 theta) cos(phi)

where A, B, C are the per-edge correlation vectors of v0^2, v1^2 and v0 v1. The pairs (u, t) fill the
unit disc -- REAL superpositions are its boundary, states with a relative phase its interior -- and
the diagnostic depends on nothing except the Bloch radius r = sqrt(u^2 + t^2):

    E(r) = sqrt(a^2 + r^2 b^2),   a = 0.110269137,  b = 0.115461995

so the ENTIRE set of values reachable by any ground state is the closed interval [a, sqrt(a^2+b^2)].

THE TEST, AND WHY THE OBVIOUS ONE IS CIRCULAR. Solving r from one of his values and then recomputing
the value from that r is arithmetic; it agrees to 0e+00 for any number whatsoever inside the range,
and reporting that agreement as confirmation would be a fit with one free parameter per point. This
probe therefore tests the part that can fail:

  1. the law is fitted on NOTHING -- a and b are computed from the eigenvectors, not from his values;
  2. it is checked against many independently CONSTRUCTED states, where r is known in advance;
  3. the interval is a falsifiable prediction: NO ground state may give a value outside [a, b'], and
     a random search over the disc is run specifically to try to produce one;
  4. only then are his five values checked for membership. Any one outside would kill the law.

CONTROLS:
  * POSITIVE: seed 0 on his 27-edge script must reproduce his published E_global(s=1) = 0.159658;
  * the r = 0 state must be a genuine PURE eigenstate, not a density-matrix average -- the chiral
    combination (|v0> + i|v1>)/sqrt(2), checked by its residual and by restoring the D_3 symmetry;
  * NEGATIVE: a deliberately out-of-range value must be rejected by the membership test, or the test
    admits everything and has measured nothing.

Run:  python probes/edrn_his_five_seed_depths_lie_on_one_curve.py
"""
from __future__ import annotations
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from edrn_his_valley_bottom_is_a_start_vector import (  # noqa: E402
    build_hamiltonian, _sp_table, ground_space, single_vector_density, edge_orbits,
    HIS_EDGES, N, N_UP)

HIS_TABLE_I = [0.159295, 0.142707, 0.143544, 0.142196, 0.146785]
HIS_27EDGE_AT_S1 = 0.159658
HIS_GAP = 0.1857


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ok = True
    res = {}

    H1, basis = build_hamiltonian(N, HIS_EDGES, np.ones(len(HIS_EDGES)), N_UP)
    sp = _sp_table(basis, HIS_EDGES)
    e0, d, vecs, gap = ground_space(H1)
    v0, v1 = vecs[:, 0], vecs[:, 1]
    print("ground space: degeneracy %d, gap to next distinct level %.4f (his manuscript: %.4f)"
          % (d, gap, HIS_GAP), flush=True)
    res["degeneracy"], res["gap"] = d, gap
    gap_ok = abs(gap - HIS_GAP) < 5e-4 and d == 2
    print("  agrees with his manuscript: %s" % ("PASS" if gap_ok else "FAIL"), flush=True)
    ok = ok and gap_ok

    # ---- CONTROL (positive): his 27-edge number -------------------------------------------------
    e_seed0 = float(np.std(sp @ single_vector_density(H1, 0)))
    pc = abs(e_seed0 - HIS_27EDGE_AT_S1) < 5e-6
    print("CONTROL his 27-edge E_global(s=1) = %.6f ; here %.6f  %s"
          % (HIS_27EDGE_AT_S1, e_seed0, "PASS" if pc else "FAIL"), flush=True)
    ok = ok and pc
    if not pc:
        return 1

    # ---- the law, fitted on nothing -------------------------------------------------------------
    A, B, C = sp @ (v0 ** 2), sp @ (v1 ** 2), sp @ (v0 * v1)
    a = float(np.std((A + B) / 2.0))
    hi = float(np.std(A))
    b = (hi ** 2 - a ** 2) ** 0.5
    print("\nE(r) = sqrt(a^2 + r^2 b^2) with a = %.9f, b = %.9f, taken from the eigenvectors"
          % (a, b), flush=True)
    print("reachable interval: [%.9f, %.9f]" % (a, hi), flush=True)
    res["a"], res["b"], res["interval"] = a, b, [a, hi]

    # ---- 1. predict CONSTRUCTED states, where r is known before the value is computed ------------
    rng = np.random.default_rng(20260822)
    worst = 0.0
    n_built = 0
    for _ in range(2000):
        u, t = rng.uniform(-1, 1, 2)
        r2 = u * u + t * t
        if r2 > 1.0:
            continue
        q = (A + B) / 2.0 + u * (A - B) / 2.0 + t * C
        worst = max(worst, abs(float(np.std(q)) - (a * a + r2 * b * b) ** 0.5))
        n_built += 1
    print("\nlaw vs %d constructed states with r known in advance: max |error| = %.3e"
          % (n_built, worst), flush=True)
    law_ok = worst < 1e-9
    print("  CONTROL the law predicts states it was not built from: %s"
          % ("PASS" if law_ok else "FAIL"), flush=True)
    ok = ok and law_ok
    res["law_max_error"], res["law_n_states"] = worst, n_built

    # ---- 2. the falsifiable half: try hard to escape the interval --------------------------------
    escapes, lo_seen, hi_seen = 0, 1e9, -1e9
    for _ in range(20000):
        th = rng.uniform(0, np.pi)
        ph = rng.uniform(0, 2 * np.pi)
        psi = np.cos(th) * v0 + np.exp(1j * ph) * np.sin(th) * v1
        psi = psi / np.linalg.norm(psi)
        val = float(np.std(sp @ (np.abs(psi) ** 2)))
        lo_seen, hi_seen = min(lo_seen, val), max(hi_seen, val)
        if val < a - 1e-9 or val > hi + 1e-9:
            escapes += 1
    print("20000 random ground states: span %.9f .. %.9f, escapes from the interval: %d"
          % (lo_seen, hi_seen, escapes), flush=True)
    esc_ok = escapes == 0
    print("  CONTROL nothing escapes the predicted interval: %s"
          % ("PASS" if esc_ok else "FAIL"), flush=True)
    ok = ok and esc_ok
    res["random_span"], res["escapes"] = [lo_seen, hi_seen], escapes

    # ---- 3. NOW his five values, and this is a membership test, not a fit ------------------------
    print("\nhis Table I values against the interval predicted WITHOUT them:", flush=True)
    inside = []
    for i, v in enumerate(HIS_TABLE_I):
        r = ((v * v - a * a) / (b * b)) ** 0.5 if v * v >= a * a else float("nan")
        ins = a - 1e-9 <= v <= hi + 1e-9
        inside.append(ins)
        print("  seed %d  %.6f   %s   implied r = %.4f"
              % (i, v, "inside" if ins else "OUTSIDE -- the law is dead", r), flush=True)
    all_in = all(inside)
    print("  all five inside: %s" % ("PASS" if all_in else "FAIL"), flush=True)
    ok = ok and all_in
    res["his_values"], res["all_inside"] = HIS_TABLE_I, bool(all_in)
    res["implied_radii"] = [float(((v * v - a * a) / (b * b)) ** 0.5) for v in HIS_TABLE_I]

    # ---- CONTROL (negative): the membership test must REJECT something ---------------------------
    bogus = [a - 0.01, hi + 0.01]
    rejected = all(not (a - 1e-9 <= v <= hi + 1e-9) for v in bogus)
    print("  CONTROL two out-of-range values are rejected: %s"
          % ("PASS" if rejected else "FAIL -- the test admits everything"), flush=True)
    ok = ok and rejected

    # ---- the r = 0 endpoint is a PURE state, not an averaging convention -------------------------
    psi = (v0 + 1j * v1) / np.sqrt(2.0)
    resid = float(np.linalg.norm(H1 @ psi - e0 * psi))
    q = np.abs(psi) ** 2
    corr = sp @ q
    orbits, n_auto = edge_orbits(HIS_EDGES, N)
    worst_orb = max(float(corr[o].max() - corr[o].min()) for o in orbits)
    val0 = float(np.std(corr))
    print("\nthe r = 0 endpoint is the chiral PURE state (|v0> + i|v1>)/sqrt(2):", flush=True)
    print("  residual ||(H-E0)psi|| = %.2e, value %.9f, within-orbit spread %.2e (|Aut| = %d)"
          % (resid, val0, worst_orb, n_auto), flush=True)
    pure_ok = resid < 1e-10 and abs(val0 - a) < 1e-9 and worst_orb < 1e-9
    print("  CONTROL it is a genuine eigenstate AND it restores the D_3 symmetry: %s"
          % ("PASS" if pure_ok else "FAIL"), flush=True)
    ok = ok and pure_ok
    res["chiral_residual"], res["chiral_value"] = resid, val0
    res["chiral_within_orbit_spread"] = worst_orb

    print("\n" + "=" * 92)
    print("His five depths are not scatter and not statistics. Every ground state of this")
    print("Hamiltonian gives a value on E(r) = sqrt(%.6f^2 + r^2 %.6f^2), so the whole" % (a, b))
    print("reachable set is [%.6f, %.6f] and his five sit at r = %s."
          % (a, hi, ", ".join("%.2f" % x for x in res["implied_radii"])))
    print("The r = 0 end is a single pure state that restores the D_3 symmetry exactly, so the")
    print("table can become one number and a stated prescription instead of a five-row range.")
    print("=" * 92)

    res["all_controls_pass"] = bool(ok)
    out = os.path.join(HERE, "edrn_his_five_seed_depths_lie_on_one_curve.result.json")
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1)
    print("receipt -> " + out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
