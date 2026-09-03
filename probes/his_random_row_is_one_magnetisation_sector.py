"""Does Table 2's random-graph depth come from scanning one magnetisation sector?

WHY. Table 2 reports the random graph's deepest valley as 0.1050 at edge (8,14), s = 1.20. His
per-edge file gives 0.104966 there. Regenerating that edge over every magnetisation sector gives
0.010163 in the projection view and -0.001524 in the single-state view: two orders apart. Before
telling him Table 2 does not reproduce, the difference has to be explained rather than reported.

THE HYPOTHESIS, taken from his own script rather than from a guess. His scan fixes `N_up = 7`
(line 229 of the full-data script) and calls `eigsh(k=1)` inside that sector. Our pipeline
determines which sectors hold the ground state and finds the random graph's ground manifold
spanning n_up = 6, 7, 8, 9 at one energy: an S = 3/2 multiplet, four members, one per sector. The
zz correlation is not the same in every member, so fixing the sector picks one member of a
degenerate manifold and reads its correlations as if they were the ground state's.

If that is the cause, running OUR pipeline restricted to n_up = 7 reproduces HIS number.

ARMS:
  A  his method:   random (8,14), sectors = [7], single state          -> expect ~0.104966 at 1.20
  B  our method:   random (8,14), every ground sector, both views      -> 0.010163 / -0.001524
  C  sensitivity:  the same edge at n_up = 6 and n_up = 8              -> must DIFFER from A

CONTROLS, each able to fail:
  * A POSITIVE CONTROL ON THE AGREED VALUE. Arm A is run first on tree edge (1,10), where his two
    views and the repaired CSV all give 0.058909125. If the single-sector arm cannot reproduce the
    number everyone agrees on, it is not his method and nothing else in this file is evidence.
  * ONE CODE PATH, ONE DIFFERENCE. Every arm calls the same `scan` and the same valley rule from
    `regenerate_edge_8_14.py`. The sector list is the only thing that changes between A and B.
  * BOTH VALLEY RULES ARE REPORTED. His `detect_valley` requires a strict interior local minimum;
    ours takes the minimum over the grid after s = 0. A depth that only appears under one rule is a
    finding about the rule, not about the sector, so both are printed for every arm.
  * A SENSITIVITY ARM THAT CAN REFUTE. If n_up = 6 and n_up = 8 give the same depth as n_up = 7,
    the sector is not what separates the numbers and the hypothesis is dead. That branch is live.
  * THE SECTOR IS CHECKED AGAINST THE GLOBAL GROUND ENERGY at the valley, so the report can say
    whether n_up = 7 holds a true ground state or a state above it.
"""
from __future__ import annotations

import io
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
OUT = os.path.join(HERE, "his_random_row_is_one_magnetisation_sector.result.json")

WORKERS = 4                    # of 24 logical CPUs, capped at the owner's standing limit.
GRID_LO, GRID_HI, GRID_N = 0.0, 3.0, 61      # the grid that produced Table 2, measured separately
HIS_SECTOR = 7                 # `N_up = 7` in his full-data script
CAL = {"edge": (1, 10), "expected": 0.058909125, "tol": 5e-6}
TARGET_EDGE = (8, 14)
HIS_TARGET = {"depth": 0.104966, "s": 1.20}


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def his_valley(rows):
    """His rule: the grid minimum, only if it is a strict interior local minimum. Depth from E(0)."""
    es = [r[1] for r in rows]
    i = min(range(len(es)), key=lambda k: es[k])
    if i == 0 or i == len(es) - 1:
        return {"s": None, "depth": None, "internal": False}
    if es[i] < es[i - 1] and es[i] < es[i + 1]:
        return {"s": rows[i][0], "depth": es[0] - es[i], "internal": True}
    return {"s": None, "depth": None, "internal": False}


def _arm(args):
    """One arm. Runs in a worker so the four are not serial on a 24-core box."""
    import numpy as np
    from regenerate_edge_8_14 import scan, valley
    label, which, contra, sectors, standard = args
    import networkx as nx
    if which == "tree":
        edges = [tuple(sorted(e)) for e in nx.random_labeled_tree(15, seed=42).edges()]
    else:
        edges = [tuple(sorted(e)) for e in nx.gnm_random_graph(15, 27, seed=42).edges()]
    grid = np.linspace(GRID_LO, GRID_HI, GRID_N)
    rows = scan(edges, contra, grid, standard=standard, cache={}, sectors=sectors)
    return {"label": label, "graph": which, "edge": list(contra), "sectors": sectors,
            "standard": standard,
            "our_rule": valley(rows),
            "his_rule": his_valley(rows),
            "E_at_zero": rows[0][1],
            "degeneracy_seen": sorted({r[3] for r in rows})}


def main():
    print("  parallelism: %d workers of %d logical CPUs; %d arms, %d grid points each"
          % (WORKERS, os.cpu_count(), 6, GRID_N))

    arms = [
        ("A_control_tree_his_sector", "tree", CAL["edge"], [HIS_SECTOR], True),
        ("A_target_random_his_sector", "random", TARGET_EDGE, [HIS_SECTOR], True),
        ("B_target_random_all_sectors_single_state", "random", TARGET_EDGE, None, True),
        ("B_target_random_all_sectors_projection", "random", TARGET_EDGE, None, False),
        ("C_sensitivity_random_sector_6", "random", TARGET_EDGE, [6], True),
        ("C_sensitivity_random_sector_8", "random", TARGET_EDGE, [8], True),
    ]

    t0 = time.time()
    with mp.Pool(WORKERS) as pool:
        results = {r["label"]: r for r in pool.map(_arm, arms)}
    print("  all arms done in %.0fs" % (time.time() - t0))

    print()
    for label, r in results.items():
        o, h = r["our_rule"], r["his_rule"]
        print("  %-42s our %+.6f at s=%.2f | his %s at s=%s"
              % (label, o["depth"], o["valley_s"],
                 ("%+.6f" % h["depth"]) if h["depth"] is not None else "  none  ", h["s"]))

    # CONTROL: the positive control on the agreed value, under HIS rule, since it is his method.
    cal = results["A_control_tree_his_sector"]
    cal_depth = cal["his_rule"]["depth"]
    if cal_depth is None:
        refuse("the single-sector arm found no interior valley on tree edge (1,10), so it does not "
               "reproduce the one number every source agrees on")
    if abs(cal_depth - CAL["expected"]) > CAL["tol"]:
        refuse("the single-sector arm gives %.9f on tree edge (1,10) against the agreed %.9f, so it "
               "is not his method and nothing here is evidence" % (cal_depth, CAL["expected"]))
    print()
    print("  POSITIVE CONTROL: single-sector arm reproduces tree (1,10) at %.9f, off %.2e"
          % (cal_depth, abs(cal_depth - CAL["expected"])))

    his_arm = results["A_target_random_his_sector"]["his_rule"]
    reproduces = (his_arm["depth"] is not None
                  and abs(his_arm["depth"] - HIS_TARGET["depth"]) < 5e-5
                  and abs(his_arm["s"] - HIS_TARGET["s"]) < 1e-9)

    # CONTROL: the sensitivity arm has to be able to refute the hypothesis.
    s6 = results["C_sensitivity_random_sector_6"]["his_rule"]["depth"]
    s8 = results["C_sensitivity_random_sector_8"]["his_rule"]["depth"]
    others = [d for d in (s6, s8) if d is not None]
    sector_matters = any(abs(d - (his_arm["depth"] or 0.0)) > 1e-6 for d in others) if others else None
    if sector_matters is False:
        print("  SENSITIVITY: n_up 6 and 8 give the same depth as 7, so the sector does NOT explain "
              "the difference. The hypothesis fails here.")

    verdict = ("SECTOR_EXPLAINS_IT" if reproduces and sector_matters
               else "NOT_EXPLAINED_BY_THE_SECTOR")
    print()
    print("  his published value for random (8,14): %.6f at s=%.2f"
          % (HIS_TARGET["depth"], HIS_TARGET["s"]))
    print("  our single-sector reproduction:        %s at s=%s"
          % (("%.6f" % his_arm["depth"]) if his_arm["depth"] is not None else "none", his_arm["s"]))
    print("  VERDICT: %s" % verdict)

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "grid": "linspace(%g,%g,%d)" % (GRID_LO, GRID_HI, GRID_N),
        "workers": WORKERS,
        "his_published_value": HIS_TARGET,
        "arms": results,
        "verdict": verdict,
        "controls": {
            "positive_control_on_the_agreed_value_passed": True,
            "one_code_path_only_the_sector_changes": True,
            "both_valley_rules_reported": True,
            "sensitivity_arm_can_refute": bool(others),
            "sector_changes_the_depth": sector_matters,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
