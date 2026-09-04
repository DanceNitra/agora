"""The matched null he asked for, built without cutting anything.

HIS OBJECTION, 2026-09-04: separating the two entrances cuts the shared ground state, so the
separated system is no longer the same observation. He is right, and our earlier nulls did cut it.

THE ANSWER IS NOT A DEFINITION. It is a null that needs no cutting. His graph has 20 edges, so it
has C(20,2) = 190 entrance pairs. Every one of them sits in the SAME Hamiltonian, shares ONE ground
state, and is scored by the SAME statistic. Nothing is separated, nothing is rewired, and the
relational field he says the cut destroys is intact in all 190. His five reported pairs are five
draws from this population.

If his (0,1)-(6,8) deviation sits high in that population, the number is doing work. If it sits in
the middle, the statistic is reporting the graph rather than those two entrances.

THE STATISTIC IS HIS, transcribed from his script: E_pred(s1,s2) = E1(s1) + E2(s2) - E(1,1), and
the deviation is the mean absolute difference between the measured E(s1,s2) and that prediction,
over his 21-point grid on [0,3]. The fraction is that deviation over the system's own E range,
because an absolute deviation is not comparable across systems with different ranges.

SECOND MEASUREMENT, on his distance analysis. He replaced the null with a Spearman correlation
between deviation and entrance distance over five pairs, and reports r = 0.000, p = 1.000. This
enumerates every permutation of that design to say what it could have shown, rather than calling it
"underpowered" and moving on.

CONTROLS, each able to fail:
  * POSITIVE CONTROL: his own pair must reproduce his published 0.049977 to 1e-6. If it does not,
    the reimplementation is wrong and the population below means nothing.
  * THE POPULATION MUST VARY. If every pair returned the same deviation the percentile would be an
    artefact of ties rather than a rank.
  * HIS FIVE PAIRS ARE LOCATED IN IT. They were measured by him, independently, so they are a
    second check on the reimplementation as well as data.
  * THE PERMUTATION FLOOR IS COMPUTED, NOT ASSERTED. If the smallest reachable p on his design is
    above 0.05, no possible arrangement of those five points could have been significant, which is
    a statement about the design and not about his result.

Owner's standing instruction: at most 4 cores. This runs on one and prints a heartbeat.
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

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "the_matched_null_lives_on_his_own_graph.result.json")

GRID = np.linspace(0.0, 3.0, 21)          # his S_MIN, S_MAX, S_GRID_SIZE
N, N_UP = 10, 5
HIS_PAIR = ((0, 1), (6, 8))
HIS_MEAN_ABS = 0.04997721400862463        # his published figure for that pair

# His five reported pairs, retyped from his 2026-09-04 comment, with the deviation percentages he
# gives and the node distances he assigns.
HIS_FIVE = [(((0, 1), (6, 8)), 2, 24.5), (((0, 1), (1, 4)), 1, 17.4),
            (((0, 1), (7, 9)), 2, 19.1), (((6, 8), (1, 8)), 1, 24.2),
            (((2, 5), (3, 4)), 1, 28.0)]


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def graph():
    import networkx as nx
    G = nx.watts_strogatz_graph(10, 4, 0.1, seed=42)
    edges = [tuple(sorted(e)) for e in G.edges()]
    if len(edges) != 20:
        refuse("the small-world generator gave %d edges, not 20" % len(edges))
    return G, edges


# THE PHYSICS IS IMPORTED, NOT REWRITTEN. A first version of this file built its own Hamiltonian
# and its positive control refused at once: his pair came out 0.052184364 against his published
# 0.049977214. The cause was the coupling convention. His script, transcribed in the separable-null
# probe, puts +/-1 on the diagonal where mine put +/-0.25. Reusing the module that already
# reproduces his number to 1e-11 removes a whole class of quiet disagreement.
sys.path.insert(0, HERE)
from separable_null_for_the_multi_entrance_deviation import (  # noqa: E402
    ground_vector, corrs_from, E_of)


def pair_deviation(edges, i1, i2):
    """(mean absolute deviation, fraction of that system's own E range) for one entrance pair."""
    nodes = list(range(N))
    J = np.ones(len(edges))
    e2d = np.empty((len(GRID), len(GRID)))
    for i, a in enumerate(GRID):
        for j, b in enumerate(GRID):
            J[:] = 1.0
            J[i1], J[i2] = a, b
            _w, v, bas = ground_vector(nodes, edges, J, N_UP)
            e2d[i, j] = E_of(corrs_from(v, bas, edges))
    # THE MARGINALS ARE AT EXACTLY s = 1.0, WHICH IS NOT ON THE GRID. His grid is
    # linspace(0, 3, 21), step 0.15, so it runs 0.90, 1.05, and never touches 1.0. Reading the
    # marginals off the 2D grid instead, at the nearest column, gave 0.052184364 against his
    # 0.049977214 and the positive control refused. The uniform point has to be evaluated, not
    # approximated.
    def at(s1, s2):
        J[:] = 1.0
        J[i1], J[i2] = s1, s2
        _w, vv, bb = ground_vector(nodes, edges, J, N_UP)
        return E_of(corrs_from(vv, bb, edges))

    e1 = np.array([at(s, 1.0) for s in GRID])
    e2 = np.array([at(1.0, s) for s in GRID])
    # AND THE REFERENCE IS e1 AT THE NEAREST GRID COLUMN, not E(1,1). His transcription reads
    # ref = e1[argmin(|grid - 1|)], which is E(1.05, 1.0) on this grid. Using E(1.0, 1.0) instead
    # gave 0.048837020 against his 0.049977214. Both near misses came from treating the uniform
    # point as if it were a grid point; it is neither, and the formula uses a third thing.
    ref = float(e1[int(np.argmin(np.abs(GRID - 1.0)))])
    d = np.abs(e2d - (e1[:, None] + e2[None, :] - ref))
    rng = e2d.max() - e2d.min()
    return float(d.mean()), (float(d.mean() / rng) if rng > 0 else None)


def permutation_facts(dists, devs):
    """Everything the five-point Spearman design could ever have shown."""
    from scipy import stats
    r0, p0 = stats.spearmanr(dists, devs)
    rs = [stats.spearmanr(dists, list(perm))[0] for perm in itertools.permutations(devs)]
    rs = [0.0 if np.isnan(r) else float(r) for r in rs]
    absr = [abs(r) for r in rs]
    # The exact two-sided permutation p for the most extreme arrangement possible.
    best = max(absr)
    p_floor = sum(1 for r in absr if r >= best - 1e-12) / len(rs)
    modal_zero = sum(1 for r in rs if abs(r) < 1e-12)
    return {"r": float(r0), "p": float(p0), "arrangements": len(rs),
            "max_abs_r_reachable": best, "smallest_reachable_two_sided_p": p_floor,
            "arrangements_giving_r_zero": modal_zero,
            "distinct_distance_values": sorted(set(dists))}


def main():
    t0 = time.time()
    G, edges = graph()
    idx = {e: i for i, e in enumerate(edges)}
    for e in HIS_PAIR:
        if e not in idx:
            refuse("edge %s is not in his graph" % (e,))

    # POSITIVE CONTROL first. Nothing below counts if his own number does not reproduce.
    m, frac = pair_deviation(edges, idx[HIS_PAIR[0]], idx[HIS_PAIR[1]])
    print("  CONTROL his pair %s-%s: mean abs %.9f against his published %.9f  [%.0fs]"
          % (HIS_PAIR[0], HIS_PAIR[1], m, HIS_MEAN_ABS, time.time() - t0))
    if abs(m - HIS_MEAN_ABS) > 1e-6:
        refuse("his own pair does not reproduce (%.9f vs %.9f), so the population below would be "
               "measuring a different statistic from his" % (m, HIS_MEAN_ABS))

    pairs = list(itertools.combinations(range(len(edges)), 2))
    print("  scanning all %d entrance pairs on his graph, one shared ground state throughout"
          % len(pairs))
    rows = []
    for n, (a, b) in enumerate(pairs, 1):
        mm, ff = pair_deviation(edges, a, b)
        rows.append({"pair": [list(edges[a]), list(edges[b])], "mean_abs": mm, "fraction": ff})
        if n % 20 == 0 or n == len(pairs):
            print("     %3d/%d  [%.0fs]" % (n, len(pairs), time.time() - t0))

    vals = np.array([r["mean_abs"] for r in rows])
    fracs = np.array([r["fraction"] for r in rows if r["fraction"] is not None])
    if vals.std() < 1e-9:
        refuse("every pair returns the same deviation, so a percentile would be an artefact of "
               "ties rather than a rank")

    below = int((vals < HIS_MEAN_ABS).sum())
    pct = 100.0 * below / len(vals)
    print()
    print("  THE NULL BAND, all 190 pairs on his own graph, nothing cut:")
    print("     mean absolute deviation   min %.6f   median %.6f   max %.6f"
          % (vals.min(), float(np.median(vals)), vals.max()))
    print("     as a fraction of E range  min %.1f%%   median %.1f%%   max %.1f%%"
          % (100 * fracs.min(), 100 * float(np.median(fracs)), 100 * fracs.max()))
    print("     his pair %.6f sits at the %.0fth percentile (%d of %d pairs are below it)"
          % (HIS_MEAN_ABS, pct, below, len(vals)))

    # HIS FIVE, located in the population.
    print()
    print("  his five reported pairs, located in that population:")
    five = []
    for (e1, e2), dist, his_pct in HIS_FIVE:
        if e1 not in idx or e2 not in idx:
            refuse("his reported pair %s-%s is not in the graph as we build it" % (e1, e2))
        mm, ff = pair_deviation(edges, idx[e1], idx[e2])
        rank = int((vals < mm).sum())
        five.append({"pair": [list(e1), list(e2)], "distance": dist, "his_percent": his_pct,
                     "our_fraction_percent": 100 * ff, "mean_abs": mm,
                     "percentile_in_population": 100.0 * rank / len(vals)})
        print("     %-8s %-8s  his %.1f%%   ours %.1f%%   population percentile %.0f"
              % (e1, e2, his_pct, 100 * ff, 100.0 * rank / len(vals)))

    perm = permutation_facts([d for _, d, _ in HIS_FIVE], [p for _, _, p in HIS_FIVE])
    print()
    print("  his distance test, every arrangement enumerated:")
    print("     r = %.3f, p = %.3f as he reports" % (perm["r"], perm["p"]))
    print("     over all %d arrangements the largest reachable |r| is %.3f"
          % (perm["arrangements"], perm["max_abs_r_reachable"]))
    print("     so the smallest two-sided p this design can ever produce is %.2f"
          % perm["smallest_reachable_two_sided_p"])
    print("     distinct distance values among his five pairs: %s"
          % perm["distinct_distance_values"])
    if perm["smallest_reachable_two_sided_p"] <= 0.05:
        print("     NOTE: the design CAN reach significance, so the draft must not say it cannot.")

    json.dump({"script": os.path.basename(__file__),
               "graph": "watts_strogatz(10,4,0.1,seed=42)", "sector_n_up": N_UP,
               "grid": "linspace(0,3,21)", "pairs_scanned": len(pairs),
               "control_his_pair": m, "his_published": HIS_MEAN_ABS,
               "band": {"min": float(vals.min()), "median": float(np.median(vals)),
                        "max": float(vals.max()),
                        "frac_min": float(fracs.min()), "frac_median": float(np.median(fracs)),
                        "frac_max": float(fracs.max())},
               "his_pair_percentile": pct, "pairs_below_his": below,
               "his_five": five, "permutation": perm,
               "controls": {"positive_control_reproduces_his_number": True,
                            "population_varies": float(vals.std()),
                            "his_five_located": len(five),
                            "permutation_floor_computed": True},
               "seconds": time.time() - t0},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print()
    print("  written: %s  [%.0fs]" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
