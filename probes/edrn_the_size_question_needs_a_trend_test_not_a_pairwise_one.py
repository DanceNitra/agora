"""The size question, asked with a test that can answer it -- and with the per-edge data kept.

WHY THIS REPLACES THE FIRST ENSEMBLE. `edrn_smallworld_ensemble.py` ran 25 graphs per size at
N = 10, 12, 14, 16 and asked whether consecutive per-size means separate under bootstrap intervals.
None did, and it concluded there was no resolvable decline. That test is the weak one: comparing two
intervals for overlap throws away every graph at the other two sizes, and "the intervals overlap" is
not "there is no trend". Fitting log(median prominence) against N across ALL the graphs at once, with
the bootstrap resampling graphs, uses the whole ensemble -- and on the very same 100 graphs it gives
a slope whose interval EXCLUDES zero. The first conclusion was an artifact of the test, not a
property of the data.

It also stored only per-graph aggregates, so two questions could not be asked afterwards at all:
whether a per-edge criterion behaves like the median, and whether a decline survives being scaled by
the growing edge count. This keeps every edge.

WHAT IS REPORTED, and each can refuse the claim:
  * per-graph median topographic prominence, raw and divided by sqrt(|E|) -- the observable is a
    dispersion across an edge set that grows as 2N, so one perturbed edge contributes less as N
    rises, and without that correction a mechanical dilution reads as a physical decline;
  * the trend in each across all four sizes, bootstrap over GRAPHS, slope interval vs zero;
  * the manuscript's own criterion -- the share of edges whose valley clears a threshold -- under a
    FIXED threshold (0.01) and under one scaled the same way (0.01 at N=10, x sqrt(20/|E|)), because
    a fixed cut on a diluted quantity declines by construction;
  * the share of edges whose sector gap at their own minimum is below 0.05, counted not averaged;
  * POSITIVE CONTROL: seeds 0..24 must reproduce the stored ensemble's per-graph rows EXACTLY.

Run: python probes/edrn_the_size_question_needs_a_trend_test_not_a_pairwise_one.py [--seeds 50]
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
OUT = HERE / "edrn_the_size_question_needs_a_trend_test_not_a_pairwise_one.result.json"
ENSEMBLE = HERE / "edrn_smallworld_ensemble.result.json"
_spec = importlib.util.spec_from_file_location("trend", HERE / "edrn_smallworld_size_trend.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

STEP = 0.02                    # identical to the first ensemble, so the two are comparable
UNSAFE = 0.05
THRESH = 0.01                  # the manuscript-style significance cut, at N=10
BASE_E = 20                    # |E| at N=10, the size the cut is calibrated on


def _corr_vector(n, edges, ei, s, z, idx, zi, v0):
    """The per-edge <sz sz> vector at one s -- the thing whose dispersion IS the observable."""
    from scipy.sparse.linalg import eigsh
    coup = [1.0] * len(edges)
    coup[ei] = float(s)
    h = T.hamiltonian(n, edges, coup, z, idx)
    w, V = eigsh(h, k=6, which="SA", tol=0, maxiter=300000, v0=v0)
    p = V[:, int(np.argmin(w))] ** 2
    return np.array([p @ (zi[a] * zi[b]) for a, b in edges])


def _share(c, ei):
    """Fraction of the observable's variance carried by the perturbed edge alone.

    If the valley is one edge moving away from an otherwise unchanged set, this is large and the
    observable is diluted as 1/sqrt(|E|) by construction. If the valley is a collective
    reorganisation, it is not.
    """
    d = (c - c.mean()) ** 2
    tot = float(d.sum())
    return float(d[ei] / tot) if tot > 0 else None


def _job(task):
    n, seed, edges, ei, svals = task
    _, out = T._scan((n, edges, ei, svals))
    E = np.array([c[1] for c in out])
    gaps = np.array([c[3] for c in out])
    i = int(np.argmin(E))
    interior = bool(0 < i < len(E) - 1)

    shares = {}
    if interior:
        z, idx = T.sector(n)
        zi = z[:, idx].astype(np.float64)
        v0 = np.random.default_rng(20260818).standard_normal(idx.size)      # same start as T._scan
        li = int(np.argmax(E[:i]))
        ri = i + 1 + int(np.argmax(E[i + 1:]))
        for label, j in (("min", i), ("left_max", li), ("right_max", ri)):
            shares[label] = _share(_corr_vector(n, edges, ei, svals[j], z, idx, zi, v0), ei)

    return dict(n=n, seed=seed, ei=ei, edge=list(edges[ei]), interior=interior,
                prominence=(float(min(E[:i].max(), E[i + 1:].max()) - E[i]) if interior else None),
                s_star=float(svals[i]), gap_at_min=float(gaps[i]),
                degeneracy_at_min=int(out[i][2]), full_range=float(E.max() - E.min()),
                perturbed_edge_variance_share=shares)


def cluster_boot_slope(x, y, n=20000, seed=5):
    """Slope of y on x, with the bootstrap resampling the unit of independence: the GRAPH."""
    rng = np.random.default_rng(seed)
    b0 = float(np.polyfit(x, y, 1)[0])
    bs = np.empty(n)
    for t in range(n):
        i = rng.integers(0, x.size, size=x.size)
        while np.unique(x[i]).size < 2:                  # a resample with one size cannot give a slope
            i = rng.integers(0, x.size, size=x.size)
        bs[t] = np.polyfit(x[i], y[i], 1)[0]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return b0, float(lo), float(hi), bool(hi < 0 or lo > 0)


def boot_mean_ci(vals, n=20000, seed=20260819):
    rng = np.random.default_rng(seed)
    a = np.asarray(vals, dtype=float)
    m = a[rng.integers(0, a.size, size=(n, a.size))].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--sizes", default="10,12,14,16")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    a = ap.parse_args(argv[1:])
    sizes = [int(x) for x in a.sizes.split(",")]
    svals = np.arange(0.0, 3.0 + STEP / 2, STEP)

    graphs, tasks = {}, []
    for n in sizes:
        for sd in range(a.seeds):
            g = nx.watts_strogatz_graph(n, 4, 0.1, seed=sd)
            assert nx.is_connected(g), "disconnected graph (n=%d seed=%d)" % (n, sd)
            edges = sorted(tuple(sorted(e)) for e in g.edges())
            graphs[(n, sd)] = edges
            tasks += [(n, sd, edges, ei, svals) for ei in range(len(edges))]

    print("%d edge-scans over %d graphs (%d sizes x %d seeds), %d workers, all connected"
          % (len(tasks), len(graphs), len(sizes), a.seeds, a.workers), flush=True)
    t0, done, rows = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(_job, tasks, chunksize=1):
            rows.append(r)
            done += 1
            if done % 100 == 0:
                el = time.time() - t0
                print("  %d/%d  %.0fs elapsed, ~%.0fs left"
                      % (done, len(tasks), el, el * (len(tasks) - done) / done), flush=True)

    # ---------- per-graph aggregates ----------
    per = {}
    for (n, sd), edges in sorted(graphs.items()):
        mine = [r for r in rows if r["n"] == n and r["seed"] == sd]
        pr = [r["prominence"] for r in mine if r["interior"]]
        sq = np.sqrt(len(edges))
        scaled = [p * sq for p in pr]
        per["%d_%d" % (n, sd)] = dict(
            n=n, seed=sd, edges=len(edges), interior=len(pr),
            unsafe_gap=sum(1 for r in mine if r["gap_at_min"] < UNSAFE),
            median_prominence=float(np.median(pr)), median_scaled=float(np.median(pr) * sq),
            n_ge_abs=int(sum(p >= THRESH for p in pr)),
            n_ge_scaled=int(sum(v >= THRESH * np.sqrt(BASE_E) for v in scaled)))

    OUT.write_text(json.dumps(dict(per_graph=per, per_edge=rows), indent=1), encoding="utf-8")

    # ---------- POSITIVE CONTROL against the stored 25-seed ensemble ----------
    old = json.loads(ENSEMBLE.read_text(encoding="utf-8"))
    ok = miss = bad = 0
    for k, want in old.items():
        got = per.get(k)
        if got is None:
            miss += 1
            continue
        same = (got["interior"] == want["interior"] and got["unsafe_gap"] == want["unsafe_gap"]
                and abs(got["median_prominence"] - want["median_prominence"]) < 1e-12
                and abs(got["median_scaled"] - want["median_scaled"]) < 1e-12)
        ok += same
        bad += not same
        if not same:
            print("  MISMATCH %s  now=%s  stored=%s" % (k, got, want))
    print("\nPOSITIVE CONTROL vs the stored 25-seed ensemble: %d reproduce exactly, %d disagree, "
          "%d not covered%s" % (ok, bad, miss, "" if not bad else "   <-- STOP"))

    # ---------- per size ----------
    print("\n%-4s %-7s %-26s %-24s %-9s %s"
          % ("N", "graphs", "mean median prominence", "mean x sqrt|E|", "interior", "gap<0.05"))
    summary = {}
    for n in sizes:
        rs = [r for r in per.values() if r["n"] == n]
        m = [r["median_prominence"] for r in rs]
        sc = [r["median_scaled"] for r in rs]
        lo, hi = boot_mean_ci(m)
        slo, shi = boot_mean_ci(sc)
        et = sum(r["edges"] for r in rs)
        ue = sum(r["unsafe_gap"] for r in rs)
        summary[n] = dict(mean=float(np.mean(m)), lo=lo, hi=hi, mean_scaled=float(np.mean(sc)),
                          slo=slo, shi=shi, edges=et, unsafe=ue,
                          interior=float(np.mean([r["interior"] for r in rs])),
                          share_abs=sum(r["n_ge_abs"] for r in rs) / sum(r["interior"] for r in rs),
                          share_scaled=sum(r["n_ge_scaled"] for r in rs) / sum(r["interior"] for r in rs))
        print("%-4d %-7d %.6f [%.6f, %.6f]  %.4f [%.4f, %.4f]  %-9.1f %d/%d = %.1f%%"
              % (n, len(rs), np.mean(m), lo, hi, np.mean(sc), slo, shi,
                 summary[n]["interior"], ue, et, 100 * ue / et))

    print("\nTHE PAIRWISE TEST (what the first ensemble asked)")
    for x, y in list(zip(sizes, sizes[1:])) + [(sizes[0], sizes[-1])]:
        ax, ay = summary[x], summary[y]
        print("  N=%d vs N=%d : raw %s ; edge-count-corrected %s"
              % (x, y, "SEPARATE" if (ax["hi"] < ay["lo"] or ay["hi"] < ax["lo"]) else "overlap",
                 "SEPARATE" if (ax["shi"] < ay["slo"] or ay["shi"] < ax["slo"]) else "overlap"))

    # ---------- the trend test ----------
    N = np.array([r["n"] for r in per.values()], dtype=float)
    P = np.array([r["median_prominence"] for r in per.values()], dtype=float)
    S = np.array([r["median_scaled"] for r in per.values()], dtype=float)
    A = np.array([r["n_ge_abs"] / r["interior"] for r in per.values()], dtype=float)
    C = np.array([r["n_ge_scaled"] / r["interior"] for r in per.values()], dtype=float)
    U = np.array([r["unsafe_gap"] / r["edges"] for r in per.values()], dtype=float)
    span = float(sizes[-1] - sizes[0])

    print("\nTHE TREND TEST (every graph used at once; the bootstrap resamples graphs)")
    trends = {}
    for label, y, logspace in (("log median prominence", np.log(P), True),
                               ("log median x sqrt|E|", np.log(S), True),
                               ("share >= %.2f  (fixed cut)" % THRESH, A, False),
                               ("share >= cut x sqrt(20/|E|)", C, False),
                               ("share gap<0.05 at minimum", U, False)):
        b, lo, hi, excl = cluster_boot_slope(N, y)
        extra = ("  -> x%.3f over N=%d..%d" % (np.exp(span * b), sizes[0], sizes[-1])) if logspace \
            else ("  -> %+.1f pp over N=%d..%d" % (100 * span * b, sizes[0], sizes[-1]))
        trends[label] = dict(slope=b, lo=lo, hi=hi, excludes_zero=excl)
        print("  %-30s %+.5f per spin  [%+.5f, %+.5f]  %-12s%s"
              % (label, b, lo, hi, "EXCLUDES 0" if excl else "includes 0", extra))

    # ---------- is the decline dilution? the perturbed edge's share of the variance ----------
    print("\nWHERE THE OBSERVABLE'S VARIANCE SITS AT THE VALLEY (share carried by the scanned edge)")
    print("%-4s %-8s %-22s %-22s %s" % ("N", "edges", "at the minimum", "at the flanking maxima",
                                        "1/|E| (a flat set)"))
    shares = {}
    for n in sizes:
        rs = [r for r in rows if r["n"] == n and r["interior"] and r["perturbed_edge_variance_share"]]
        at = np.array([r["perturbed_edge_variance_share"]["min"] for r in rs
                       if r["perturbed_edge_variance_share"]["min"] is not None])
        fl = np.array([v for r in rs for k2 in ("left_max", "right_max")
                       for v in [r["perturbed_edge_variance_share"][k2]] if v is not None])
        ed = 2 * n
        shares[n] = dict(at_min_mean=float(at.mean()), at_min_median=float(np.median(at)),
                         flank_mean=float(fl.mean()), n=len(rs), uniform=1.0 / ed)
        print("%-4d %-8d mean %.3f  med %.3f   mean %.3f            %.3f"
              % (n, len(rs), at.mean(), np.median(at), fl.mean(), 1.0 / ed))

    OUT.write_text(json.dumps(dict(per_graph=per, per_edge=rows,
                                   summary={str(k): v for k, v in summary.items()},
                                   trends=trends, variance_share={str(k): v for k, v in shares.items()},
                                   control=dict(reproduced=ok, disagreed=bad, uncovered=miss)),
                              indent=1), encoding="utf-8")
    print("\nwrote %s  (%.0fs total)" % (OUT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
