"""The control-graph row of the EDRN paper, recomputed on the manifold instead of one eigenvector.

WHY THIS EXISTS. Table 3 of the manuscript reports single-edge scans on three N=15 control graphs
and concludes that the random graph shows no stable valley because its depth varies across seeds,
0.0730 +- 0.0548. Li Guanghao asked for a procedure rather than a judgement, and on 2026-09-09 he
asked us to apply it and decide whether the row survives. The procedure has four steps: name the
magnetisation sector, start every scan point from a fresh random vector, compare the lowest energies
across sectors, and where they agree, average the correlations over the degenerate manifold rather
than over whichever state the solver returned.

A cross-seed spread in the depth is exactly the signature of a degenerate ground manifold read
through a single eigenvector. So the question this answers is whether the instability is in the
graph or in the reading, and the paper cannot say which today: the table names no contradiction
edge, so the published row is not reproducible from the paper alone. Every edge is therefore scanned,
which answers the stronger question of whether ANY edge of these graphs carries a stable valley.

TWO ARMS ON ONE SET OF EIGENVECTORS.
  * as_published: the lowest eigenvector of the S_z = -1/2 sector alone, one state, the reading the
    table's cross-seed spread comes from.
  * manifold: the sectors around it are solved too, the global ground energy is taken across them,
    and the ZZ correlations are averaged over every state within EPS_DEGEN of it. For a degenerate
    manifold an equal-weight average over an orthonormal basis of that manifold IS the normalised
    projector, which is what the paper's own Sec. 6.1 uses for the gasket.

SECTORS. N_up in 6, 7, 8, 9, that is S_z in -3/2, -1/2, +1/2, +3/2 for N=15. The paper's pipeline
fixes N_up=7 and says so nowhere. The four cover the doublet and the quartet, which is the
distinction that matters: an S >= 3/2 multiplet reaches across sectors and a doublet does not.

CONTROLS, because an arm that silently becomes a copy of the other reproduces the published number
for the wrong reason, and we have already been caught by exactly that on Table 2:
  * THE RING AT s=1 MUST GIVE E(1)=0 under the manifold arm. The ring is edge-transitive, so the
    paper's own orbit argument forces it. A non-zero value there means the manifold average is not
    averaging, and nothing else in the run can be believed.
  * THE TWO ARMS MUST DIFFER SOMEWHERE. If every point agrees to machine precision the manifold is
    everywhere trivial or the projection is a no-op.
  * THE MANIFOLD ARM MUST BE SEED-INDEPENDENT and the as_published arm must not be, wherever the
    manifold is degenerate. That is the claim under test, stated as a check that can fail.
  * A NEGATIVE DEPTH IS REPORTED, never dropped. It means the E(0) baseline does not hold for that
    edge, which is how edge (6,11) was handled in Table 2.
"""
import io
import itertools
import json
import multiprocessing as mp
import os
import sys
import time

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import eigsh

try:
    import networkx as nx
except ImportError:                                   # pragma: no cover
    print("CANNOT RUN: networkx is not installed")
    raise SystemExit(2)

N = 15
SECTORS = (6, 7, 8, 9)
PUBLISHED_SECTOR = 7
EPS_DEGEN = 1e-8
N_EIGS = 6
GRID = np.linspace(0.0, 3.0, 61)
SEEDS = (0, 1, 2)
RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"


def graphs():
    ring = [(i, (i + 1) % N) for i in range(N)]
    try:
        tree = sorted(tuple(sorted(e)) for e in nx.random_labeled_tree(N, seed=42).edges())
    except AttributeError:                            # networkx < 3.4
        tree = sorted(tuple(sorted(e)) for e in nx.random_tree(N, seed=42).edges())
    rnd = sorted(tuple(sorted(e)) for e in nx.gnm_random_graph(N, 27, seed=42).edges())
    return {"ring": ring, "tree": tree, "random": rnd}


def build(edges, J_vals, n_up):
    """His Hamiltonian, copied from the archive rather than re-derived."""
    basis = list(itertools.combinations(range(N), n_up))
    index = {st: i for i, st in enumerate(basis)}
    H = lil_matrix((len(basis), len(basis)), dtype=float)
    for (i, j), J in zip(edges, J_vals):
        for idx, st in enumerate(basis):
            si = 1 if i in st else -1
            sj = 1 if j in st else -1
            H[idx, idx] += J * si * sj
        for idx, st in enumerate(basis):
            iu, ju = i in st, j in st
            if iu and not ju:
                ns = list(st); ns.remove(i); ns.append(j)
                H[idx, index[tuple(sorted(ns))]] += 2.0 * J
            elif ju and not iu:
                ns = list(st); ns.remove(j); ns.append(i)
                H[idx, index[tuple(sorted(ns))]] += 2.0 * J
    return csr_matrix(H), basis


def lowest(H, seed):
    rng = np.random.default_rng(seed)
    v0 = rng.standard_normal(H.shape[0])
    vals, vecs = eigsh(H, k=min(N_EIGS, H.shape[0] - 1), which="SA", v0=v0,
                       maxiter=20000, tol=1e-10)
    order = np.argsort(vals)
    return vals[order], vecs[:, order]


def zz(basis, psi, edges):
    w = np.abs(psi) ** 2
    out = np.empty(len(edges))
    for k, (i, j) in enumerate(edges):
        diag = np.fromiter((((1 if i in st else -1) * (1 if j in st else -1)) for st in basis),
                           dtype=float, count=len(basis))
        out[k] = float(np.dot(w, diag))
    return out


def e_of(corr):
    return float(np.std(corr))


def one_point(args):
    """E(s) at one s, both arms, all seeds. A FRESH v0 at every point, never a continuation."""
    edges, e_idx, s, seeds = args
    J = [1.0] * len(edges)
    J[e_idx] = s
    out = {"as_published": {}, "manifold": {}, "degenerate_sectors": None}
    for seed in seeds:
        per_sector = {}
        for n_up in SECTORS:
            H, basis = build(edges, J, n_up)
            vals, vecs = lowest(H, seed + 1000 * n_up)
            per_sector[n_up] = (vals, vecs, basis)
        e0 = min(v[0][0] for v in per_sector.values())
        degen = [n for n, v in per_sector.items() if abs(v[0][0] - e0) < EPS_DEGEN]
        out["degenerate_sectors"] = degen
        vals, vecs, basis = per_sector[PUBLISHED_SECTOR]
        out["as_published"][seed] = e_of(zz(basis, vecs[:, 0], edges))
        acc, n_states = np.zeros(len(edges)), 0
        for n_up in degen:
            vals, vecs, basis = per_sector[n_up]
            for k in range(len(vals)):
                if abs(vals[k] - e0) < EPS_DEGEN:
                    acc += zz(basis, vecs[:, k], edges)
                    n_states += 1
        out["manifold"][seed] = e_of(acc / n_states) if n_states else None
        out["n_states"] = n_states
    return (e_idx, float(s), out)


def scan(edges, e_idx, pool):
    jobs = [(edges, e_idx, float(s), SEEDS) for s in GRID]
    got = pool.map(one_point, jobs)
    got.sort(key=lambda r: r[1])
    curves = {arm: {seed: [r[2][arm][seed] for r in got] for seed in SEEDS}
              for arm in ("as_published", "manifold")}
    n_states = [r[2].get("n_states", 0) for r in got]
    out = {"n_states_min": min(n_states), "n_states_max": max(n_states)}
    for arm in ("as_published", "manifold"):
        pos, dep = [], []
        for seed in SEEDS:
            y = np.array(curves[arm][seed], dtype=float)
            k = int(np.argmin(y))
            pos.append(float(GRID[k]))
            dep.append(float(y[0] - y[k]))
        out[arm] = {"valley_s": pos, "depth": dep,
                    "pos_std": float(np.std(pos)), "depth_mean": float(np.mean(dep)),
                    "depth_std": float(np.std(dep)),
                    "E_at_s1": float(curves[arm][SEEDS[0]][int(np.argmin(np.abs(GRID - 1.0)))])}
    return out


def _rescore(path):
    """Recompute the checks from a completed run, without re-measuring.

    The scan costs 48 minutes and the numbers in it are the measurement. When only the SUMMARY is
    wrong, as it was when a stability test used exact equality against a floating-point spread,
    re-running would burn the machine to re-derive identical arms. This reads them back, rewrites
    the checks, and records that it did so.
    """
    doc = json.load(io.open(path, encoding="utf-8"))
    return doc["results"], doc


def main():
    started = time.time()
    rescore_from = None
    if len(sys.argv) > 1 and sys.argv[1] == "--rescore":
        rescore_from = RESULT
    gs = graphs()
    total = sum(len(v) for v in gs.values())
    done = 0
    results = {}
    if rescore_from:
        results, _prev = _rescore(rescore_from)
        print("rescoring the checks from %s; the arms are not re-measured"
              % os.path.basename(rescore_from), flush=True)
    with mp.Pool(processes=min(12, os.cpu_count() or 4)) as pool:
        for name, edges in ([] if rescore_from else gs.items()):
            results[name] = {}
            for e_idx, e in enumerate(edges):
                results[name][str(tuple(e))] = scan(edges, e_idx, pool)
                done += 1
                print("  %s %s  %d/%d  %.0fs" % (name, tuple(e), done, total,
                                                 time.time() - started), flush=True)

    checks = []

    def check(nm, ok, got):
        checks.append({"check": nm, "pass": bool(ok), "got": got})

    ring_e1 = [v["manifold"]["E_at_s1"] for v in results["ring"].values()]
    check("CONTROL_THE_RING_GIVES_E1_ZERO_ON_THE_MANIFOLD",
          max(abs(x) for x in ring_e1) < 1e-6,
          "largest |E(1)| over the ring's %d edges is %.3e" % (len(ring_e1),
                                                               max(abs(x) for x in ring_e1)))
    diffs = [abs(v["as_published"]["depth_mean"] - v["manifold"]["depth_mean"])
             for g in results.values() for v in g.values()]
    check("CONTROL_THE_TWO_ARMS_DIFFER_SOMEWHERE",
          max(diffs) > 1e-9,
          "largest depth difference between the arms is %.3e over %d edges"
          % (max(diffs), len(diffs)))
    man_spread = max(v["manifold"]["depth_std"] for g in results.values() for v in g.values())
    pub_spread = max(v["as_published"]["depth_std"] for g in results.values() for v in g.values())
    check("THE_MANIFOLD_ARM_IS_SEED_INDEPENDENT",
          man_spread < 1e-6,
          "largest cross-seed depth spread is %.3e on the manifold against %.3e as published"
          % (man_spread, pub_spread))
    check("THE_PUBLISHED_ARM_IS_NOT",
          pub_spread > 1e-6,
          "largest cross-seed depth spread as published is %.3e" % pub_spread)
    neg = [(g, e) for g, rows in results.items() for e, v in rows.items()
           if v["manifold"]["depth_mean"] < 0]
    check("NEGATIVE_DEPTHS_ARE_REPORTED_NOT_DROPPED", True,
          "%d of %d edges have a negative manifold depth: %s"
          % (len(neg), total, neg[:6]))
    published = 0.0730
    close = [(g, e, v["as_published"]["depth_mean"]) for g, rows in results.items()
             for e, v in rows.items() if abs(v["as_published"]["depth_mean"] - published) < 0.005]
    check("CAN_THE_PUBLISHED_RANDOM_GRAPH_DEPTH_BE_LOCATED_AT_ALL",
          True,
          "%d edge(s) reproduce the published 0.0730 within 0.005 as published: %s"
          % (len(close), close[:5]))

    rnd = results["random"]
    # A TOLERANCE, NOT AN EQUALITY. The first version tested pos_std == 0.0 and reported 17 of 27
    # stable edges. Edge (4,9) has valley_s exactly [1.35, 1.35, 1.35] and np.std returns
    # 2.220446049250313e-16 for it, one ulp of two-pass arithmetic. The count was a property of the
    # summariser, not of the graph. It is 18.
    stable = [e for e, v in rnd.items()
              if v["manifold"]["pos_std"] < 1e-12 and v["manifold"]["depth_std"] < 1e-6
              and v["manifold"]["depth_mean"] > 1e-9]
    out = {
        "probe": os.path.basename(__file__),
        "grid": {"s_min": 0.0, "s_max": 3.0, "points": len(GRID)},
        "sectors": list(SECTORS), "published_sector": PUBLISHED_SECTOR, "seeds": list(SEEDS),
        "results": results,
        "random_graph_edges_with_a_stable_positive_manifold_valley": stable,
        "checks": checks,
        "all_passed": all(c["pass"] for c in checks),
        "elapsed_s": round(time.time() - started, 1),
        "rescored": bool(rescore_from),
        "scope": (
            "Three N=15 control graphs, every edge, 61 points over s in [0,3], three Lanczos seeds, "
            "magnetisation sectors N_up in 6, 7, 8, 9. Depth is E(0) minus the scan minimum, the "
            "paper's own definition. The manifold arm averages the ZZ correlations over every state "
            "within 1e-8 of the global ground energy across those sectors. This does not reproduce "
            "the paper's contradiction-edge choice, which the table does not record."),
    }
    with io.open(RESULT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps({"checks": checks, "all_passed": out["all_passed"],
                      "stable_random_edges": stable}, indent=1))
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
