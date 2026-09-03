"""SUPERSEDED 2026-09-03. Do not cite this file's conclusion.

It enumerated ARPACK eigenvectors and reported that four of Table 1's five values match no
state, on the premise that the ground manifold carries ONE diagnosis value. That premise came
from a real-rotation test which cannot reach the manifold's interior. The reachable set is the
closed interval [0.110269137, 0.159658244] and all five published values lie inside it, at
r = 0.996, 0.785, 0.796, 0.778 and 0.839. We had already sent Li Guanghao exactly this on
2026-08-31 in comment 5380781829, with the same a and b to nine decimals, so the "finding" here
was also a restatement of our own published result.

Replaced by probes/the_manifold_reachable_set_is_an_interval_and_real_rotations_cannot_see_it.py.
Kept because a receipt that quietly disappears is worse than one that records what it got wrong.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "agora_output", "edrn_submission"))
OUT = os.path.join(HERE, "where_table_1s_five_seed_values_come_from.result.json")

HIS_EDGES = [(0, 6), (0, 8), (1, 9), (1, 11), (2, 12), (2, 14),
             (3, 6), (3, 7), (3, 9), (3, 10), (4, 10), (4, 11), (4, 12), (4, 13),
             (5, 7), (5, 8), (5, 13), (5, 14),
             (6, 7), (7, 8), (9, 10), (10, 11), (12, 13), (13, 14),
             (6, 8), (9, 11), (12, 14)]
CONTRA = (0, 6)
VALLEY_S = 1.0
SECTORS = (6, 7, 8)
LEVELS = 6
TOL = 5e-4                      # the published values carry six decimals; match to the fourth
PUBLISHED_VALLEY = [0.159295, 0.142707, 0.143544, 0.142196, 0.146785]
PUBLISHED_DEPTH = [0.087436, 0.104024, 0.103187, 0.104535, 0.099946]
PUBLISHED_BASELINE = 0.246731   # every row of Table 1 sums to this


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def zz_std(vec, basis, edges):
    import numpy as np
    p = np.abs(vec) ** 2
    out = []
    for (a, b) in edges:
        sp = np.array([(1.0 if (st >> a) & 1 else -1.0) * (1.0 if (st >> b) & 1 else -1.0)
                       for st in basis])
        out.append(float(p @ sp))
    return float(np.std(out))


def main():
    # SUPERSEDED, AND IT REFUSES RATHER THAN PRINTING A FRESH-LOOKING RESULT. Re-running this file
    # would write a new receipt for a conclusion that is void, and a receipt with today's timestamp
    # is exactly what a reader trusts. The replacement computes the reachable interval instead of
    # enumerating ARPACK's real eigenvectors.
    refuse("superseded on 2026-09-03. The ground manifold's reachable diagnoses form the closed "
           "interval [0.110269137, 0.159658244], not the single point this probe's premise assumed, "
           "and all five of Table 1's values lie inside it. Use "
           "probes/the_manifold_reachable_set_is_an_interval_and_real_rotations_cannot_see_it.py.")

def _original_main():
    import numpy as np
    from scipy.sparse.linalg import eigsh
    from regenerate_edge_8_14 import build_H, sector_basis

    print("  serial: %d sectors x %d levels at s=%.2f, plus one baseline solve"
          % (len(SECTORS), LEVELS, VALLEY_S))

    # POSITIVE CONTROL: the baseline every published row shares.
    b7 = sector_basis(15, 7)
    wb, vb = eigsh(build_H(HIS_EDGES, CONTRA, 0.0, b7), k=2, which="SA")
    base = zz_std(vb[:, int(np.argmin(wb))], b7, HIS_EDGES)
    print("  E(0) in sector n_up=7: %.9f  against the published %.6f" % (base, PUBLISHED_BASELINE))
    if abs(base - PUBLISHED_BASELINE) > 5e-6:
        refuse("our E(0) is %.9f against the published %.6f, so the graph, sector or convention "
               "differs and no comparison below is about their table" % (base, PUBLISHED_BASELINE))

    rows, t0 = [], time.time()
    ground = None
    for n_up in SECTORS:
        basis = sector_basis(15, n_up)
        w, v = eigsh(build_H(HIS_EDGES, CONTRA, VALLEY_S, basis), k=LEVELS, which="SA")
        o = np.argsort(w)
        w, v = w[o], v[:, o]
        if n_up == 7:
            ground = float(w[0])
        for k in range(LEVELS):
            rows.append({"n_up": n_up, "level": k, "energy": float(w[k]),
                         "diagnosis": zz_std(v[:, k], basis, HIS_EDGES)})
    for r in rows:
        r["above_ground"] = r["energy"] - ground
    print("  %d states enumerated in %.0fs" % (len(rows), time.time() - t0))

    print()
    print("  n_up level   energy      above ground   diagnosis   matches a published value")
    matched = {}
    for r in sorted(rows, key=lambda r: r["energy"]):
        hit = [p for p in PUBLISHED_VALLEY if abs(r["diagnosis"] - p) < TOL]
        for p in hit:
            matched.setdefault(p, []).append(r)
        print("   %2d   %2d   %10.6f  %10.6f   %9.6f   %s"
              % (r["n_up"], r["level"], r["energy"], r["above_ground"], r["diagnosis"],
                 ", ".join("%.6f" % p for p in hit) or "-"))

    unexplained = [p for p in PUBLISHED_VALLEY if p not in matched]
    print()
    print("  published values reproduced by some enumerated state: %d of %d"
          % (len(matched), len(PUBLISHED_VALLEY)))
    if unexplained:
        print("  NOT IDENTIFIED: %s" % ", ".join("%.6f" % p for p in unexplained))
        print("  The source of these is not established by this probe. It is not evidence that they "
              "are wrong, only that no state enumerated here produces them.")

    ground_states = [r for r in rows if abs(r["above_ground"]) < 1e-9]
    ground_vals = sorted({round(r["diagnosis"], 9) for r in ground_states})
    print("  ground level: %d states across sectors %s, diagnosis values %s"
          % (len(ground_states), sorted({r["n_up"] for r in ground_states}),
             ["%.9f" % v for v in ground_vals]))

    from_ground = [p for p in PUBLISHED_VALLEY
                   if any(abs(p - v) < TOL for v in ground_vals)]
    print("  published values consistent with a GROUND state: %d of %d  %s"
          % (len(from_ground), len(PUBLISHED_VALLEY), ["%.6f" % p for p in from_ground]))

    json.dump({
        "script": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "graph": "L2 Sierpinski gasket, his labelling", "edge": list(CONTRA), "s": VALLEY_S,
        "match_tolerance": TOL,
        "published_valley_values": PUBLISHED_VALLEY,
        "published_depths": PUBLISHED_DEPTH,
        "published_baseline": PUBLISHED_BASELINE,
        "our_baseline": base,
        "states": rows,
        "ground_diagnosis_values": ground_vals,
        "published_values_matched_by_some_state": {("%.6f" % p): [
            {"n_up": r["n_up"], "level": r["level"], "above_ground": r["above_ground"]}
            for r in v] for p, v in matched.items()},
        "published_values_consistent_with_a_ground_state": from_ground,
        "not_identified": unexplained,
        "controls": {
            "baseline_positive_control_passed": True,
            "search_covers_three_sectors_and_six_levels": True,
            "null_can_fire_and_is_reported_as_not_identified": True,
            "energy_above_ground_reported_for_every_match": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
