"""Two single-use skills, both older than two weeks: does age decide which keeps its text, or position?

WHY. anthropics/claude-code#81081, @tonydzi 2026-09-21 (comment 5764466062): inside the user tier,
at usageCount=1, "declined" (48.1 days) arrived with text and "decide-as-cofounder" (18.2 days)
arrived name-only. He reads that as recency no longer being monotone. Our 2026-09-21 sweep
(at_two_uses_how_stale_before_a_fresh_single_use_wins.py) found the recency term steep for about
two weeks and flat after it, with a 7-day tie broken by listing order. Both of his skills sit past
two weeks. If the flat region is real, position decides between them and an interleaving is what
one listing should show.

The test: both halves at usageCount=1, the early half aged D1 and the late half aged D2, then the
same with the halves swapped (rpair). If age decides, the fresher group keeps its text in both
orientations. If position decides, the early half keeps its text in both.

POSITIVE CONTROL: a pair inside the steep region (10 days against 1 day). There, age must win in
both orientations, or the harness cannot see age at all and every "position wins" row is void.

Same mechanics as the sibling probes: isolated CLAUDE_CONFIG_DIR, seeded skillUsage, a local
recorder, zero completions.

    python -X utf8 probes/at_one_use_each_does_age_or_position_decide.py
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import does_the_listing_drop_by_usage_or_by_position as P  # noqa: E402

# (older, fresher) in days. (48.1, 18.2) is his pair. (10, 1) is the positive control.
PAIRS = [(48.1, 18.2), (60, 20), (30, 16), (90, 45), (10, 1)]


def main() -> int:
    if P.S.CLAUDE is None:
        raise SystemExit("REFUSED: no runnable `claude` on PATH")
    P.S.recorder(P.S.PORT)
    N, WIDE, NARROW = 220, 900, 150
    out = []
    for old, fresh in PAIRS:
        res = {}
        for kind in ("pair", "rpair"):
            # pair: early half = old, late half = fresh.  rpair: early half = fresh, late = old.
            r = P.run_arm("%s_1x_%gd_vs_1x_%gd" % (kind, old, fresh), N, WIDE, NARROW,
                          "%s:1:%g:%g" % (kind, old, fresh))
            early = sum(1 for x in r["kept_positions"] if x <= N / 2)
            late = len(r["kept_positions"]) - early
            kept_old = early if kind == "pair" else late
            kept_fresh = late if kind == "pair" else early
            assert r["isolated"] and r["seed_survived"], "control: isolated and seeded"
            assert r["names_on_wire"] == N, "control: every name arrived"
            assert 0 < len(r["kept_positions"]) < N, "control: something was dropped"
            res[kind] = {"kept_early": early, "kept_late": late, "kept_old": kept_old,
                         "kept_fresh": kept_fresh, "kept_total": len(r["kept_positions"])}
            print("  1 use %5.1f d vs 1 use %5.1f d, %-5s (old group %s): kept old %3d  fresh %3d"
                  % (old, fresh, kind, "early" if kind == "pair" else "late", kept_old, kept_fresh),
                  flush=True)
        a, b = res["pair"], res["rpair"]
        if a["kept_fresh"] > a["kept_old"] and b["kept_fresh"] > b["kept_old"]:
            verdict = "age decides (fresher kept in both orientations)"
        elif a["kept_early"] > a["kept_late"] and b["kept_early"] > b["kept_late"]:
            verdict = "position decides (early half kept in both orientations)"
        else:
            verdict = "mixed"
        out.append({"older_days": old, "fresher_days": fresh, "pair": a, "rpair": b, "verdict": verdict})
        print("    -> %s" % verdict, flush=True)
    ctl = [o for o in out if (o["older_days"], o["fresher_days"]) == (10, 1)][0]
    control_ok = ctl["verdict"].startswith("age")
    ver = subprocess.run([P.S.CLAUDE, "--version"], capture_output=True, text=True).stdout.strip()
    receipt = {"cli": ver, "skills": N, "rows": out,
               "positive_control_age_visible": control_ok}
    path = os.path.join(HERE, "at_one_use_each_does_age_or_position_decide.result.json")
    io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, indent=1) + "\n")
    print("positive control (10 d vs 1 d, age must win both ways):", "HOLDS" if control_ok else "FAILED")
    return 0 if control_ok else 1


if __name__ == "__main__":
    sys.exit(main())
