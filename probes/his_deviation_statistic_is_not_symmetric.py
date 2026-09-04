"""Does his multi-entrance deviation depend on which entrance is called the first one?

WHY IT CAN. His formula is E_pred(s1,s2) = E1(s1) + E2(s2) - E_ref, with E1 scanning entrance one
at s2 = 1 and E2 scanning entrance two at s1 = 1. The reference is not E(1,1). Transcribed from his
script it is e1 at the grid column nearest 1.0, which on linspace(0,3,21) is E(1.05, 1.0). That
value belongs to entrance one, so the two entrances do not enter the formula in the same way, and
swapping their roles moves the whole predicted surface.

Whether the shift matters is a question about his graph and not about the algebra, so it has to be
measured rather than argued.

MEASURED, on his graph, his sector, his grid, both orderings of four of his own pairs:

    pair               A then B     B then A     difference
    (6,8)-(1,8)        0.037152     0.032670     -12.1%
    (0,1)-(6,8)        0.049977     0.050465      +1.0%
    (0,1)-(1,4)        0.032136     0.033575      +4.5%
    (2,5)-(3,4)        0.034392     0.033550      -2.4%

So it is not a rounding effect. His published 0.049977 becomes 0.050465 with the entrances swapped,
and one of his own pairs moves by 12 percent.

HOW THIS SURFACED, because the route matters. Two independent implementations of the 190-pair
census disagreed on exactly one of his five pairs, (6,8)-(1,8), and agreed to every digit on the
other four. Neither was wrong. They had fixed the entrance order differently, and that pair is the
order-sensitive one.

CONTROLS:
  * POSITIVE CONTROL: one ordering of his headline pair must reproduce his published 0.049977214.
    Without it a difference between two orderings could be a difference between two bugs.
  * THE EFFECT MUST NOT BE UNIFORM. If every pair shifted by the same amount the cause would be a
    constant offset in the transcription rather than an asymmetry in the formula.
  * A SYMMETRIC REFERENCE MUST REMOVE IT. Recomputing with E(1,1), which treats both entrances
    alike, has to bring the two orderings together. If it does not, the diagnosis is wrong.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "his_deviation_statistic_is_not_symmetric.result.json")
sys.path.insert(0, HERE)

from the_matched_null_lives_on_his_own_graph import graph, pair_deviation, GRID, N, N_UP  # noqa
from separable_null_for_the_multi_entrance_deviation import (  # noqa
    ground_vector, corrs_from, E_of)

HIS_PUBLISHED = 0.04997721400862463
PAIRS = [((6, 8), (1, 8)), ((0, 1), (6, 8)), ((0, 1), (1, 4)), ((2, 5), (3, 4))]


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def symmetric_reference(edges, i1, i2):
    """The same statistic with E(1,1) as the reference, which treats both entrances alike."""
    nodes = list(range(N))
    J = np.ones(len(edges))

    def at(s1, s2):
        J[:] = 1.0
        J[i1], J[i2] = s1, s2
        _w, v, b = ground_vector(nodes, edges, J, N_UP)
        return E_of(corrs_from(v, b, edges))

    e2d = np.array([[at(a, b) for b in GRID] for a in GRID])
    e1 = np.array([at(s, 1.0) for s in GRID])
    e2 = np.array([at(1.0, s) for s in GRID])
    ref = at(1.0, 1.0)
    return float(np.abs(e2d - (e1[:, None] + e2[None, :] - ref)).mean())


def main():
    t0 = time.time()
    _G, edges = graph()
    idx = {e: i for i, e in enumerate(edges)}
    rows = []
    print("  %-22s %-12s %-12s %s" % ("pair", "A then B", "B then A", "difference"))
    for a, b in PAIRS:
        if a not in idx or b not in idx:
            refuse("pair %s-%s is not in his graph" % (a, b))
        m1, _ = pair_deviation(edges, idx[a], idx[b])
        m2, _ = pair_deviation(edges, idx[b], idx[a])
        pct = 100.0 * (m2 - m1) / m1
        rows.append({"pair": [list(a), list(b)], "ab": m1, "ba": m2, "percent": pct})
        print("  %-22s %-12.6f %-12.6f %+.1f%%  [%.0fs]"
              % ("%s-%s" % (a, b), m1, m2, pct, time.time() - t0))

    head = next(r for r in rows if r["pair"] == [[0, 1], [6, 8]])
    if abs(head["ab"] - HIS_PUBLISHED) > 1e-6:
        refuse("his headline pair does not reproduce in either ordering (%.9f), so a difference "
               "between orderings could be a difference between two bugs" % head["ab"])
    print("  CONTROL: his published %.9f reproduces in the A-then-B ordering" % HIS_PUBLISHED)

    pcts = [r["percent"] for r in rows]
    if max(pcts) - min(pcts) < 1.0:
        refuse("every pair shifts by nearly the same amount (%.2f to %.2f), which is a constant "
               "offset in the transcription rather than an asymmetry in the formula"
               % (min(pcts), max(pcts)))
    print("  CONTROL: the shift is not uniform, %+.1f%% to %+.1f%%, so it is not a constant offset"
          % (min(pcts), max(pcts)))

    worst = max(rows, key=lambda r: abs(r["percent"]))
    a, b = [tuple(x) for x in worst["pair"]]
    s1 = symmetric_reference(edges, idx[a], idx[b])
    s2 = symmetric_reference(edges, idx[b], idx[a])
    sym_pct = 100.0 * (s2 - s1) / s1
    print()
    print("  with a SYMMETRIC reference E(1,1) on the worst pair %s-%s: %.6f vs %.6f, %+.2f%%"
          % (a, b, s1, s2, sym_pct))
    if abs(sym_pct) > abs(worst["percent"]) / 2:
        refuse("a symmetric reference does not remove the gap (%.2f%% against %.2f%%), so the "
               "reference point is not the cause and the diagnosis is wrong"
               % (sym_pct, worst["percent"]))
    print("  CONTROL: the symmetric reference removes it, so the reference point is the cause")

    json.dump({"script": os.path.basename(__file__), "graph": "watts_strogatz(10,4,0.1,seed=42)",
               "grid": "linspace(0,3,21)", "sector_n_up": N_UP,
               "his_published": HIS_PUBLISHED, "rows": rows,
               "worst_pair": worst["pair"], "worst_percent": worst["percent"],
               "symmetric_reference": {"ab": s1, "ba": s2, "percent": sym_pct},
               "verdict": "THE_REFERENCE_POINT_BREAKS_THE_SYMMETRY",
               "controls": {"positive_control_reproduces_his_number": True,
                            "shift_is_not_uniform": True,
                            "symmetric_reference_removes_it": True},
               "seconds": time.time() - t0},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s  [%.0fs]" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
