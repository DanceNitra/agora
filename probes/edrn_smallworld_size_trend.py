"""The small-world scan at N = 10, 12, 14, with a stated significance criterion.

This is the part of the EDRN manuscript that survived re-verification, so it is the part worth
extending. Everything here is exact: even N puts the ground state in the Sz=0 sector (dim 252 / 924 /
3432), it is non-degenerate throughout, and the observable is therefore a function of s with no
choice of eigenvector anywhere in it. None of the failure modes that broke the N=15 gasket results
can arise.

WHY A CRITERION. The manuscript reports "19 of 20 edges produce significant valleys" with no
threshold stated, and at N=10 the prominences span 0.000484 to 0.124434 -- a factor of 250. A count
without a criterion is not a measurement. This reports topographic prominence per edge and the count
surviving each threshold, so the number can be quoted with the rule that produced it.

POSITIVE CONTROL: at N=10 this must reproduce edrn_smallworld_exact.py, which worked in the FULL
1024-state space with a different routine. If the two disagree, one of them is wrong and nothing here
is usable.

Run: python probes/edrn_smallworld_size_trend.py
"""
from __future__ import annotations

import json
import os
import pathlib
import time
from concurrent.futures import ProcessPoolExecutor

import networkx as nx
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh

OUT = pathlib.Path(__file__).with_suffix(".result.json")
SIZES = (10, 12, 14)
STEP = 0.01


def z_table(n):
    b = np.arange(1 << n, dtype=np.int64)
    return np.stack([1 - 2 * ((b >> k) & 1) for k in range(n)]).astype(np.int8)


def sector(n):
    z = z_table(n)
    return z, np.nonzero(z.sum(axis=0) == 0)[0]


def hamiltonian(n, edges, coup, z, idx):
    dim = 1 << n
    diag = np.zeros(dim)
    rows, cols, vals = [], [], []
    for (i, j), w in zip(edges, coup):
        if w == 0.0:
            continue
        diag += w * (z[i].astype(np.float64) * z[j])
        anti = np.nonzero(z[i] != z[j])[0]
        rows.append(anti ^ ((1 << i) | (1 << j)))
        cols.append(anti)
        vals.append(np.full(anti.size, 2.0 * w))
    r = np.concatenate(rows + [np.arange(dim)])
    c = np.concatenate(cols + [np.arange(dim)])
    v = np.concatenate(vals + [diag])
    return sp.csr_matrix((v, (r, c)), shape=(dim, dim))[idx][:, idx]


def _scan(task):
    n, edges, ei, svals = task
    z, idx = sector(n)
    zi = z[:, idx].astype(np.float64)
    v0 = np.random.default_rng(20260818).standard_normal(idx.size)
    out = []
    for s in svals:
        coup = [1.0] * len(edges)
        coup[ei] = float(s)
        h = hamiltonian(n, edges, coup, z, idx)
        w, V = eigsh(h, k=6, which="SA", tol=0, maxiter=300000, v0=v0)
        o = np.argsort(w)
        w, V = w[o], V[:, o]
        d = int(np.sum(w - w[0] < 1e-8))
        p = V[:, 0] ** 2
        E = float(np.array([p @ (zi[i] * zi[j]) for i, j in edges]).std())
        out.append((round(float(s), 4), E, d, float(w[d] - w[0])))
    return ei, out


def prominence(E, i):
    if not (0 < i < len(E) - 1):
        return None
    return float(min(E[:i].max(), E[i + 1:].max()) - E[i])


def main():
    workers = min(16, (os.cpu_count() or 4) - 2)
    svals = np.arange(0.0, 3.0 + STEP / 2, STEP)
    report = {}
    t0 = time.time()
    for n in SIZES:
        g = nx.watts_strogatz_graph(n, 4, 0.1, seed=42)
        edges = sorted(tuple(sorted(e)) for e in g.edges())
        tasks = [(n, edges, ei, svals) for ei in range(len(edges))]
        rows = {}
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for ei, r in ex.map(_scan, tasks):
                rows[ei] = r
        per = []
        for ei, e in enumerate(edges):
            cur = rows[ei]
            ss = np.array([c[0] for c in cur])
            E = np.array([c[1] for c in cur])
            dg = sorted({c[2] for c in cur})
            i = int(np.argmin(E))
            per.append(dict(edge=list(e), s_star=float(ss[i]), interior=bool(0 < i < len(E) - 1),
                            prominence=prominence(E, i), gap_at_min=cur[i][3], degeneracies=dg,
                            full_range=float(E.max() - E.min())))
        report[n] = dict(edges=[list(e) for e in edges], per_edge=per,
                         curves={str(k): v for k, v in rows.items()})
        print("N=%d done (%d edges) %.0fs" % (n, len(edges), time.time() - t0), flush=True)

    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")

    # ---- POSITIVE CONTROL against the independent full-space run at N=10
    prev = pathlib.Path(__file__).with_name("edrn_smallworld_exact.result.json")
    ctrl = "not run"
    if prev.exists():
        old = json.loads(prev.read_text())
        oldmin = {}
        for ei, e in enumerate([tuple(x) for x in old["edges"]]):
            cur = old["curves"][str(ei)]
            E = np.array([c[1] for c in cur])
            oldmin[e] = cur[int(np.argmin(E))][0]
        agree = sum(1 for p in report[10]["per_edge"]
                    if abs(p["s_star"] - oldmin[tuple(p["edge"])]) <= 0.011)
        ctrl = "%d/%d edges agree with the independent full-space run" % (agree, len(oldmin))
    print("\nPOSITIVE CONTROL at N=10: %s" % ctrl)

    print("\n%-4s %-7s %-8s %-9s %-11s %s" % ("N", "edges", "interior", "deg", "gap range", "prominence"))
    for n in SIZES:
        per = report[n]["per_edge"]
        pr = [p["prominence"] for p in per if p["prominence"] is not None]
        dg = sorted({d for p in per for d in p["degeneracies"]})
        gaps = [p["gap_at_min"] for p in per]
        print("%-4d %-7d %-8d %-9s %.2f-%.2f   %.6f-%.6f  median %.6f"
              % (n, len(per), sum(1 for p in per if p["interior"]), dg,
                 min(gaps), max(gaps), min(pr), max(pr), float(np.median(pr))))
    print("\nedges surviving a prominence threshold:")
    print("%-4s %-8s %-8s %-8s %s" % ("N", ">=0.005", ">=0.01", ">=0.02", "total"))
    for n in SIZES:
        pr = [p["prominence"] for p in report[n]["per_edge"] if p["prominence"] is not None]
        print("%-4d %-8d %-8d %-8d %d"
              % (n, sum(p >= 0.005 for p in pr), sum(p >= 0.01 for p in pr),
                 sum(p >= 0.02 for p in pr), len(report[n]["per_edge"])))
    print("\nmanuscript claims 19 of 20 significant valleys at N=10, with no threshold stated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
