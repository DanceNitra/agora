#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chi->infinity extrapolation of the PERIODIC-ring weak-bond spin gap (EDRN Direction-2 gatekeeping).

The collaborator's L=40, U=4 ring with one 0.5t bond gave A = Ds*L = 0.47 at chi_max=100 — physically
impossible (a weak bond cannot disconnect a ring; A must land in [~3.07 open-chain, ~3.53 uniform ring])
and flagged as the classic periodic-MPS under-convergence trap (chi_PBC ~ chi_OBC^2; a norm_err on each
state does not converge a GAP). This runner does the discriminating check we publicly offered:

  L=40, U=4, t=1, ONE bond weakened to 0.5t, bc_x='periodic' (finite MPS carries the ring the long way),
  sectors singlet (half-filling Sz=0) and triplet (Sz=1), chi sweep 100 -> 200 -> 300 -> 400 (600 reserve),
  E extrapolated linearly in the discarded weight per sector; gap from the extrapolated energies.

Expected outcome: A(chi) climbs from ~0.47-ish at low chi back into the [3.07, 3.53] window as chi grows.
Incremental JSON so a partial run is still evidence. Smoke: --smoke runs L=8/chi=64 to validate wiring.
"""
import os, json, time, argparse
import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "4")

from tenpy.models.hubbard import FermiHubbardModel
from tenpy.networks.mps import MPS
from tenpy.algorithms import dmrg

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "periodic_defect_chi_sweep.json")

U = 4.0
T_UNIFORM = 1.0
T_DEFECT = 0.5


def build_model(L, defect=True):
    # site-dependent hopping on a PERIODIC chain: L bonds (bond i = site i -- site i+1 mod L, wrap = L-1).
    t = np.full(L, T_UNIFORM)
    if defect:
        t[L // 2] = T_DEFECT              # one weakened bond in the "bulk" of the MPS path
    # FermiHubbardModel (general MPO model): the periodic wrap bond is long-range for the MPS,
    # which a NearestNeighborModel (FermiHubbardChain) refuses — exactly the hard case we're testing.
    return FermiHubbardModel({
        "lattice": "Chain", "L": L, "t": t, "U": U, "mu": 0.0,
        "bc_MPS": "finite", "bc_x": "periodic",
    })


def product_state(L, sector):
    ps = ["up" if i % 2 == 0 else "down" for i in range(L)]
    if sector == "triplet":
        ps[ps.index("down")] = "up"      # Sz 0 -> 1 (charge 2*Sz = +2), N unchanged
    return ps


def run_point(L, chi, sector, defect=True, sweeps_cap=60):
    model = build_model(L, defect)
    psi = MPS.from_product_state(model.lat.mps_sites(), product_state(L, sector), bc=model.lat.bc_MPS)
    eng = dmrg.TwoSiteDMRGEngine(psi, model, {
        "mixer": True,
        "max_E_err": 1.e-10,
        "max_sweeps": sweeps_cap,
        # the ring at low chi IS badly truncated — that's the effect under study. Don't let TenPy's
        # consistency check kill the run; we RECORD disc_weight and extrapolate instead of hiding it.
        "max_trunc_err": 1.0,
        "trunc_params": {"chi_max": chi, "svd_min": 1.e-10},
    })
    t0 = time.time()
    E, psi = eng.run()
    stats = eng.sweep_stats
    disc = float(max(stats["max_trunc_err"][-3:])) if len(stats["max_trunc_err"]) else 0.0
    return {"L": L, "chi": chi, "sector": sector, "E": float(E),
            "disc_weight": disc, "sweeps": int(stats["sweep"][-1]),
            "max_chi": int(max(psi.chi)), "secs": round(time.time() - t0, 1)}


def key(L, chi, s, mode="defect"):
    return f"{mode}_L{L}_chi{chi}_{s}"


def extrapolate(points):
    """Linear E vs disc_weight -> E at disc=0. Falls back to the largest-chi E if <2 points."""
    if len(points) < 2:
        return points[-1][1], "single-point"
    x = np.array([p[0] for p in points]); y = np.array([p[1] for p in points])
    a, b = np.polyfit(x, y, 1)
    return float(b), f"linear fit over {len(points)} chis"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--chis", default="100,200,300,400")
    ap.add_argument("--mode", default="defect", choices=["defect", "uniform"],
                    help="defect = the Direction-2 point; uniform = instrument control (must reproduce his A=3.5262)")
    ap.add_argument("--point", default=None,
                    help="MODE,CHI,SECTOR — run exactly one point, write to periodic_pts/<key>.json (parallel-safe)")
    ap.add_argument("--report", action="store_true", help="merge periodic_pts/*.json and report gaps + extrapolation")
    a = ap.parse_args()
    L = 8 if a.smoke else 40
    pts_dir = os.path.join(HERE, "periodic_pts"); os.makedirs(pts_dir, exist_ok=True)
    if a.point:
        mode, chi_s, sector = a.point.split(",")
        chi = int(chi_s)
        k = key(L, chi, sector, mode)
        f = os.path.join(pts_dir, k + ".json")
        if os.path.exists(f):
            print(f"[skip] {k} exists"); return
        r = run_point(L, chi, sector, defect=(mode == "defect"))
        json.dump(r, open(f, "w"), indent=1)
        print(f"{k}: E={r['E']:.8f} disc={r['disc_weight']:.2e} sweeps={r['sweeps']} ({r['secs']}s)")
        return
    if a.report:
        allpts = {}
        for fn in os.listdir(pts_dir):
            if fn.endswith(".json"):
                allpts[fn[:-5]] = json.load(open(os.path.join(pts_dir, fn)))
        for mode in ("uniform", "defect"):
            print(f"--- {mode} ---")
            for chi in (100, 200, 300, 400, 600):
                ks, kt = key(L, chi, "singlet", mode), key(L, chi, "triplet", mode)
                if ks in allpts and kt in allpts:
                    ds = allpts[kt]["E"] - allpts[ks]["E"]
                    print(f"  chi={chi}: Ds={ds:.6f}  A={ds*L:.4f}  "
                          f"(disc s={allpts[ks]['disc_weight']:.1e} t={allpts[kt]['disc_weight']:.1e})")
            spts = sorted((allpts[key(L,c,"singlet",mode)]["disc_weight"], allpts[key(L,c,"singlet",mode)]["E"])
                          for c in (100,200,300,400,600) if key(L,c,"singlet",mode) in allpts)
            tpts = sorted((allpts[key(L,c,"triplet",mode)]["disc_weight"], allpts[key(L,c,"triplet",mode)]["E"])
                          for c in (100,200,300,400,600) if key(L,c,"triplet",mode) in allpts)
            if len(spts) >= 2 and len(tpts) >= 2:
                Es,_ = extrapolate(spts); Et,_ = extrapolate(tpts)
                print(f"  chi->inf: Ds={Et-Es:.6f}  A={(Et-Es)*L:.4f}")
        return
    defect = (a.mode == "defect")
    chis = [64] if a.smoke else [int(c) for c in a.chis.split(",")]
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    print(f"periodic ring · mode={a.mode} · L={L} U={U} · chis={chis}", flush=True)
    for chi in chis:
        for sector in ("singlet", "triplet"):
            k = key(L, chi, sector, a.mode)
            if k in res:
                print(f"  [skip] {k} (cached)", flush=True)
                continue
            r = run_point(L, chi, sector, defect=defect)
            res[k] = r
            json.dump(res, open(OUT, "w"), indent=1)
            print(f"  {k}: E={r['E']:.8f} disc={r['disc_weight']:.2e} "
                  f"sweeps={r['sweeps']} chi_reached={r['max_chi']} ({r['secs']}s)", flush=True)
        # report the running gap after each chi completes both sectors
        ks, kt = key(L, chi, "singlet", a.mode), key(L, chi, "triplet", a.mode)
        if ks in res and kt in res:
            ds = res[kt]["E"] - res[ks]["E"]
            print(f"  == chi={chi}: Ds={ds:.6f}  A=Ds*L={ds*L:.4f}", flush=True)
    # extrapolation over all completed chis
    pts = {}
    for sector in ("singlet", "triplet"):
        pts[sector] = sorted(
            [(res[key(L, c, sector, a.mode)]["disc_weight"], res[key(L, c, sector, a.mode)]["E"])
             for c in chis if key(L, c, sector, a.mode) in res])
    if all(len(v) >= 1 for v in pts.values()):
        Es, how = extrapolate(pts["singlet"]); Et, _ = extrapolate(pts["triplet"])
        ds = Et - Es
        print(f"\n== chi->inf ({how}): Ds={ds:.6f}  A={ds*L:.4f}   "
              f"(physical window [3.07, 3.53]; his chi=100 value was 0.47)", flush=True)
        res[f"_extrapolation_{a.mode}"] = {"L": L, "Ds": ds, "A": ds * L, "method": how}
        json.dump(res, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
