#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMRG study of the 1D Fermi-Hubbard chain (half filling, OBC, t=1, U/t=1.0).
TenPy v1.0+ API. Correctness-first; parameterized; incremental JSON output.

Expected sane result (finite-size-artifact hypothesis): at U/t=1 the charge gap
is exponentially small (Lieb-Wu), so the local charge exponent alpha(L) should
DRIFT TOWARD 0 as L grows and chi->inf; the spin sector is gapless so its
exponent stays ~ -1 and A = Delta_s * L ~ const. A charge exponent pinned near
-1 at large L/chi would instead argue for a real thermodynamic gap.
"""

import os, json, time, argparse, logging
import numpy as np

# Live per-sweep visibility: TenPy's DMRG engine logs one INFO line per sweep
# (sweep #, energy, entropy, max truncation). Route that logger to _live.log so a
# long run is watchable in real time ( tail -f _live.log ) instead of opaque.
LIVE_LOG = "_live.log"


def setup_live_logging():
    lg = logging.getLogger("tenpy")
    lg.setLevel(logging.INFO)
    lg.handlers = [h for h in lg.handlers if getattr(h, "_inspeximus_live", False)]
    if not lg.handlers:
        fh = logging.FileHandler(LIVE_LOG, mode="w")
        fh._inspeximus_live = True
        fh.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s",
                                          datefmt="%H:%M:%S"))
        lg.addHandler(fh)
    lg.propagate = False

from tenpy.models.hubbard import FermiHubbardChain
from tenpy.networks.mps import MPS
from tenpy.algorithms import dmrg

LS   = [40, 80, 160, 320]
CHIS = [100, 200, 300, 400, 500, 600]   # 500/600 only needed where chi=400 under-converges (L=320)
U    = 1.0
T    = 1.0
SECTORS = ["singlet", "Nm1", "Np1", "triplet"]
OUTFILE = "hubbard_dmrg_results.json"


def make_product_state(L, sector):
    # Sector pinned by the initial product state's conserved (N, Sz).
    # SpinHalfFermionSite: 'empty'(N0,Sz0) 'up'(N1,Sz+1) 'down'(N1,Sz-1) 'full'(N2,Sz0).
    # TenPy 'Sz' charge = 2*S_z; physical S_z=1 triplet = charge-Sz=+2.
    assert L % 2 == 0, "half filling singlet needs even L"
    ps = ['up' if i % 2 == 0 else 'down' for i in range(L)]
    j = ps.index('down')
    if sector == "singlet":
        pass
    elif sector == "Nm1":
        ps[j] = 'empty'
    elif sector == "Np1":
        ps[j] = 'full'
    elif sector == "triplet":
        ps[j] = 'up'
    else:
        raise ValueError(sector)
    return ps


def expected_counts(L, sector):
    # (N_target, PHYSICAL Sz_target). expectation_value('Sz') returns physical S_z
    # (+-1/2 per electron), so targets are in physical units: removing one 'down'
    # leaves net S_z=+1/2; the triplet member has S_z=1.
    if sector == "singlet":  return L,   0.0
    if sector == "Nm1":      return L-1, 0.5
    if sector == "Np1":      return L+1, 0.5
    if sector == "triplet":  return L,   1.0
    raise ValueError(sector)


def run_sector(L, chi, sector):
    t0 = time.time()
    model_params = dict(
        L=L, t=T, U=U, mu=0.0,
        cons_N='N', cons_Sz='Sz',
        bc_MPS='finite',              # finite MPS => OPEN boundary conditions
    )
    M = FermiHubbardChain(model_params)
    ps = make_product_state(L, sector)
    psi = MPS.from_product_state(M.lat.mps_sites(), ps, bc=M.lat.bc_MPS)

    # Convergence schedule scales with L: at small U the entanglement is high, so
    # large chains need MANY more sweeps and a longer-lived mixer or they
    # under-converge and can FAKE the alpha->0 drift (reviewer's highest risk).
    # max_sweeps is a CAP, not a target: a too-small chi can never reach max_E_err,
    # so an unbounded cap makes it spin (chi=100/L=80 hit 251 sweeps = 16 min for a
    # mere low anchor). DMRG with the mixer converges in tens of sweeps when chi is
    # adequate; if it can't in this cap, that chi is simply inadequate (a signal).
    if L >= 300:
        disable_after, min_sw, max_sw = 100, 60, 250   # L=320 under-converged at cap 120
    elif L >= 160:
        disable_after, min_sw, max_sw = 60, 40, 120
    elif L >= 80:
        disable_after, min_sw, max_sw = 40, 25, 90
    else:
        disable_after, min_sw, max_sw = 30, 20, 70
    dmrg_params = {
        'mixer': True,
        'mixer_params': {'amplitude': 1.e-5, 'decay': 2.0, 'disable_after': disable_after},
        'trunc_params': {'chi_max': chi, 'svd_min': 1.e-10},
        'combine': True,
        'min_sweeps': min_sw,
        'max_sweeps': max_sw,
        'max_E_err': 1.e-10,
        'max_S_err': 1.e-6,
    }
    eng = dmrg.TwoSiteDMRGEngine(psi, M, dmrg_params)
    E, psi = eng.run()

    # chi->inf extrapolation x-variable. The reviewer flagged max_trunc_err (a
    # single worst bond) as noisier than the TOTAL discarded weight of the final
    # sweep; take the total when TenPy exposes per-update errors, else fall back.
    max_trunc = float(eng.sweep_stats['max_trunc_err'][-1])
    try:
        errs = eng.update_stats['err']
        nb = 2 * (L - 1)                          # updates in one full two-site sweep
        total_disc = float(sum(getattr(e, 'eps', 0.0) for e in errs[-nb:]))
        if not (total_disc > 0):
            total_disc = max_trunc
    except Exception:
        total_disc = max_trunc
    disc_weight = total_disc
    n_sweeps    = int(eng.sweep_stats['sweep'][-1])
    Es          = eng.sweep_stats['E']
    dE_last     = float(Es[-1] - Es[-2]) if len(Es) > 1 else float('nan')
    max_chi     = int(max(psi.chi))
    try:
        var = float(M.H_MPO.variance(psi))
    except Exception:
        var = None

    N_meas  = float(np.sum(psi.expectation_value('Ntot')))
    Sz_meas = float(np.sum(psi.expectation_value('Sz')))   # physical S_z
    N_tar, Sz_tar = expected_counts(L, sector)
    ok = (abs(N_meas - N_tar) < 1e-6) and (abs(Sz_meas - Sz_tar) < 1e-6)

    return {
        "L": L, "chi": chi, "sector": sector, "E": float(E),
        "disc_weight": disc_weight, "max_trunc_err": max_trunc,
        "energy_variance": var, "n_sweeps": n_sweeps, "dE_last_sweep": dE_last,
        "max_chi_reached": max_chi,
        "N_measured": N_meas, "N_target": N_tar,
        "Sz_measured": Sz_meas, "Sz_target": Sz_tar,
        "sector_ok": bool(ok), "walltime_s": round(time.time() - t0, 1),
    }


CELLDIR = "cells"   # per-cell result files, so parallel workers never race on one JSON


def load_results():
    res = {}
    if os.path.exists(OUTFILE):
        with open(OUTFILE) as f:
            res = json.load(f)
    merge_cells(res)
    return res


def merge_cells(res):
    if not os.path.isdir(CELLDIR):
        return res
    for fn in os.listdir(CELLDIR):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(CELLDIR, fn)) as f:
                cell = json.load(f)
            res.update(cell)   # each cell file is {key: result}
        except Exception:
            pass
    return res


def save_cell(k, r):
    os.makedirs(CELLDIR, exist_ok=True)
    tmp = os.path.join(CELLDIR, k + ".json.tmp")
    with open(tmp, "w") as f:
        json.dump({k: r}, f, indent=2)
    os.replace(tmp, os.path.join(CELLDIR, k + ".json"))


def save_results(res):
    tmp = OUTFILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(res, f, indent=2)
    os.replace(tmp, OUTFILE)


def key(L, chi, sector):
    return f"L{L}_chi{chi}_{sector}"


def extrapolate_energy(points):
    # linear in discarded weight w (leading DMRG variational error): E(w)~E_inf+a*w
    w = np.array([p[0] for p in points], float)
    E = np.array([p[1] for p in points], float)
    if len(w) < 2 or np.ptp(w) == 0:
        return float(E[np.argmin(w)]), 0.0, 0.0
    A = np.vstack([w, np.ones_like(w)]).T
    (slope, intercept), res, *_ = np.linalg.lstsq(A, E, rcond=None)
    resid = float(res[0]) if len(res) else 0.0
    return float(intercept), float(slope), resid


def gaps_from_energies(E):
    dE = E["singlet"] - E["Nm1"]                    # collaborator's charge gap
    dc = E["Np1"] + E["Nm1"] - 2 * E["singlet"]     # single-particle Mott gap
    ds = E["triplet"] - E["singlet"]                # spin gap
    return {
        "charge_gap_dE": dE, "charge_gap_Mott_dc": dc, "spin_gap_ds": ds,
        "chi_c_proxy": (1.0 / dE) if abs(dE) > 1e-15 else None,
    }


def analyze(res):
    out = {"per_L": {}, "alpha": {}}
    Einf = {L: {} for L in LS}
    for L in LS:
        entry = {"E_extrap": {}, "extrap_diag": {}, "E_by_chi": {}}
        for sector in SECTORS:
            pts = []
            for chi in CHIS:
                r = res.get(key(L, chi, sector))
                if r is None:
                    continue
                pts.append((r["disc_weight"], r["E"]))
                entry["E_by_chi"].setdefault(str(chi), {})[sector] = r["E"]
            if not pts:
                continue
            E_inf, slope, resid = extrapolate_energy(pts)
            Einf[L][sector] = E_inf
            entry["E_extrap"][sector] = E_inf
            entry["extrap_diag"][sector] = {"slope": slope, "resid": resid, "n_points": len(pts)}
        if all(s in Einf[L] for s in SECTORS):
            entry["gaps_chi_inf"] = gaps_from_energies(Einf[L])
        entry["gaps_by_chi"] = {}
        for chi in CHIS:
            Echi = {s: res[key(L, chi, s)]["E"] for s in SECTORS if key(L, chi, s) in res}
            if len(Echi) == len(SECTORS):
                g = gaps_from_energies(Echi)
                g["A_spin_times_L"] = g["spin_gap_ds"] * L
                entry["gaps_by_chi"][str(chi)] = g
        if "gaps_chi_inf" in entry:
            entry["gaps_chi_inf"]["A_spin_times_L"] = entry["gaps_chi_inf"]["spin_gap_ds"] * L
        out["per_L"][str(L)] = entry

    def alpha_series(gap_name):
        series = []
        for L1, L2 in zip(LS[:-1], LS[1:]):
            g1 = out["per_L"].get(str(L1), {}).get("gaps_chi_inf")
            g2 = out["per_L"].get(str(L2), {}).get("gaps_chi_inf")
            if not g1 or not g2:
                continue
            v1, v2 = g1[gap_name], g2[gap_name]
            if v1 is None or v2 is None or v1 <= 0 or v2 <= 0:
                series.append({"L1": L1, "L2": L2, "alpha": None, "note": "non-positive gap"})
                continue
            a = (np.log(v2) - np.log(v1)) / (np.log(L2) - np.log(L1))
            series.append({"L1": L1, "L2": L2, "alpha": float(a)})
        return series

    out["alpha"]["charge_dE"]   = alpha_series("charge_gap_dE")
    out["alpha"]["charge_Mott"] = alpha_series("charge_gap_Mott_dc")
    out["alpha"]["spin"]        = alpha_series("spin_gap_ds")
    return out


def main():
    global U, CELLDIR, OUTFILE, LS
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=None)
    ap.add_argument("--chi", type=int, default=None)
    ap.add_argument("--sector", type=str, default=None, choices=SECTORS)
    ap.add_argument("--U", type=float, default=1.0)
    ap.add_argument("--Ls", type=str, default=None, help="comma list overriding LS (for analyze)")
    ap.add_argument("--analyze-only", action="store_true")
    args = ap.parse_args()

    # U-aware output paths so different U runs never collide (U=1.0 keeps the
    # original 'cells'/ dir for backward compat with the existing dataset).
    U = args.U
    if abs(U - 1.0) > 1e-9:
        CELLDIR = f"cells_U{U:g}"
        OUTFILE = f"hubbard_dmrg_results_U{U:g}.json"
    if args.Ls:
        LS = [int(x) for x in args.Ls.split(",")]

    res = load_results()
    # single-cell mode (all three specified) => one worker, writes its own cell file,
    # never touches the shared JSON. This is what the parallel driver invokes.
    single_cell = bool(args.L and args.chi and args.sector)
    if not args.analyze_only:
        setup_live_logging()
        Ls   = [args.L] if args.L else LS
        chis = [args.chi] if args.chi else CHIS
        secs = [args.sector] if args.sector else SECTORS
        for L in Ls:
            for chi in chis:
                for sector in secs:
                    k = key(L, chi, sector)
                    if k in res and res[k].get("sector_ok", False):
                        print(f"[skip] {k} (done)")
                        continue
                    print(f"[run ] {k} ...", flush=True)
                    logging.getLogger("tenpy").info(f"===== START {k} =====")
                    try:
                        r = run_sector(L, chi, sector)
                    except Exception as e:
                        print(f"[FAIL] {k}: {e}", flush=True)
                        res[k] = {"error": str(e)}
                        if single_cell:
                            save_cell(k, res[k])
                        else:
                            save_results(res)
                        continue
                    res[k] = r
                    if single_cell:
                        save_cell(k, r)
                    else:
                        save_results(res)
                    flag = "OK " if r["sector_ok"] else "!! SECTOR MISMATCH"
                    print(f"[done] {k}: E={r['E']:.10f} w={r['disc_weight']:.2e} "
                          f"var={r['energy_variance']} sweeps={r['n_sweeps']} "
                          f"N={r['N_measured']:.3f}/{r['N_target']} "
                          f"Sz={r['Sz_measured']:.3f}/{r['Sz_target']} "
                          f"[{flag}] {r['walltime_s']}s", flush=True)

    analysis = analyze(res)
    with open("hubbard_dmrg_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)
    print("\n=== gaps (chi->inf) and local exponents ===")
    for L in LS:
        e = analysis["per_L"].get(str(L), {})
        g = e.get("gaps_chi_inf")
        if g:
            print(f"L={L:4d}  dE={g['charge_gap_dE']:.6e}  dc(Mott)={g['charge_gap_Mott_dc']:.6e}  "
                  f"ds={g['spin_gap_ds']:.6e}  A={g['A_spin_times_L']:.4f}")
    print("alpha(charge dE):  ", analysis["alpha"]["charge_dE"])
    print("alpha(charge Mott):", analysis["alpha"]["charge_Mott"])
    print("alpha(spin):       ", analysis["alpha"]["spin"])


if __name__ == "__main__":
    main()
