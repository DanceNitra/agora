#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chi->infinity extrapolation of the OPEN-CHAIN single-bond defect scan (EDRN Prediction 1).

Why this run exists. The collaborator's defect scan (data/game1_log.csv, data/game1_L60_log.csv) is
the dataset behind Prediction 1: weaken ONE bond in the middle of an open Hubbard chain, sweep the
bond strength, and watch the spin gap respond while the topological index C stays flat. Every point
in it was computed at chi_max=100 and at a single bond dimension, so none of the published numbers
carries a convergence check. That mattered once already in this collaboration: the periodic-ring
defect point read A = 0.47 at chi=100 and moved to A = 3.19 +- 0.03 once extrapolated, and the
periodic C read 0.4996 at chi=100 against 0.9992 converged. A chi=100 number here is a candidate,
not a result.

Method (identical to scripts/u05_analysis.py and periodic_defect_chi_sweep.py, so the paper uses one
estimator throughout): for each (L, defect strength, sector) run chi = 100, 200, 300, 400 and
extrapolate the energy linearly in the discarded weight to dw -> 0 -- the standard MPS estimator,
since the truncation error in the energy is first order in the discarded weight. The spin gap is then
rebuilt from extrapolated energies, never from a mix of extrapolated and raw ones, and A = gap * L.

Geometry note: open chain, L-1 bonds, the weakened bond is the CENTER bond (index L//2 - 1), matching
the collaborator's game1_defect_scan.py exactly. We reproduce his chi=100 row first as a control --
if our chi=100 does not land on his, the two codes are not running the same system and nothing
downstream is comparable.

Each cell writes its own JSON so a partial run is still evidence and the run is resumable.
"""
import argparse
import json
import os
import pathlib
import time

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "2")

from tenpy.models.hubbard import FermiHubbardChain
from tenpy.networks.mps import MPS
from tenpy.algorithms import dmrg

HERE = pathlib.Path(__file__).resolve().parent
CELLS = HERE / "defect_scan"

U = 4.0
SV_MIN = 1e-10

# The collaborator's published grid, both chain lengths (data/game1_log.csv, data/game1_L60_log.csv).
# L=40 defect 0.8 appears in the manuscript's table but in NO committed CSV: the only repository row
# for that point (root game1_log.csv) reads delta_s = 6.5e-9, A = 0.000000 -- a run that failed to
# resolve the two spin sectors. We compute it ourselves so the published row has a data file behind it.
POINTS = [(40, d) for d in (0.5, 0.8, 1.0, 1.2, 1.5)] + \
         [(60, d) for d in (0.5, 0.8, 1.0, 1.2, 1.5)]
CHIS = (100, 200, 300, 400)

# His chi=100 A values, for the control comparison (L, defect) -> A.
PAPER_A = {
    (40, 0.5): 5.469862, (40, 1.0): 3.066727, (40, 1.2): 1.910170, (40, 1.5): 0.965498,
    (60, 0.5): 5.738530, (60, 0.8): 4.642328, (60, 1.0): 3.139223, (60, 1.2): 1.801868,
    (60, 1.5): 0.827740,
}


def build_model(L: int, defect: float) -> FermiHubbardChain:
    t = np.ones(L - 1)
    t[L // 2 - 1] = defect                    # same center bond as game1_defect_scan.py
    return FermiHubbardChain({
        "L": L, "t": t, "U": U,
        "cons_N": "N", "cons_Sz": "Sz",
        "bc_MPS": "finite",
    })


def product_state(L: int, sector: str):
    ps = ["up" if i % 2 == 0 else "down" for i in range(L)]
    if sector == "triplet":
        ps[ps.index("down")] = "up"           # Sz 0 -> 1 at fixed N
    return ps


def run_cell(L: int, defect: float, chi: int, sector: str) -> dict:
    model = build_model(L, defect)
    psi = MPS.from_product_state(model.lat.mps_sites(), product_state(L, sector), bc="finite")
    params = {
        "trunc_params": {"chi_max": chi, "svd_min": SV_MIN},
        "max_E_err": 1e-10,
        "max_S_err": 1e-8,
        # 60 sweeps, the same cap periodic_defect_chi_sweep.py used — one method across the paper,
        # and it bounds a cell so a slow corner of the grid cannot stall the whole run.
        "max_sweeps": 60,
        "mixer": True,
        # A low-chi cell IS badly truncated — that is the effect under study. Don't let TenPy's
        # consistency check abort it; we RECORD the discarded weight and extrapolate in it.
        "max_trunc_err": 1.0,
    }
    t0 = time.time()
    eng = dmrg.TwoSiteDMRGEngine(psi, model, params)
    E, psi = eng.run()
    stats = eng.sweep_stats
    disc = float(max(stats["max_trunc_err"][-3:])) if len(stats["max_trunc_err"]) else 0.0
    # Sanity: the state must actually be in the sector we asked for, or the gap is meaningless.
    sz = float(np.sum(psi.expectation_value("Sz")))
    n = float(np.sum(psi.expectation_value("Ntot")))
    return {
        "L": L, "defect": defect, "chi": chi, "sector": sector,
        "E": float(E),
        "disc_weight": disc,
        "sweeps": int(stats["sweep"][-1]),
        "max_chi": int(max(psi.chi)),
        "Sz_total": sz, "N_total": n,
        "sector_ok": bool(abs(sz - (1.0 if sector == "triplet" else 0.0)) < 1e-6
                          and abs(n - L) < 1e-6),
        "seconds": round(time.time() - t0, 1),
    }


def key(L, defect, chi, sector):
    return f"L{L}_d{defect}_chi{chi}_{sector}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", help="run ONE cell: L,defect,chi,sector")
    ap.add_argument("--smoke", action="store_true", help="tiny wiring check")
    args = ap.parse_args()
    CELLS.mkdir(exist_ok=True)

    if args.smoke:
        print(run_cell(8, 0.5, 64, "singlet"))
        return

    if args.cell:
        # .strip() on every field: a work list written on Windows carries CRLF, and a trailing \r in
        # the sector name produces a filename Windows rejects — AFTER the DMRG has already run, so
        # the cell is computed and then thrown away with an OSError. Parse defensively.
        L, defect, chi, sector = (x.strip() for x in args.cell.strip().split(","))
        L, defect, chi = int(L), float(defect), int(chi)
        out = CELLS / (key(L, defect, chi, sector) + ".json")
        if out.exists():
            print(f"skip {out.name}")
            return
        res = run_cell(L, defect, chi, sector)
        out.write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(f"{out.name}: E={res['E']:.10f} dw={res['disc_weight']:.3e} "
              f"ok={res['sector_ok']} {res['seconds']}s")
        return

    # No --cell: just print the work list, so the parallel driver can consume it.
    for L, d in POINTS:
        for chi in CHIS:
            for sector in ("singlet", "triplet"):
                if not (CELLS / (key(L, d, chi, sector) + ".json")).exists():
                    print(f"{L},{d},{chi},{sector}")


if __name__ == "__main__":
    main()
