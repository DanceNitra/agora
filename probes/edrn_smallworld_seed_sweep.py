"""Is the collapse of the valley with N a SIZE effect, or graph-to-graph variation?

Measured first at one seed: the median prominence runs 0.047736 (N=10), 0.045620 (N=12), 0.007216
(N=14) -- a 6.3x drop at the last step. That would matter a great deal to the manuscript, whose
thermodynamic limit is listed as an open problem.

But WS(10,4,0.1,42), WS(12,4,0.1,42) and WS(14,4,0.1,42) are three DIFFERENT graphs, not a nested
family: at p=0.1 each realisation rewires differently. A single seed cannot tell "the effect shrinks
with size" from "this particular N=14 graph happens to be flat". Five seeds per size can.

Two confounds handled explicitly:
  * edge count grows with N (2N), and E is a standard deviation across edges, so one perturbed edge
    contributes less as the count rises. Prominence x sqrt(|E|) is reported alongside, which removes
    that scaling.
  * an edge whose gap collapses at its minimum has no safe value there; those are counted, not
    silently averaged in. One appeared at N=14 (edge (6,8), gap 3.0e-04).

Run: python probes/edrn_smallworld_seed_sweep.py
"""
from __future__ import annotations

import json
import os
import pathlib
import time
from concurrent.futures import ProcessPoolExecutor

import networkx as nx
import numpy as np

OUT = pathlib.Path(__file__).with_suffix(".result.json")
SIZES = (10, 12, 14)
SEEDS = (42, 1, 2, 3, 4)
STEP = 0.02

_mod = pathlib.Path(__file__).with_name("edrn_smallworld_size_trend.py")
import importlib.util
_spec = importlib.util.spec_from_file_location("trend", _mod)
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)


def _job(task):
    n, seed, edges, ei, svals = task
    _, out = T._scan((n, edges, ei, svals))
    return n, seed, ei, out


def main():
    workers = min(16, (os.cpu_count() or 4) - 2)
    svals = np.arange(0.0, 3.0 + STEP / 2, STEP)
    tasks = []
    graphs = {}
    for n in SIZES:
        for sd in SEEDS:
            g = nx.watts_strogatz_graph(n, 4, 0.1, seed=sd)
            edges = sorted(tuple(sorted(e)) for e in g.edges())
            graphs[(n, sd)] = edges
            tasks += [(n, sd, edges, ei, svals) for ei in range(len(edges))]

    print("%d edge-scans across %d graphs, %d workers" % (len(tasks), len(graphs), workers), flush=True)
    t0 = time.time()
    acc: dict = {}
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for n, sd, ei, out in ex.map(_job, tasks, chunksize=2):
            acc.setdefault((n, sd), {})[ei] = out
            done += 1
            if done % 50 == 0:
                print("  %d/%d  %.0fs" % (done, len(tasks), time.time() - t0), flush=True)

    report: dict = {}
    for (n, sd), rows in sorted(acc.items()):
        edges = graphs[(n, sd)]
        proms, unsafe, interior = [], 0, 0
        for ei in range(len(edges)):
            cur = rows[ei]
            E = np.array([c[1] for c in cur])
            i = int(np.argmin(E))
            if cur[i][3] < 0.05:
                unsafe += 1
            if 0 < i < len(E) - 1:
                interior += 1
                proms.append(float(min(E[:i].max(), E[i + 1:].max()) - E[i]))
        report["%d_%d" % (n, sd)] = dict(
            n=n, seed=sd, edges=len(edges), interior=interior, unsafe_gap=unsafe,
            median_prominence=float(np.median(proms)), max_prominence=float(max(proms)),
            n_ge_001=int(sum(p >= 0.01 for p in proms)),
            median_scaled=float(np.median(proms) * np.sqrt(len(edges))))
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")

    print("\n%-4s %-6s %-7s %-9s %-11s %-13s %-9s %s"
          % ("N", "seed", "edges", "interior", "median prom", "median*sqrt|E|", ">=0.01", "unsafe gap"))
    for k in sorted(report, key=lambda x: (report[x]["n"], report[x]["seed"])):
        r = report[k]
        print("%-4d %-6d %-7d %-9d %-11.6f %-13.4f %-9d %d"
              % (r["n"], r["seed"], r["edges"], r["interior"], r["median_prominence"],
                 r["median_scaled"], r["n_ge_001"], r["unsafe_gap"]))
    print("\nper size, across %d seeds:" % len(SEEDS))
    print("%-4s %-24s %-24s %s" % ("N", "median prominence", "median x sqrt|E|", "edges >=0.01 (of total)"))
    for n in SIZES:
        rs = [r for r in report.values() if r["n"] == n]
        m = [r["median_prominence"] for r in rs]
        sc = [r["median_scaled"] for r in rs]
        c = [r["n_ge_001"] for r in rs]
        print("%-4d %.6f  [%.6f, %.6f]  %.4f  [%.4f, %.4f]  %.1f of %d"
              % (n, float(np.mean(m)), min(m), max(m), float(np.mean(sc)), min(sc), max(sc),
                 float(np.mean(c)), rs[0]["edges"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
