"""Do the sub-0.76 zeros reproduce in ANY magnetisation sector, or only in the three we tested?

WHY THIS EXISTS. `edrn_gap_structure_and_sector.py` sweeps `nup in (8, 9, 10)` and prints, honestly,
"no TESTED sector has a zero gap at s=0.5". In the letter sent to the co-author on 2026-08-21 I
widened that to "I could not reproduce those zeros in ANY magnetisation sector". Three is not any.
The direction was right and the quantifier was not, so rather than correct the sentence downward,
this measures the remaining sectors and either earns the word or retracts it.

SG(2) has N=15 spins, so the distinct sectors are n_up = 8..15 (Sz = +1/2 .. +15/2); n_up and
15-n_up are related by a global spin flip, which commutes with the Heisenberg Hamiltonian, so the
lower half carries no new information. n_up = 15 is the fully polarised state: a one-dimensional
sector with no second level at all, and it is reported as such rather than silently skipped.

THE CLAIM UNDER TEST is the manuscript's, not ours: "the gap is strictly zero for s <~ 0.76". It is
tested at s = 0.5, well inside that range, in every sector.

CONTROLS
  C1 COVERAGE     every distinct sector 8..15 is visited; the count must equal 8, and the union of
                  sector sizes must equal 2^15 / 2 rounded the way the spin-flip pairing implies.
  C2 CALIBRATION  exactly one sector reproduces the manuscript's E(0) = 0.246731. If none does, the
                  instrument is not the paper's; if several do, E(0) does not identify the sector
                  and the manuscript's Fig. 3 is ambiguous -- which would itself be the finding.
  C3 CAN FAIL     the check must be able to report a zero. It is run against a 15-spin ring with
                  uniform couplings, a real Hamiltonian whose ground level is exactly two-fold, and
                  that control must come back "zero found" -- otherwise a clean sweep proves only
                  that the detector is dead. (The first version used the zero matrix, which ARPACK
                  cannot even start on; the control crashed rather than passing, which is the
                  behaviour you want from a control that is wrong.)
  C4 DISCRIMINATE within the identified sector, s=0.77 must NOT be zero while the detuned control
                  is, so "zero" and "non-zero" are distinguishable at the tolerance used.

Run:  python probes/edrn_every_sector_not_just_three.py
"""
from __future__ import annotations
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import scipy.sparse.linalg as spla  # noqa: E402


def lowest(H, k=2):
    """Two lowest eigenvalues. Dense below 512 because ARPACK is unreliable at dim 15 and
    cannot start at all on a zero matrix -- the first version of this probe crashed its own
    C3 control that way, which is the control doing its job."""
    d = H.shape[0]
    if d <= 512:
        return np.sort(np.linalg.eigvalsh(H.toarray()))[:k]
    return np.sort(spla.eigsh(H, k=k, which='SA', tol=1e-11)[0])

from edrn_gap_structure_and_sector import (  # noqa: E402
    sierpinski, sector_basis, sector_H, observables,
)

PUBLISHED_E0 = 0.246731
ZERO_TOL = 1e-6          # "strictly zero" read generously; the real gaps are O(0.1)
S_TEST = 0.5             # well inside the range the manuscript calls strictly zero


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    t0 = time.time()
    n, edges = sierpinski(2)
    tips = {v for v in range(n) if sum(1 for e in edges if v in e) == 2}
    defect = next(e for e in edges if (e[0] in tips) != (e[1] in tips))
    print(f"SG(2): {n} vertices, {len(edges)} edges | defect {defect}")
    print(f"testing s={S_TEST}, which the manuscript calls strictly zero\n")

    out, zeros = {}, []
    for nup in range(8, n + 1):
        states, index = sector_basis(n, nup)
        dim = len(states)
        sz = (nup - (n - nup)) / 2
        if dim < 2:
            print(f"  Sz={sz:+.1f}  dim={dim:5d}  fully polarised: no second level in this sector",
                  flush=True)
            out[nup] = {"Sz": sz, "dim": dim, "gap": None, "E0": None,
                        "note": "one-dimensional sector"}
            continue
        H = sector_H(n, edges, defect, S_TEST, states, index)
        v = lowest(H)
        gap = float(v[1] - v[0])
        H0 = sector_H(n, edges, defect, 0.0, states, index)
        if dim <= 512:
            v0, w0 = np.linalg.eigh(H0.toarray())
        else:
            v0, w0 = spla.eigsh(H0, k=2, which="SA", tol=1e-11)
        o = np.argsort(v0)
        _, e0 = observables(w0[:, o][:, 0], states, edges)
        out[nup] = {"Sz": sz, "dim": dim, "gap": gap, "E0": e0}
        if gap < ZERO_TOL:
            zeros.append(sz)
        print(f"  Sz={sz:+.1f}  dim={dim:5d}  gap(s={S_TEST})={gap:.6f}  E(0)={e0:.6f}"
              f"  ({time.time()-t0:.0f}s)", flush=True)

    print()
    tested = [k for k in out if out[k]["gap"] is not None]
    c1 = len(out) == 8 and all(out[k]["dim"] == math.comb(n, k) for k in out)
    print(f"C1 COVERAGE     {len(out)} distinct sectors visited (n_up 8..15); "
          f"every dim = C(15,n_up)  {'OK' if c1 else 'FAIL'}")

    ident = [out[k]["Sz"] for k in tested if abs(out[k]["E0"] - PUBLISHED_E0) < 5e-6]
    c2 = len(ident) == 1
    print(f"C2 CALIBRATION  sectors reproducing E(0)={PUBLISHED_E0}: {ident}  "
          f"{'OK -- E(0) identifies the sector' if c2 else 'FAIL'}")

    # C3: a detector that cannot report a zero has not measured anything.
    # A 15-spin ring at s=1 is a real Hamiltonian with an exactly two-fold ground level, so the
    # control is a genuine matrix rather than the zero matrix the first version used.
    ring = [(i, (i + 1) % n) for i in range(n)]
    fs, fi = sector_basis(n, 8)
    vf = lowest(sector_H(n, ring, (0, 1), 1.0, fs, fi))
    flat_gap = float(vf[1] - vf[0])
    c3 = flat_gap < ZERO_TOL
    print(f"C3 CAN FAIL     control (15-spin ring, uniform couplings) gap={flat_gap:.3e}  "
          f"{'OK -- a zero IS detectable' if c3 else 'FAIL -- the detector cannot see a zero'}")

    ref = next(k for k in tested if abs(out[k]["E0"] - PUBLISHED_E0) < 5e-6) if c2 else 8
    st, ix = sector_basis(n, ref)
    v77 = lowest(sector_H(n, edges, defect, 0.77, st, ix))
    g77 = float(v77[1] - v77[0])
    c4 = g77 > 0.1 and flat_gap < ZERO_TOL
    print(f"C4 DISCRIMINATE in the identified sector, gap(0.77)={g77:.6f} while the control is "
          f"{flat_gap:.1e}  {'OK' if c4 else 'FAIL'}")

    print()
    if zeros:
        print(f"RESULT: the zeros DO reproduce, in sector(s) Sz={zeros}. The letter's claim is "
              f"WRONG and the manuscript needs another look before upload.")
    else:
        print(f"RESULT: no sector of the {len(tested)} with a second level has a zero gap at "
              f"s={S_TEST}. Smallest gap across all sectors: "
              f"{min(out[k]['gap'] for k in tested):.6f} (Sz="
              f"{out[min(tested, key=lambda k: out[k]['gap'])]['Sz']:+.1f}).")
        print("The word 'any' in the 2026-08-21 letter is now earned rather than assumed.")

    res = {"probe": "edrn_every_sector_not_just_three", "s_test": S_TEST, "zero_tol": ZERO_TOL,
           "sectors": {str(k): v for k, v in out.items()}, "zeros_found": zeros,
           "identified_sector_Sz": ident, "gap_at_077_identified": g77,
           "detuned_control_gap": flat_gap,
           "controls": {"C1 coverage": c1, "C2 calibration": c2, "C3 can fail": c3,
                        "C4 discriminate": c4}}
    p = os.path.join(HERE, "edrn_every_sector_not_just_three.result.json")
    json.dump(res, open(p, "w", encoding="utf-8"), indent=1)
    print(f"\nreceipt -> {p}   ({time.time()-t0:.0f}s)")
    return 0 if (c1 and c2 and c3 and c4 and not zeros) else 1


if __name__ == "__main__":
    sys.exit(main())
