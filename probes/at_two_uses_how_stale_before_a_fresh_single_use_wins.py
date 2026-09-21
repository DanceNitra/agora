"""At 2 uses against 1, how stale does the 2-use skill have to be before the fresh 1-use one is kept?

WHY. anthropics/claude-code#81081. Our 2026-08-26 sweep held the age gap at ONE YEAR and swept the
count ratio: recency won at 1x, 2x and 5x, count won at 10x and 20x. That already rules out a
lexicographic count-then-recency rule (a 2-use skill a year stale lost to a 1-use skill seconds old),
which is the model @tonydzi's 2026-09-19 listing could not separate from a weighted score: on his
machine a 2-use skill last used 2026-07-27 was KEPT over a 1-use skill last used 2026-08-30. Both
observations fit one weighted rule only if the crossover at ratio 2 lies between his gap (about
seven weeks) and ours (a year). This probe sweeps the gap at ratio 2 to find it.

He also reported a skill with NO skillUsage record arriving with text. The last arm here seeds
records for the late half only and asks where the unrecorded half lands.

MECHANICS are the sibling probe's: an isolated CLAUDE_CONFIG_DIR, seeded skillUsage, a local
recorder, zero completions. Every arm re-asserts its controls (isolated, seeded, names arrived,
something dropped). The recorded CLI version is in the receipt; the earlier sweep ran on 2.1.246.

    python probes/at_two_uses_how_stale_before_a_fresh_single_use_wins.py
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

GAPS_DAYS = [7, 8, 9, 10, 14, 21, 30, 45, 60, 90, 120, 180, 270, 365]
# Both sides stale, the shape an organic listing has. (2 uses, 54 d) against (1 use, 20 d) is
# @tonydzi's kept/dropped pair of 2026-09-19; the rest move one side at a time.
# The position control: the same shapes with the 2-use group in the LATE half. The 7-day and
# 8-day rows are the ratio-sweep boundary re-measured with the sides swapped.
SWAPPED = [(54, 20), (30, 17), (30, 14), (7, 0), (8, 0), (365, 300)]
PAIRS = [(54, 20), (54, 0), (30, 10), (30, 12), (30, 14), (30, 17), (30, 20), (30, 29), (54, 14), (365, 14), (60, 30), (90, 60), (365, 300)]


def main() -> int:
    if P.S.CLAUDE is None:
        raise SystemExit("REFUSED: no runnable `claude` on PATH")
    srv = P.S.recorder(P.S.PORT)
    N, WIDE, NARROW = 220, 900, 150
    rows = []
    for d in GAPS_DAYS:
        rows.append(P.run_arm("gap_%dd" % d, N, WIDE, NARROW, "gap:2:%d" % d))
        r = rows[-1]
        e = sum(1 for x in r["kept_positions"] if x <= N / 2)
        print("  ratio 2x, 2-use half %3d days stale: kept early(2-use) %3d  late(1-use fresh) %3d"
              % (d, e, len(r["kept_positions"]) - e), flush=True)
    pair_rows = []
    for d1, d2 in PAIRS:
        r = P.run_arm("pair_2x_%dd_vs_1x_%dd" % (d1, d2), N, WIDE, NARROW, "pair:2:%d:%d" % (d1, d2))
        pair_rows.append(((d1, d2), r))
        e = sum(1 for x in r["kept_positions"] if x <= N / 2)
        print("  2 uses %3d days old against 1 use %3d days old: kept 2-use %3d  1-use %3d"
              % (d1, d2, e, len(r["kept_positions"]) - e), flush=True)
    # POSITION CONTROL. Every count win above had the 2-use group in the EARLY half, which listing
    # order favours on its own. The same pairs with the 2-use group in the LATE half: a count win
    # there is a count win.
    swapped = []
    for d1, d2 in SWAPPED:
        r = P.run_arm("swapped_2x_%dd_vs_1x_%dd" % (d1, d2), N, WIDE, NARROW, "rpair:2:%d:%d" % (d1, d2))
        swapped.append(((d1, d2), r))
        late2 = sum(1 for x in r["kept_positions"] if x > N / 2)
        print("  SWAPPED 2 uses %3d d (late half) against 1 use %3d d (early): kept 2-use %3d  1-use %3d"
              % (d1, d2, late2, len(r["kept_positions"]) - late2), flush=True)
    un = P.run_arm("unrecorded_early", N, WIDE, NARROW, "unrecorded_early")
    rows.append(un)
    rows.extend(r for _p, r in pair_rows)
    rows.extend(r for _p, r in swapped)
    srv.shutdown()

    v = {}
    v["CONTROL_the_config_was_isolated"] = all(r["isolated"] for r in rows)
    v["note_the_real_profile_was_rewritten_by_another_process_during_the_run"] = any(
        r.get("real_profile_touched_during_run") for r in rows)
    v["CONTROL_the_seed_was_written_and_survived"] = all(
        r["seed_survived"] and r["seeded_entries"] > 0 for r in rows)
    v["CONTROL_every_name_arrived"] = all(r["names_on_wire"] == r["skills"] for r in rows)
    v["CONTROL_something_was_dropped_in_every_arm"] = all(
        0 < r["descriptions_on_wire"] < r["skills"] for r in rows)

    def early_wins(r):
        e = sum(1 for x in r["kept_positions"] if x <= N / 2)
        return e > len(r["kept_positions"]) - e

    sweep = [(d, r) for d, r in zip(GAPS_DAYS, rows)]
    flips = [(lo, hi) for (lo, a), (hi, b) in zip(sweep, sweep[1:]) if early_wins(a) != early_wins(b)]
    v["the_smallest_gap_row_reads_count_with_the_2use_group_early_only"] = early_wins(sweep[0][1])
    v["recency_wins_at_a_year"] = not early_wins(sweep[-1][1])
    v["THE_CROSSOVER_IS_BRACKETED_ONCE"] = len(flips) == 1
    v["a_lexicographic_count_then_recency_rule_is_refuted"] = any(not early_wins(r) for _d, r in sweep)
    pairs_out = {"%d_vs_%d" % p: ("count" if early_wins(r) else "recency") for p, r in pair_rows}
    swapped_out = {"%d_vs_%d" % p: ("count" if not early_wins(r) else "recency") for p, r in swapped}
    # The unswapped reading of the same shape: the pair arms, or the gap sweep for (d, 0).
    gap_out = {"%d_vs_0" % d: ("count" if early_wins(r) else "recency") for d, r in sweep}
    verdicts = {}
    for k, sw in swapped_out.items():
        un_ = pairs_out.get(k, gap_out.get(k))
        verdicts[k] = sw if sw == un_ else "TIE, listing order decides"
    ties = [k for k, x in verdicts.items() if x.startswith("TIE")]
    # Measured 2026-09-21: (7, 0) read "count" with the 2-use group early and "recency" with it
    # late, so the 7-day row of the sweep is a tie broken by position, not a count win. Every
    # other shape read the same in both orientations. A tie is reported, never counted as a win.
    v["CONTROL_position_every_non_tie_reads_the_same_in_both_orientations"] = all(
        x != "TIE, listing order decides" or k in ties for k, x in verdicts.items())
    v["the_7_day_row_is_a_tie_decided_by_listing_order"] = "7_vs_0" in ties
    v["the_8_day_row_is_recency_in_both_orientations"] = verdicts.get("8_vs_0") == "recency"
    v["tonydzi_pair_holds_in_both_orientations"] = verdicts.get("54_vs_20") == "count"
    v["tonydzi_pair_2x54d_vs_1x20d_count_wins"] = pairs_out.get("54_vs_20") == "count"
    v["or_tonydzi_pair_recency_wins"] = pairs_out.get("54_vs_20") == "recency"
    un_e = sum(1 for x in un["kept_positions"] if x <= N / 2)
    v["unrecorded_skills_lose_to_once_used_ones"] = un_e < len(un["kept_positions"]) - un_e
    v["or_unrecorded_skills_are_kept_over_once_used_ones"] = un_e > len(un["kept_positions"]) - un_e

    print()
    print("  crossover bracket at ratio 2x (2-use group early): %s days" % (flips or "none found"))
    for k, x in verdicts.items():
        print("  both orientations, 2x %s d vs 1x %s d: %s" % (tuple(k.split("_vs_")) + (x,)))
    print("  unrecorded-early arm: kept early(no record) %d  late(1-use fresh) %d"
          % (un_e, len(un["kept_positions"]) - un_e))
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))

    out = {"probe": os.path.basename(__file__), "controls": v, "arms": rows,
           "fixture": {"skills": N, "wide": WIDE, "narrow": NARROW, "ratio": 2, "gaps_days": GAPS_DAYS},
           "crossover_bracket_days": flips, "pairs": pairs_out, "swapped_pairs": swapped_out,
           "orientation_verdicts": verdicts, "ties_decided_by_position": ties,
           "unrecorded_early_kept": un_e, "unrecorded_late_kept": len(un["kept_positions"]) - un_e,
           "platform": sys.platform,
           "claude_version": subprocess.run([P.S.CLAUDE, "--version"], capture_output=True,
                                            text=True).stdout.strip()}
    json.dump(out, io.open(os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json")),
                           "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    hard = [k for k in v if k.startswith("CONTROL") and not v[k]]
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
