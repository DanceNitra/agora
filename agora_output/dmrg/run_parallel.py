#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parallel driver for the Hubbard DMRG grid.

The grid is 4 L x 4 chi x 4 sectors = 64 INDEPENDENT DMRG runs. TenPy with
conserved (N, Sz) makes many small tensor blocks, so a single run barely uses
one core (OpenBLAS won't thread small blocks). The efficient use of a 12-core
CPU is PROCESS parallelism: run many cells at once, each capped to a few BLAS
threads, each writing its own cells/<key>.json (no shared-file race).

  python run_parallel.py [--workers 6] [--threads 2] [--Ls 80,160,320]

Ordered ascending by (L, chi) so the smaller L finish first (physics trend);
the heavy L=320 cells fill the pool and complete last. Fully resumable: a cell
whose cells/<key>.json already exists with sector_ok is skipped.
"""
import os, sys, json, time, argparse, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "dmrg_hubbard.py")

LS_DEFAULT = [40, 80, 160, 320]
CHIS = [100, 200, 300, 400]

# U-aware paths (set in main() from --U); U=1.0 keeps the original 'cells' dir.
CELLDIR = os.path.join(HERE, "cells")
SHARED = os.path.join(HERE, "hubbard_dmrg_results.json")
U = 1.0
SECTORS = ["singlet", "Nm1", "Np1", "triplet"]


def cell_key(L, chi, sector):
    return f"L{L}_chi{chi}_{sector}"


def already_done(k):
    # done if a cell file OR the shared JSON has it with sector_ok
    cf = os.path.join(CELLDIR, k + ".json")
    if os.path.exists(cf):
        try:
            d = json.load(open(cf))
            if d.get(k, {}).get("sector_ok"):
                return True
        except Exception:
            pass
    if os.path.exists(SHARED):
        try:
            d = json.load(open(SHARED))
            if d.get(k, {}).get("sector_ok"):
                return True
        except Exception:
            pass
    return False


def run_cell(L, chi, sector, threads):
    k = cell_key(L, chi, sector)
    env = dict(os.environ)
    for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[v] = str(threads)
    t0 = time.time()
    p = subprocess.run(
        [sys.executable, SCRIPT, "--L", str(L), "--chi", str(chi), "--sector", sector,
         "--U", str(U)],
        cwd=HERE, env=env, capture_output=True, text=True,
    )
    dt = time.time() - t0
    ok = os.path.exists(os.path.join(CELLDIR, k + ".json"))
    tail = (p.stdout or "").strip().splitlines()
    tail = tail[-1] if tail else (p.stderr or "").strip().splitlines()[-1:] or ""
    return k, ok, dt, (tail if isinstance(tail, str) else " ".join(tail))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--Ls", type=str, default=None, help="comma list, e.g. 80,160,320")
    ap.add_argument("--U", type=float, default=1.0)
    args = ap.parse_args()

    global CELLDIR, SHARED, U
    U = args.U
    if abs(U - 1.0) > 1e-9:
        CELLDIR = os.path.join(HERE, f"cells_U{U:g}")
        SHARED = os.path.join(HERE, f"hubbard_dmrg_results_U{U:g}.json")

    Ls = [int(x) for x in args.Ls.split(",")] if args.Ls else LS_DEFAULT
    cells = [(L, chi, s) for L in Ls for chi in CHIS for s in SECTORS]
    cells.sort(key=lambda c: (c[0], c[1]))   # ascending L, then chi
    todo = [c for c in cells if not already_done(cell_key(*c))]
    done0 = len(cells) - len(todo)
    print(f"grid={len(cells)} cells | already done={done0} | to run={len(todo)} "
          f"| workers={args.workers} x {args.threads} threads", flush=True)

    n_ok = 0
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_cell, L, chi, s, args.threads): (L, chi, s) for (L, chi, s) in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            k, ok, dt, tail = fut.result()
            n_ok += int(ok)
            elapsed = time.time() - t_start
            print(f"[{i}/{len(todo)}] {'OK ' if ok else 'FAIL'} {k}  {dt/60:.1f}min "
                  f"| elapsed {elapsed/60:.1f}min | {tail[:90]}", flush=True)

    # merge all cells into the shared JSON + analyze
    print("merging cells + analyzing ...", flush=True)
    subprocess.run([sys.executable, SCRIPT, "--analyze-only"], cwd=HERE)
    print(f"DONE: {n_ok}/{len(todo)} new cells ok, total elapsed {(time.time()-t_start)/60:.1f}min", flush=True)


if __name__ == "__main__":
    main()
