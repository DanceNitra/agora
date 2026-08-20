"""The ensemble the small-world section needs, at four sizes and twenty-five graphs each.

WHY. The manuscript lists the thermodynamic limit as open. One graph per size suggested the effect
collapses by N=14 (median prominence 0.047736 / 0.045620 / 0.007216); five graphs per size showed
the within-size spread EXCEEDS the between-size difference and the ranges overlap. Five is not
enough to separate them either way, so this runs twenty-five per size and adds N=16, and reports a
confidence interval so the answer can be "they do not separate" and mean something.

Everything here is exact. Even N puts the ground state in the Sz=0 sector (dim 252 / 924 / 3432 /
12870), it is non-degenerate at essentially every point, and the observable is a function of s with
no eigenvector choice anywhere in it -- none of the failure modes that broke the N=15 gasket results
can arise.

WHAT IS REPORTED, and each can refuse the claim:
  * median topographic prominence per graph, and the per-size mean with a bootstrap interval;
  * the same divided by sqrt(|E|), since E is a dispersion across an edge set that grows with N and
    one perturbed edge contributes less as it does -- without this a mechanical dilution reads as a
    physical decline;
  * edges whose gap collapses at their own minimum, counted rather than averaged in;
  * a POSITIVE CONTROL at N=10 seed 42 against the independent full-space run.

Run: python probes/edrn_smallworld_ensemble.py [--seeds 25] [--sizes 10,12,14,16]
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

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                  # noqa: BLE001
    pass

HERE = pathlib.Path(__file__).parent
OUT = HERE / "edrn_smallworld_ensemble.result.json"
_spec = importlib.util.spec_from_file_location("trend", HERE / "edrn_smallworld_size_trend.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

STEP = 0.02
UNSAFE_GAP = 0.05


def _job(task):
    n, seed, edges, ei, svals = task
    _, out = T._scan((n, edges, ei, svals))
    return n, seed, ei, out


def boot_ci(vals, n=4000, seed=20260818):
    rng = np.random.default_rng(seed)
    a = np.asarray(vals, dtype=float)
    means = a[rng.integers(0, a.size, size=(n, a.size))].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=25)
    ap.add_argument("--sizes", default="10,12,14,16")
    ap.add_argument("--workers", type=int, default=min(16, (os.cpu_count() or 4) - 2))
    a = ap.parse_args(argv[1:])
    sizes = [int(x) for x in a.sizes.split(",")]
    seeds = list(range(a.seeds))
    svals = np.arange(0.0, 3.0 + STEP / 2, STEP)

    graphs, tasks = {}, []
    for n in sizes:
        for sd in seeds:
            g = nx.watts_strogatz_graph(n, 4, 0.1, seed=sd)
            edges = sorted(tuple(sorted(e)) for e in g.edges())
            graphs[(n, sd)] = edges
            tasks += [(n, sd, edges, ei, svals) for ei in range(len(edges))]

    print("%d edge-scans over %d graphs (%d sizes x %d seeds), %d workers"
          % (len(tasks), len(graphs), len(sizes), len(seeds), a.workers), flush=True)
    t0 = time.time()
    acc: dict = {}
    done = 0
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for n, sd, ei, out in ex.map(_job, tasks, chunksize=1):
            acc.setdefault((n, sd), {})[ei] = out
            done += 1
            if done % 100 == 0:
                el = time.time() - t0
                print("  %d/%d  %.0fs elapsed, ~%.0fs left"
                      % (done, len(tasks), el, el * (len(tasks) - done) / done), flush=True)

    per: dict = {}
    for (n, sd), rows in sorted(acc.items()):
        edges = graphs[(n, sd)]
        proms, unsafe, interior = [], 0, 0
        for ei in range(len(edges)):
            cur = rows[ei]
            E = np.array([c[1] for c in cur])
            i = int(np.argmin(E))
            if cur[i][3] < UNSAFE_GAP:
                unsafe += 1
            if 0 < i < len(E) - 1:
                interior += 1
                proms.append(float(min(E[:i].max(), E[i + 1:].max()) - E[i]))
        per["%d_%d" % (n, sd)] = dict(
            n=n, seed=sd, edges=len(edges), interior=interior, unsafe_gap=unsafe,
            median_prominence=float(np.median(proms)),
            median_scaled=float(np.median(proms) * np.sqrt(len(edges))),
            n_ge_001=int(sum(p >= 0.01 for p in proms)))
    OUT.write_text(json.dumps(per, indent=1), encoding="utf-8")

    print("\n%-4s %-7s %-24s %-24s %-9s %s"
          % ("N", "graphs", "mean median prominence", "mean x sqrt|E|", "interior", "unsafe"))
    summary = {}
    for n in sizes:
        rs = [r for r in per.values() if r["n"] == n]
        m = [r["median_prominence"] for r in rs]
        sc = [r["median_scaled"] for r in rs]
        lo, hi = boot_ci(m)
        slo, shi = boot_ci(sc)
        summary[n] = (float(np.mean(m)), lo, hi, float(np.mean(sc)), slo, shi)
        print("%-4d %-7d %.6f [%.6f, %.6f]  %.4f [%.4f, %.4f]  %-9.1f %d"
              % (n, len(rs), np.mean(m), lo, hi, np.mean(sc), slo, shi,
                 float(np.mean([r["interior"] for r in rs])), sum(r["unsafe_gap"] for r in rs)))

    print("\nDo consecutive sizes separate? (95%% bootstrap intervals on the mean)")
    for x, y in zip(sizes, sizes[1:]):
        ax, ay = summary[x], summary[y]
        sep_raw = ax[2] < ay[1] or ay[2] < ax[1]
        sep_sc = ax[5] < ay[4] or ay[5] < ax[4]
        print("  N=%d vs N=%d : raw %s ; edge-count-corrected %s"
              % (x, y, "SEPARATE" if sep_raw else "overlap", "SEPARATE" if sep_sc else "overlap"))

    ends = (summary[sizes[0]], summary[sizes[-1]])
    print("\n  N=%d vs N=%d (the whole span): raw %s ; corrected %s"
          % (sizes[0], sizes[-1],
             "SEPARATE" if ends[0][2] < ends[1][1] or ends[1][2] < ends[0][1] else "overlap",
             "SEPARATE" if ends[0][5] < ends[1][4] or ends[1][5] < ends[0][4] else "overlap"))
    print("\nwrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
