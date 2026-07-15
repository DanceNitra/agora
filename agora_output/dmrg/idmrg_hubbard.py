#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INFINITE DMRG (iDMRG) for the 1D Fermi-Hubbard chain at half filling, t=1.

Why iDMRG instead of finite L: the U=1 Mott charge gap is exponentially small
(Lieb-Wu Delta_c ~ 0.005), so the charge correlation length xi_c ~ v_c/Delta_c
~ 380 sites. Finite L<=320 sits AT that crossover and cannot resolve it. iDMRG
works DIRECTLY in the thermodynamic limit: the transfer-matrix correlation
length xi(chi) of the GAPPED charge sector SATURATES to the physical xi_c as
chi grows (a gapless sector would instead diverge with chi). We sweep chi, read
xi_charge, show the plateau, and cross-check Delta_c = v_c / xi_c against the
exact Lieb-Wu value. No finite-L extrapolation, no GPU needed.

TeNPy 1.1.0 API. Correctness-first.
"""
import os, json, time, argparse
import numpy as np

from tenpy.models.hubbard import FermiHubbardChain
from tenpy.networks.mps import MPS
from tenpy.algorithms import dmrg


def run_idmrg(U, chi, t=1.0, verbose=False):
    t0 = time.time()
    model_params = dict(
        L=2, t=t, U=U, mu=0.0,          # 2-site unit cell, half filling
        cons_N='N', cons_Sz='Sz',
        bc_MPS='infinite',
    )
    M = FermiHubbardChain(model_params)
    psi = MPS.from_product_state(M.lat.mps_sites(), ['up', 'down'], bc='infinite')

    dmrg_params = {
        'mixer': True,
        'mixer_params': {'amplitude': 1.e-5, 'decay': 2.0, 'disable_after': 40},
        'trunc_params': {'chi_max': chi, 'svd_min': 1.e-12},
        'combine': True,
        'min_sweeps': 30,
        'max_sweeps': 400,
        'max_E_err': 1.e-11,
        'max_S_err': 1.e-8,
    }
    eng = dmrg.TwoSiteDMRGEngine(psi, M, dmrg_params)
    E, psi = eng.run()                 # energy per site (infinite)

    # Sector-resolved correlation lengths from the transfer matrix. charges = [N, Sz]
    # (TeNPy Sz = 2*S_z). The single-particle (holon) sector dN=1,dSz=+-1 tracks the
    # CHARGE gap; dN=2 is the doublon; dN=0,dSz=2 is the (gapless) spin sector; the
    # trivial sector 0 is dominated by gapless spin (SzSz) and is not the charge scale.
    out = {"U": U, "chi": chi, "E_per_site": float(E),
           "max_chi": int(max(psi.chi)),
           "S": float(np.max(psi.entanglement_entropy())),
           "walltime_s": round(time.time() - t0, 1)}
    sectors = [("xi_triv", 0), ("xi_1p", [1, 1]), ("xi_doublon", [2, 0]), ("xi_spin", [0, 2])]
    for name, sec in sectors:
        try:
            xi = psi.correlation_length2(charge_sector=sec)
            out[name] = float(np.real(xi))
        except Exception as e:
            out[name] = f"ERR:{type(e).__name__}:{str(e)[:60]}"
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--U", type=float, default=1.0)
    ap.add_argument("--chi", type=int, default=None)
    ap.add_argument("--chis", type=str, default=None, help="comma list of chi to sweep")
    args = ap.parse_args()

    chis = [args.chi] if args.chi else ([int(x) for x in args.chis.split(",")] if args.chis else [64])
    outfile = f"idmrg_U{args.U:g}.json"
    results = json.load(open(outfile)) if os.path.exists(outfile) else []
    for chi in chis:
        r = run_idmrg(args.U, chi)
        results = [x for x in results if x.get("chi") != chi] + [r]   # replace same-chi
        json.dump(sorted(results, key=lambda x: x["chi"]), open(outfile, "w"), indent=2)
        def f(x): return f"{x:.2f}" if isinstance(x, float) else str(x)
        print(f"[iDMRG] U={r['U']} chi={r['chi']:4d}  E/site={r['E_per_site']:.8f}  "
              f"xi_1p={f(r.get('xi_1p'))}  xi_doublon={f(r.get('xi_doublon'))}  "
              f"xi_spin={f(r.get('xi_spin'))}  xi_triv={f(r.get('xi_triv'))}  "
              f"S={r['S']:.3f}  [{r['walltime_s']}s]", flush=True)
