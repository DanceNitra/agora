"""Is the small gap AT the valley minimum a property of the valley, or of the spectrum?

WHY. The N=10..16 ensemble reports that the share of edges whose Sz=0-sector gap at their own
minimum falls below 0.05 climbs 0.8% -> 2.3% -> 3.4% -> 7.8%, and that reads as a mechanism-level
obstruction to the thermodynamic limit: the observable would have no safe value at exactly the point
being reported. But the threshold is ABSOLUTE while the sector grows 252 -> 12870, so the level
spacing shrinks with N whatever the physics does. A fixed cut on a denser spectrum produces exactly
this shape by itself.

THE CONTROL. Re-run a subsample of the same graphs and, for every edge, record the gap at the
minimum AND the gap at every other point of the same scan. If the at-minimum rate tracks the
background rate, the climb is spectral density and the "obstruction" is an artifact of the cut. If
the at-minimum rate stands well above the background, the association with the reported point is
real and the size trend in it means something.

TWO MORE CONTROLS, both of a kind that has already burned this thread:
  * ARPACK. k=6 with a fixed start vector is what returned an unconverged tree ground space earlier.
    Every point flagged small-gap is re-solved at k=20 and the gap compared.
  * POSITIVE CONTROL. The subsampled graphs are the same (N, seed) rows the ensemble stored, so the
    per-graph median prominence, scaled median, interior count and unsafe count must reproduce
    EXACTLY. If they do not, this probe is measuring something else and nothing below is usable.

Run: python probes/edrn_is_the_vanishing_gap_a_density_artifact.py [--seeds 6] [--sizes 10,12,14,16]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import networkx as nx
import numpy as np
from scipy.sparse.linalg import eigsh

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                  # noqa: BLE001
    pass

HERE = pathlib.Path(__file__).parent
OUT = HERE / "edrn_is_the_vanishing_gap_a_density_artifact.result.json"
ENSEMBLE = HERE / "edrn_smallworld_ensemble.result.json"
_spec = importlib.util.spec_from_file_location("trend", HERE / "edrn_smallworld_size_trend.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

STEP = 0.02                       # identical to the ensemble
UNSAFE = 0.05
CUTS = (0.05, 0.01, 1e-3, 1e-6)
RECHECK_CAP = 12


def _job(task):
    """Re-scan one edge, then re-solve every small-gap point at k=20."""
    n, seed, edges, ei, svals = task
    _, out = T._scan((n, edges, ei, svals))
    E = np.array([c[1] for c in out])
    gaps = np.array([c[3] for c in out])
    i = int(np.argmin(E))
    interior = bool(0 < i < len(E) - 1)
    prom = float(min(E[:i].max(), E[i + 1:].max()) - E[i]) if interior else None

    # --- ARPACK control: re-solve the flagged points with a much larger Krylov space.
    # Capped: the minimum's own point always, plus up to RECHECK_CAP-1 others, chosen by a fixed
    # rule (evenly spaced through the flagged list) so the sample cannot drift between runs.
    z, idx = T.sector(n)
    recheck = []
    flagged = np.nonzero(gaps < UNSAFE)[0]
    if flagged.size > RECHECK_CAP:
        take = set(np.linspace(0, flagged.size - 1, RECHECK_CAP - 1).round().astype(int).tolist())
        keep = [flagged[t] for t in sorted(take)]
        if gaps[i] < UNSAFE and i not in keep:
            keep.append(i)
        flagged = np.array(sorted(set(int(x) for x in keep)))
    for j in flagged:
        coup = [1.0] * len(edges)
        coup[ei] = float(svals[j])
        h = T.hamiltonian(n, edges, coup, z, idx)
        w = np.sort(eigsh(h, k=min(20, idx.size - 2), which="SA", tol=0, maxiter=1000000,
                          return_eigenvectors=False))
        d = int(np.sum(w - w[0] < 1e-8))
        recheck.append((int(j), float(gaps[j]), float(w[d] - w[0]), d))

    return dict(n=n, seed=seed, ei=ei, edge=list(edges[ei]), interior=interior, prominence=prom,
                s_star=float(svals[i]), gap_at_min=float(gaps[i]),
                gap_min_over_scan=float(gaps.min()), gap_median_over_scan=float(np.median(gaps)),
                n_points=int(gaps.size),
                below={str(c): int((gaps < c).sum()) for c in CUTS},
                below_at_min={str(c): bool(gaps[i] < c) for c in CUTS},
                recheck=recheck)


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--sizes", default="10,12,14,16")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    a = ap.parse_args(argv[1:])
    sizes = [int(x) for x in a.sizes.split(",")]
    seeds = list(range(a.seeds))
    svals = np.arange(0.0, 3.0 + STEP / 2, STEP)

    graphs, tasks = {}, []
    for n in sizes:
        for sd in seeds:
            g = nx.watts_strogatz_graph(n, 4, 0.1, seed=sd)
            assert nx.is_connected(g), "disconnected graph (n=%d seed=%d)" % (n, sd)
            edges = sorted(tuple(sorted(e)) for e in g.edges())
            graphs[(n, sd)] = edges
            tasks += [(n, sd, edges, ei, svals) for ei in range(len(edges))]

    print("%d edge-scans over %d graphs, %d workers (all %d graphs connected)"
          % (len(tasks), len(graphs), a.workers, len(graphs)), flush=True)
    t0, done, rows = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(_job, tasks, chunksize=1):
            rows.append(r)
            done += 1
            if done % 25 == 0:
                el = time.time() - t0
                print("  %d/%d  %.0fs elapsed, ~%.0fs left"
                      % (done, len(tasks), el, el * (len(tasks) - done) / done), flush=True)

    OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")

    # ---------- POSITIVE CONTROL against the stored ensemble ----------
    ens = json.loads(ENSEMBLE.read_text(encoding="utf-8"))
    ok = bad = 0
    for (n, sd), edges in sorted(graphs.items()):
        mine = [r for r in rows if r["n"] == n and r["seed"] == sd]
        proms = [r["prominence"] for r in mine if r["interior"]]
        got = dict(interior=len(proms), unsafe_gap=sum(1 for r in mine if r["gap_at_min"] < UNSAFE),
                   median_prominence=float(np.median(proms)),
                   median_scaled=float(np.median(proms) * np.sqrt(len(edges))))
        want = ens["%d_%d" % (n, sd)]
        same = (got["interior"] == want["interior"] and got["unsafe_gap"] == want["unsafe_gap"]
                and abs(got["median_prominence"] - want["median_prominence"]) < 1e-12
                and abs(got["median_scaled"] - want["median_scaled"]) < 1e-12)
        ok += same
        if not same:
            bad += 1
            print("  MISMATCH N=%d seed=%d  mine=%s  stored=%s" % (n, sd, got, want))
    print("\nPOSITIVE CONTROL: %d/%d graphs reproduce the stored ensemble exactly%s"
          % (ok, len(graphs), "" if not bad else "  <-- STOP, %d disagree" % bad))

    # ---------- the control that matters ----------
    print("\nAT THE MINIMUM vs EVERYWHERE ELSE (share of gaps below each cut)")
    print("%-4s %-7s %-8s %s" % ("N", "edges", "points",
                                 "  ".join("%-26s" % ("cut %g" % c) for c in CUTS)))
    summary = {}
    for n in sizes:
        rs = [r for r in rows if r["n"] == n]
        pts = sum(r["n_points"] for r in rs)
        cells, per_cut = [], {}
        for c in CUTS:
            k = str(c)
            at = sum(r["below_at_min"][k] for r in rs)
            allp = sum(r["below"][k] for r in rs)
            # background = every point of the scan except the minimum itself
            bg = allp - at
            r_at, r_bg = at / len(rs), bg / (pts - len(rs))
            per_cut[k] = dict(at_min=at, at_min_rate=r_at, background=bg, background_rate=r_bg,
                              enrichment=(r_at / r_bg) if r_bg else None)
            cells.append("%-26s" % ("%4.1f%% vs %5.2f%% (x%s)"
                                    % (100 * r_at, 100 * r_bg,
                                       "%.1f" % (r_at / r_bg) if r_bg else "inf" if r_at else "-")))
        summary[n] = per_cut
        print("%-4d %-7d %-8d %s" % (n, len(rs), pts, "  ".join(cells)))

    print("\nARPACK CONTROL (every flagged point re-solved at k=20)")
    tot = moved = 0
    worst = 0.0
    for r in rows:
        for _j, g6, g20, _d in r["recheck"]:
            tot += 1
            worst = max(worst, abs(g20 - g6))
            if abs(g20 - g6) > 1e-6:
                moved += 1
    print("  %d flagged points, %d changed by more than 1e-6, largest change %.3e" % (tot, moved, worst))
    still = sum(1 for r in rows for _j, _g6, g20, _d in r["recheck"] if g20 < UNSAFE)
    print("  %d/%d survive the cut at k=20" % (still, tot))

    OUT.write_text(json.dumps(dict(rows=rows, summary={str(k): v for k, v in summary.items()},
                                   arpack=dict(flagged=tot, moved=moved, worst=worst, survive=still)),
                              indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
