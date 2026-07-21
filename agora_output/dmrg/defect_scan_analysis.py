#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild the defect scan from chi->infinity extrapolated energies, and unify the C normalization.

Two separate corrections land in the same table, and they should not be confused with each other:

1. CONVERGENCE. Every published defect-scan number came from a single chi=100 run. Here each
   (L, defect, sector) energy is extrapolated linearly in the discarded weight to dw -> 0, the gap is
   rebuilt from extrapolated energies only, and A = gap * L. Same estimator as u05_analysis.py and
   periodic_defect_chi_sweep.py, so the paper carries one method throughout.

2. NORMALIZATION. The manuscript compares C values computed two different ways, which is what made a
   ring look 48% less connected than an open chain. Both scripts use

       C = (Omega * edge_count) / (L * (L - 1) / 2)

   but they accumulate Omega differently, and that is the whole discrepancy:

       predict1_topology_spin.py:  bond = |<Cu Cdu>| + |<Cd Cdd>|          # SUM of spin channels
       game1_defect_scan.py:72     omega_sum += (bond_up + bond_dn) / 2.0  # MEAN of spin channels
       menu2_periodic.py:88        omega_sum += (bond_up + bond_dn) / 2.0  # MEAN, same as the scan

   So the defect scan's C column is exactly half the convention used in predict1_topology_spin.csv.
   The check that settles it, on data both sides already hold: the scan at defect strength 1.0 IS the
   uniform L=40 chain, it reports C = 0.479442, twice that is 0.958884, and
   predict1_topology_spin.csv's L=40 row reads 0.9588847979. Identical to seven digits. We therefore
   restate every scan C in the SUM convention -- one convention across the paper, no new physics.

Run after defect_scan_chi_sweep.py has filled defect_scan/.
"""
import json
import pathlib
import re
import collections

HERE = pathlib.Path(__file__).resolve().parent
CELLS = HERE / "defect_scan"

PAPER_A = {   # the manuscript's published values. (40, 0.8) is the row with NO committed CSV behind
              # it -- the only repository record reads A = 0.000000 -- so it is listed here from the
              # manuscript table itself, and our own run is what gives it provenance.
    (40, 0.5): 5.469862, (40, 0.8): 4.366600, (40, 1.0): 3.066727, (40, 1.2): 1.910170,
    (40, 1.5): 0.965498,
    (60, 0.5): 5.738530, (60, 0.8): 4.642328, (60, 1.0): 3.139223, (60, 1.2): 1.801868,
    (60, 1.5): 0.827740,
}
PAPER_C = {                        # published as Omega/L
    (40, 0.5): 0.475369, (40, 0.8): 0.478021, (40, 1.0): 0.479442, (40, 1.2): 0.480129,
    (40, 1.5): 0.480227,
    (60, 0.5): 0.479309, (60, 0.8): 0.481096, (60, 1.0): 0.482060, (60, 1.2): 0.482524,
    (60, 1.5): 0.482635,
}


def extrapolate(series: dict):
    """E at dw -> 0 by least squares on (discarded weight, E). Returns (E0, n_points, chis)."""
    pts = sorted((c["disc_weight"], c["E"], c["chi"]) for c in series.values())
    if len(pts) < 2:
        return (pts[0][1], len(pts), [p[2] for p in pts]) if pts else (None, 0, [])
    n = len(pts)
    sx = sum(x for x, _, _ in pts)
    sy = sum(y for _, y, _ in pts)
    sxx = sum(x * x for x, _, _ in pts)
    sxy = sum(x * y for x, y, _ in pts)
    den = n * sxx - sx * sx
    if abs(den) < 1e-30:
        return sum(y for _, y, _ in pts) / n, n, [p[2] for p in pts]
    slope = (n * sxy - sx * sy) / den
    return (sy - slope * sx) / n, n, [p[2] for p in pts]


def main():
    cells = collections.defaultdict(dict)
    incomplete = []
    for p in sorted(CELLS.glob("L*_d*_chi*_*.json")):
        m = re.match(r"L(\d+)_d([\d.]+)_chi(\d+)_(\w+)\.json", p.name)
        if not m:
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if not d.get("sector_ok", True):
            incomplete.append(p.name + " (WRONG SECTOR)")
            continue
        cells[(int(m.group(1)), float(m.group(2)), m.group(4))][int(m.group(3))] = d

    print("chi->infinity extrapolated open-chain defect scan (U=4, center bond weakened)\n")
    print(f"{'L':>3} {'defect':>7} {'A(chi=100)':>11} {'A(chi->inf)':>12} {'shift':>8} "
          f"{'chis':>18} {'C published':>12} {'C consistent':>13}")
    print("-" * 92)

    rows = []
    for (L, d) in sorted({(k[0], k[1]) for k in cells}):
        s = cells.get((L, d, "singlet"), {})
        t = cells.get((L, d, "triplet"), {})
        if not s or not t:
            incomplete.append(f"L={L} defect={d}: singlet {len(s)} chis, triplet {len(t)} chis")
            continue
        Es, ns, chis_s = extrapolate(s)
        Et, nt, chis_t = extrapolate(t)
        if Es is None or Et is None:
            continue
        gap = Et - Es
        A = gap * L
        a100 = PAPER_A.get((L, d))
        c_pub = PAPER_C.get((L, d))
        # The scan accumulates the MEAN of the two spin channels and predict1_topology_spin.py their
        # SUM (see the module docstring), so restating the scan in the paper's convention is exactly
        # a factor of two -- verified against the uniform-chain row to seven digits.
        c_cons = c_pub * 2 if c_pub is not None else None
        shift = (A - a100) / a100 * 100 if a100 else float("nan")
        rows.append({"L": L, "defect": d, "A_chi100": a100, "A_extrap": A,
                     "shift_pct": shift, "gap": gap, "chis": sorted(set(chis_s) | set(chis_t)),
                     "C_published": c_pub, "C_consistent": c_cons})
        print(f"{L:>3} {d:>7} {a100 if a100 else 0:>11.6f} {A:>12.6f} {shift:>7.1f}% "
              f"{str(sorted(set(chis_s))):>18} {c_pub if c_pub else 0:>12.6f} "
              f"{c_cons if c_cons else 0:>13.6f}")

    if incomplete:
        print("\nNOT USABLE YET (a partial cell is not a result):")
        for x in incomplete:
            print("  -", x)

    out = HERE / "defect_scan_extrapolated.json"
    out.write_text(json.dumps({"rows": rows, "incomplete": incomplete}, indent=1), encoding="utf-8")
    print(f"\nwrote {out}")

    if rows:
        worst = max(rows, key=lambda r: abs(r["shift_pct"]))
        print(f"\nlargest chi=100 bias: L={worst['L']} defect={worst['defect']} "
              f"{worst['A_chi100']:.4f} -> {worst['A_extrap']:.4f} ({worst['shift_pct']:+.1f}%)")


if __name__ == "__main__":
    main()
