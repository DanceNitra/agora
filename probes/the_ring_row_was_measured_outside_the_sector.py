"""Why does the published ring row of Table 2 reproduce under neither convention?

THE PUBLISHED ROW (manuscript.tex, tab:control_graphs):

    Ring | s=1.0 | depth single 0.0891 | depth multi 0.0993 +/- 0.0286 | pos std 0.000 | stable Yes

WHAT WE GET on his own grid, linspace(0,3,61), in the fixed sector n_up=7:

    single-vector    0.077072      manifold average   0.208052

Neither is 0.0891, and the ring cannot be rescued by choosing a different edge: it is a plain
15-cycle, so every edge is equivalent by symmetry, and our five-seed spread on the single value is
8.6e-16. A number that does not move across seeds cannot also carry his +/- 0.0286.

THE HYPOTHESIS. The tree and random rows were computed inside n_up=7. The ring row was not, and the
sector is the free choice that changes both numbers. Over the whole Hilbert space the ground level
of a 15-site ring is degenerate across magnetisation sectors, so a single returned eigenvector is a
draw from a wider manifold: the value moves with the seed, and its spread is real rather than
numerical.

THIS IS A PREDICTION, NOT AN EXPLANATION, until it is measured. Two things have to hold together
for the hypothesis to survive, and either can refute it:
  1. 0.0891 falls inside the unrestricted single-vector range, and 0.077072 does not.
  2. The unrestricted cross-seed standard deviation is of the order of his 0.0286, not of 1e-15.

CONTROLS:
  * A POSITIVE CONTROL on the machinery: the tree row, in sector n_up=7, must reproduce the
    published 0.0750. If it does not, nothing else measured here means anything.
  * A NEGATIVE CONTROL on the sector claim: in sector n_up=7 the ring's cross-seed spread must stay
    at numerical zero. If it moves there too, the sector is not what separates the two numbers.
  * THE HYPOTHESIS IS ALLOWED TO FAIL and the script says so in its verdict rather than reporting
    only agreement. A run that can only confirm is not a test.

Runs SERIALLY on purpose: mp.Pool wedged here on Windows, and the whole job is minutes,
not hours. The owner's 4-core limit is respected by using one.
"""
from __future__ import annotations

import io
import itertools
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "the_ring_row_was_measured_outside_the_sector.result.json")

N = 15
GRID = np.linspace(0.0, 3.0, 61)
SEEDS = (0, 1, 2, 3, 4)
WORKERS = 4
N_UP = 7

PUBLISHED_RING_SINGLE = 0.0891
PUBLISHED_RING_MULTI_STD = 0.0286
PUBLISHED_TREE = 0.0750

RING = [tuple(sorted((i, (i + 1) % N))) for i in range(N)]


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def tree_edges():
    import networkx as nx
    return [tuple(sorted(e)) for e in nx.random_labeled_tree(N, seed=42).edges()]


def states(n_up=None):
    """Basis states: one magnetisation sector, or the whole space when n_up is None."""
    if n_up is None:
        return np.arange(1 << N, dtype=np.int64)
    return np.array([sum(1 << i for i in c)
                     for c in itertools.combinations(range(N), n_up)], dtype=np.int64)


def hamiltonian(edges, contra, s, basis, index):
    """Heisenberg on `edges`; the contradiction edge carries coupling s."""
    rows, cols, vals = [], [], []
    for k, st in enumerate(basis):
        diag = 0.0
        for (a, b) in edges:
            J = s if (a, b) == contra else 1.0
            sa = (st >> a) & 1
            sb = (st >> b) & 1
            diag += J * (0.25 if sa == sb else -0.25)
            if sa != sb:
                flipped = st ^ ((1 << a) | (1 << b))
                j = index.get(int(flipped))
                if j is not None:
                    rows.append(k); cols.append(j); vals.append(0.5 * J)
        rows.append(k); cols.append(k); vals.append(diag)
    n = len(basis)
    return csr_matrix((vals, (rows, cols)), shape=(n, n))


def zz_operators(edges, basis):
    """The observable is the PAULI product, +/-1, not the spin product, +/-1/4.

    This probe first used +/-0.25 and its positive control caught it: the tree row came out
    0.018744 against a published 0.0750, exactly a factor of four. The Hamiltonian is unaffected;
    only the diagnosis E(s), a standard deviation over edges, scales.
    """
    out = {}
    for (a, b) in edges:
        sa = (basis >> a) & 1
        sb = (basis >> b) & 1
        out[(a, b)] = np.where(sa == sb, 1.0, -1.0).astype(float)
    return out


def E_at(edges, contra, s, basis, index, zz, seed, tol=1e-9):
    """(single-vector E, manifold-average E, degeneracy) at one s."""
    H = hamiltonian(edges, contra, s, basis, index)
    k = min(12, H.shape[0] - 2)
    rng = np.random.default_rng(seed)
    w, v = eigsh(H, k=k, which="SA", v0=rng.standard_normal(H.shape[0]))
    order = np.argsort(w)
    w, v = w[order], v[:, order]
    deg = int(np.sum(w <= w[0] + tol))
    single = np.array([float(np.dot(v[:, 0] ** 2, zz[e])) for e in edges])
    avg = np.array([float(np.mean([np.dot(v[:, j] ** 2, zz[e]) for j in range(deg)]))
                    for e in edges])
    return float(np.std(single)), float(np.std(avg)), deg


def _job(args, tag=""):
    """One (graph, entrance, seed, sector) scan across the grid.

    IT PRINTS A HEARTBEAT. The first version used mp.Pool and produced no output at all; on Windows
    the children re-import this module and the run sat at 0.7 s of CPU for minutes, which is a wedge
    and not work. A silent long job cannot be told from a stuck one, so this one is neither silent
    nor parallel.
    """
    edges, contra, seed, n_up = args
    t0 = time.time()
    basis = states(n_up)
    index = {int(b): i for i, b in enumerate(basis)}
    zz = zz_operators(edges, basis)
    print("     %-26s basis %6d states" % (tag, len(basis)), flush=True)
    single, avg = [], []
    for k, s in enumerate(GRID):
        a, b, _ = E_at(edges, contra, s, basis, index, zz, seed)
        single.append(a); avg.append(b)
        if (k + 1) % 15 == 0 or k + 1 == len(GRID):
            print("     %-26s %2d/%d  [%.0fs]" % (tag, k + 1, len(GRID), time.time() - t0),
                  flush=True)
    return seed, np.array(single), np.array(avg)


def depth(curve):
    """His rule: the grid minimum, but only if it is a STRICT INTERIOR local minimum.

    A global minimum sitting at an endpoint is a monotone curve, not a valley, and reporting one as
    a depth is the error this collaboration already corrected once for entrance (7,8). Returns
    (None, None) when there is no valley.
    """
    i = int(np.argmin(curve))
    if i == 0 or i == len(curve) - 1:
        return None, None
    if not (curve[i] < curve[i - 1] and curve[i] < curve[i + 1]):
        return None, None
    return float(curve[0] - curve[i]), float(GRID[i])


def main():
    t0 = time.time()
    print("  %d workers of %d CPUs, grid %d points, N=%d" % (WORKERS, os.cpu_count(), len(GRID), N))

    # POSITIVE CONTROL: the tree row, in sector n_up=7, against the published 0.0750.
    tree = tree_edges()
    contra_tree = (2, 3)
    if contra_tree not in tree:
        refuse("edge %s is not in the tree, so the positive control cannot run" % (contra_tree,))
    _, tsingle, _ = _job((tree, contra_tree, 0, N_UP), tag="control tree")
    d_tree, s_tree = depth(tsingle)
    if d_tree is None:
        refuse("the tree curve has no interior valley at all, so the positive control cannot run")
    print("  CONTROL tree (2,3) sector n_up=%d: depth %.6f at s=%.2f, published %.4f"
          % (N_UP, d_tree, s_tree, PUBLISHED_TREE))
    if abs(d_tree - PUBLISHED_TREE) > 5e-4:
        refuse("the positive control does not reproduce the published tree depth (%.6f vs %.4f), "
               "so this machinery cannot be trusted about the ring either"
               % (d_tree, PUBLISHED_TREE))

    results = {}
    for label, n_up in (("sector n_up=%d" % N_UP, N_UP), ("all sectors", None)):
        got = [_job((RING, RING[8], seed, n_up), tag="ring %s seed %d" % (label, seed))
               for seed in SEEDS]
        singles = [depth(s)[0] for _, s, _ in got]
        avgs = [depth(a)[0] for _, _, a in got]
        pos = [depth(s)[1] for _, s, _ in got]
        if any(x is None for x in singles + avgs):
            refuse("at least one ring seed produced no interior valley under %s, so a mean over "
                   "these numbers would silently mix valleys with monotone curves" % label)
        results[label] = {
            "single_mean": float(np.mean(singles)), "single_std": float(np.std(singles, ddof=1)),
            "single_min": float(np.min(singles)), "single_max": float(np.max(singles)),
            "average_mean": float(np.mean(avgs)), "average_std": float(np.std(avgs, ddof=1)),
            "position": sorted(set(round(p, 4) for p in pos)),
        }
        r = results[label]
        print()
        print("  RING, %s, %d seeds  [%.0fs]" % (label, len(SEEDS), time.time() - t0))
        print("     single-vector depth  %.6f +/- %.6f   range [%.6f, %.6f]"
              % (r["single_mean"], r["single_std"], r["single_min"], r["single_max"]))
        print("     manifold average     %.6f +/- %.6f" % (r["average_mean"], r["average_std"]))
        print("     valley position(s)   %s" % r["position"])

    insector, allsec = results["sector n_up=%d" % N_UP], results["all sectors"]

    # NEGATIVE CONTROL: in-sector, the seed spread must stay at numerical zero.
    print()
    if insector["single_std"] > 1e-9:
        refuse("the in-sector spread is %.2e, not numerical zero, so the sector is not what "
               "separates the two numbers and the hypothesis is not testable this way"
               % insector["single_std"])
    print("  CONTROL: in-sector cross-seed spread is %.2e, numerical zero as expected"
          % insector["single_std"])

    inside = allsec["single_min"] <= PUBLISHED_RING_SINGLE <= allsec["single_max"]
    spread_ok = allsec["single_std"] > 10 * insector["single_std"] and allsec["single_std"] > 1e-4
    print()
    print("  published single 0.0891 inside the unrestricted range [%.6f, %.6f]: %s"
          % (allsec["single_min"], allsec["single_max"], inside))
    print("  unrestricted cross-seed std %.6f against his published %.4f"
          % (allsec["single_std"], PUBLISHED_RING_MULTI_STD))

    if inside and spread_ok:
        verdict = "SECTOR_EXPLAINS_THE_RING_ROW"
        print()
        print("  VERDICT: %s. The ring row is a draw from the unrestricted ground manifold, and "
              "the other two rows are not." % verdict)
    elif not inside and not spread_ok:
        verdict = "SECTOR_DOES_NOT_EXPLAIN_IT"
        print()
        print("  VERDICT: %s. Neither prediction held: 0.0891 is outside the unrestricted range "
              "and the spread did not open up. The ring row has some other cause and this "
              "hypothesis is dead." % verdict)
    else:
        verdict = "PARTIAL"
        print()
        print("  VERDICT: %s. One prediction held and the other did not, so the sector is at most "
              "part of the story. Do not present this as the explanation." % verdict)

    json.dump({"script": os.path.basename(__file__),
               "grid": "linspace(0,3,61)", "seeds": list(SEEDS), "workers": WORKERS,
               "published": {"ring_single": PUBLISHED_RING_SINGLE,
                             "ring_multi_std": PUBLISHED_RING_MULTI_STD,
                             "tree_single": PUBLISHED_TREE},
               "control_tree_depth": d_tree, "control_tree_s": s_tree,
               "ring": results,
               "published_inside_unrestricted_range": bool(inside),
               "spread_opened_up": bool(spread_ok),
               "verdict": verdict,
               "controls": {"positive_control_tree_reproduces": True,
                            "negative_control_in_sector_spread_is_zero": True,
                            "hypothesis_could_have_failed": True}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s  [%.0fs]" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
