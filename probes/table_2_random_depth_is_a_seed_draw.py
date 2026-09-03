"""Is Table 2's random-graph depth of 0.1050 a property of the graph, or of one Lanczos start vector?

WHY. Fixing the magnetisation sector to his `N_up = 7` moves our regenerated depth for random edge
(8,14) from 0.010163 to 0.086453 and lands the position on his s = 1.20 exactly, but it does not
reach his 0.104966. The sector is most of the difference and not all of it, so reporting "Table 2
does not reproduce" would be reporting a residual we have not identified.

THE REMAINING SUSPECT, again taken from his script rather than guessed. `compute_enhanced_diagnostic`
calls `eigsh(H, k=1, which='SA', v0=rng.standard_normal(dim))`. When the ground level of that sector
is degenerate, the returned vector depends on the start vector, so the whole E(s) curve is a
function of the seed. His Table 2 value is the seed-0 scan; his own multi-seed audit over seeds 0, 1
and 2 reports 0.073017 +/- 0.054799, a spread of the same order as the number itself.

THE TEST. Run HIS pipeline, his Hamiltonian and his eigsh call, over his grid, for twelve seeds.
If seed 0 returns 0.104966 and the first three return his published mean and spread, then Table 2's
random depth is one draw from a distribution his own audit already measured, and nothing about the
graph is in dispute.

CONTROLS, each able to fail:
  * A POSITIVE CONTROL THAT MUST NOT SCATTER. Tree edge (1,10) is run through the identical code for
    the same twelve seeds. Every source agrees on 0.058909125 there, so if the tree scatters too,
    the instrument is unstable and no conclusion about the random graph survives.
  * THE TWO HAMILTONIANS ARE CHECKED AGAINST EACH OTHER. His convention is sigma-based, ours is
    spin-based, so his spectrum must be exactly four times ours. A mismatch means one of the two
    implementations is wrong and the comparison is void.
  * HIS PUBLISHED PAIR IS THE TARGET, NOT A SHAPE. The probe asks for 0.104966 at seed 0 AND for
    the multi-seed mean and standard deviation over seeds 0 to 2. Matching one of the three would
    be easy; matching all three is the reproduction.
  * THE DEGENERACY IS REPORTED, so a scatter has a stated mechanism rather than an inferred one.
  * A NULL THAT CAN FIRE. If the twelve seeds all agree on the random edge, the seed does not
    explain the residual and the probe says so.
"""
from __future__ import annotations

import io
import itertools
import json
import multiprocessing as mp
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PIPELINE = os.path.join(ROOT, "agora_output", "edrn_submission")
sys.path.insert(0, PIPELINE)
OUT = os.path.join(HERE, "table_2_random_depth_is_a_seed_draw.result.json")

WORKERS = 4
N = 15
N_UP = 7                       # his `N_up = 7`
GRID = (0.0, 3.0, 61)          # his `np.linspace(0.0, 3.0, 61)`
SEEDS = list(range(12))        # his scan uses seed 0; his multi-seed audit uses 0, 1, 2
HIS = {"seed0_depth": 0.104966, "seed0_s": 1.20,
       "multi_mean": 0.073017, "multi_std": 0.054799, "multi_seeds": 3}
CAL = {"edge": (1, 10), "expected": 0.058909125, "tol": 5e-6}
TARGET = (8, 14)


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def his_basis(n, n_up):
    return list(itertools.combinations(range(n), n_up))


def his_H(n, edges, J_vals, basis):
    """His `build_hamiltonian_sector`, transcribed: sigma-z diagonal, 2J hopping."""
    from scipy.sparse import lil_matrix, csr_matrix
    idx = {st: i for i, st in enumerate(basis)}
    H = lil_matrix((len(basis), len(basis)), dtype=float)
    for (i, j), J in zip(edges, J_vals):
        for k, state in enumerate(basis):
            si = 1 if i in state else -1
            sj = 1 if j in state else -1
            H[k, k] += J * si * sj
        for k, state in enumerate(basis):
            i_up, j_up = i in state, j in state
            if i_up and not j_up:
                ns = tuple(sorted([x for x in state if x != i] + [j]))
                H[k, idx[ns]] += 2 * J
            elif j_up and not i_up:
                ns = tuple(sorted([x for x in state if x != j] + [i]))
                H[k, idx[ns]] += 2 * J
    return csr_matrix(H)


def his_diagnostic(edges, J_vals, basis, seed):
    """His `compute_enhanced_diagnostic`: one seeded Lanczos vector, std of zz over all edges."""
    import numpy as np
    from scipy.sparse.linalg import eigsh
    H = his_H(N, edges, J_vals, basis)
    rng = np.random.default_rng(seed)
    v0 = rng.standard_normal(H.shape[0])
    _w, evecs = eigsh(H, k=1, which="SA", v0=v0)
    psi = evecs[:, 0]
    p = np.abs(psi) ** 2
    corrs = []
    for (i, j) in edges:
        sp = np.array([(1 if i in st else -1) * (1 if j in st else -1) for st in basis])
        corrs.append(float(np.sum(p * sp)))
    return float(np.std(np.array(corrs)))


def his_detect_valley(s_values, E):
    i = min(range(len(E)), key=lambda k: E[k])
    if i == 0 or i == len(E) - 1:
        return {"s": None, "depth": None}
    if E[i] < E[i - 1] and E[i] < E[i + 1]:
        return {"s": float(s_values[i]), "depth": float(E[0] - E[i])}
    return {"s": None, "depth": None}


def _one(args):
    import numpy as np
    import networkx as nx
    which, contra, seed = args
    if which == "tree":
        edges = [tuple(sorted(e)) for e in nx.random_labeled_tree(15, seed=42).edges()]
    else:
        edges = [tuple(sorted(e)) for e in nx.gnm_random_graph(15, 27, seed=42).edges()]
    basis = his_basis(N, N_UP)
    grid = np.linspace(*GRID)
    ei = edges.index(contra) if contra in edges else edges.index(tuple(reversed(contra)))
    E = []
    for s in grid:
        J = np.ones(len(edges))
        J[ei] = s
        E.append(his_diagnostic(edges, J, basis, seed))
    return {"graph": which, "edge": list(contra), "seed": seed,
            "valley": his_detect_valley(grid, E)}


def degeneracy_at(contra, s, tol=1e-9):
    """How many states share the ground energy of sector N_UP at this s."""
    import numpy as np
    import networkx as nx
    from scipy.sparse.linalg import eigsh
    edges = [tuple(sorted(e)) for e in nx.gnm_random_graph(15, 27, seed=42).edges()]
    ei = edges.index(contra)
    J = np.ones(len(edges))
    J[ei] = s
    basis = his_basis(N, N_UP)
    H = his_H(N, edges, J, basis)
    w = np.sort(eigsh(H, k=8, which="SA", return_eigenvectors=False))
    return int(sum(1 for x in w if abs(x - w[0]) < tol)), [float(x) for x in w[:4]]


def check_conventions():
    """His sigma-based H must be exactly four times our spin-based H, or one of them is wrong."""
    import numpy as np
    import networkx as nx
    from scipy.sparse.linalg import eigsh
    from regenerate_edge_8_14 import build_H, sector_basis
    edges = [tuple(sorted(e)) for e in nx.gnm_random_graph(15, 27, seed=42).edges()]
    J = np.ones(len(edges))
    J[edges.index(TARGET)] = 1.2
    hb, ob = his_basis(N, N_UP), sector_basis(N, N_UP)
    wh = np.sort(eigsh(his_H(N, edges, J, hb), k=4, which="SA", return_eigenvectors=False))
    wo = np.sort(eigsh(build_H(edges, TARGET, 1.2, ob), k=4, which="SA", return_eigenvectors=False))
    ratio = [float(a / b) for a, b in zip(wh, wo)]
    if max(abs(r - 4.0) for r in ratio) > 1e-6:
        refuse("his Hamiltonian is not four times ours; the ratios are %r, so one implementation "
               "is wrong and this comparison means nothing" % ratio)
    return ratio


def main():
    import numpy as np
    print("  parallelism: %d workers of %d logical CPUs; %d scans of %d points"
          % (WORKERS, os.cpu_count(), 2 * len(SEEDS), GRID[2]))

    ratio = check_conventions()
    print("  convention control: his spectrum / ours = %s" % ["%.6f" % r for r in ratio])

    deg, levels = degeneracy_at(TARGET, HIS["seed0_s"])
    print("  sector n_up=%d at s=%.2f on edge %s: ground degeneracy %d, lowest levels %s"
          % (N_UP, HIS["seed0_s"], TARGET, deg, ["%.6f" % x for x in levels]))

    jobs = ([("tree", CAL["edge"], sd) for sd in SEEDS]
            + [("random", TARGET, sd) for sd in SEEDS])
    t0 = time.time()
    with mp.Pool(WORKERS) as pool:
        rows = pool.map(_one, jobs)
    print("  %d scans in %.0fs" % (len(rows), time.time() - t0))

    tree = {r["seed"]: r["valley"] for r in rows if r["graph"] == "tree"}
    rand = {r["seed"]: r["valley"] for r in rows if r["graph"] == "random"}

    print()
    print("  seed |    tree (1,10)      |  random (8,14)")
    for sd in SEEDS:
        t, r = tree[sd], rand[sd]
        print("   %2d  |  %s at s=%s  |  %s at s=%s"
              % (sd,
                 ("%.9f" % t["depth"]) if t["depth"] is not None else "    none     ", t["s"],
                 ("%.6f" % r["depth"]) if r["depth"] is not None else "  none  ", r["s"]))

    # CONTROL: the tree must not scatter, or the instrument is the story.
    td = [v["depth"] for v in tree.values() if v["depth"] is not None]
    if len(td) != len(SEEDS):
        refuse("the tree control lost %d of %d seeds to a missing valley, so the control is not "
               "clean" % (len(SEEDS) - len(td), len(SEEDS)))
    tree_spread = max(td) - min(td)
    if tree_spread > CAL["tol"]:
        refuse("the tree control scatters by %.2e across seeds, so the seed moves everything and "
               "the random result says nothing specific" % tree_spread)
    if abs(td[0] - CAL["expected"]) > CAL["tol"]:
        refuse("the tree control gives %.9f against the agreed %.9f, so this is not his pipeline"
               % (td[0], CAL["expected"]))
    print()
    print("  POSITIVE CONTROL: tree (1,10) is %.9f for all %d seeds, spread %.2e"
          % (td[0], len(td), tree_spread))

    rd = [v["depth"] for v in rand.values() if v["depth"] is not None]
    seed0 = rand[0]["depth"]
    first3 = [rand[s]["depth"] for s in (0, 1, 2) if rand[s]["depth"] is not None]
    mean3 = float(np.mean(first3)) if first3 else None
    std3 = float(np.std(first3, ddof=1)) if len(first3) > 1 else None

    hit_seed0 = seed0 is not None and abs(seed0 - HIS["seed0_depth"]) < 5e-5
    hit_mean = mean3 is not None and abs(mean3 - HIS["multi_mean"]) < 5e-5
    hit_std = std3 is not None and abs(std3 - HIS["multi_std"]) < 5e-5

    print()
    print("  his seed-0 value    %.6f   ours %s   %s"
          % (HIS["seed0_depth"], ("%.6f" % seed0) if seed0 else "none",
             "MATCH" if hit_seed0 else "differs"))
    print("  his 3-seed mean     %.6f   ours %s   %s"
          % (HIS["multi_mean"], ("%.6f" % mean3) if mean3 else "none",
             "MATCH" if hit_mean else "differs"))
    print("  his 3-seed std      %.6f   ours %s   %s"
          % (HIS["multi_std"], ("%.6f" % std3) if std3 else "none",
             "MATCH" if hit_std else "differs"))
    if rd:
        print("  across %d seeds the depth runs %.6f to %.6f, a spread of %.6f"
              % (len(rd), min(rd), max(rd), max(rd) - min(rd)))

    scatters = bool(rd) and (max(rd) - min(rd)) > 1e-6
    if not scatters:
        print("  NULL FIRED: the seeds agree on the random edge, so the seed does not explain the "
              "residual.")

    verdict = ("REPRODUCES_HIS_PUBLISHED_PAIR" if (hit_seed0 and hit_mean and hit_std)
               else "SEED_DEPENDENT_BUT_NOT_HIS_EXACT_NUMBERS" if scatters
               else "NOT_A_SEED_EFFECT")
    print("  VERDICT: %s" % verdict)

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "grid": "linspace(%g,%g,%d)" % GRID,
        "sector_n_up": N_UP,
        "workers": WORKERS,
        "his_published": HIS,
        "convention_ratio_his_over_ours": ratio,
        "ground_degeneracy_at_his_valley": deg,
        "lowest_levels_at_his_valley": levels,
        "tree_control": tree,
        "random_by_seed": rand,
        "our_seed0": seed0,
        "our_multi_mean": mean3,
        "our_multi_std": std3,
        "depth_range_across_seeds": [min(rd), max(rd)] if rd else None,
        "verdict": verdict,
        "controls": {
            "hamiltonian_conventions_cross_checked": True,
            "tree_control_did_not_scatter": True,
            "tree_control_hit_the_agreed_value": True,
            "null_can_fire_if_seeds_agree": True,
            "matched_seed0": hit_seed0, "matched_mean": hit_mean, "matched_std": hit_std,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
