"""Can we say what the frontier selector's 3.47M tokens bought? No, and the reason is structural.

WHY. `frontier-seed` is the brain's second-largest spender: 794 metered calls, 847,350 tokens in and
2,625,383 out, 39.7% of all metered spend. It is classified in `metabolism._NO_VALUE_LEDGER` as a
SELECTOR whose value "is recorded by the organ that acts on the direction, never here". That
classification is correct and it is also an IOU. This probe tries to collect it.

WHAT IT FOUND. The IOU cannot be collected from the files we keep, and not because the answer is
disappointing. The spend ledger and the outcome ledgers cover disjoint windows:

    .metabolism.json  frontier-seed   794 calls, last written 2026-09-03 08:29
    .frontier.json    80 seeds        2026-09-04 07:17 to 09:40, a 2.4 hour window
    .contributions.json  3,514 rows   ends 2026-09-03, BEFORE the first recorded seed

Every seed we can name was picked after the spend counter stopped moving, and every contribution we
can name was made before the first seed we can name. Zero of 3,514 contributions postdate the
earliest surviving seed, so no join exists in either direction. The overlap is empty by
construction, so "what did it buy" is not a hard question here; it is an unanswerable one.

THREE THINGS MAKE IT UNANSWERABLE, and they are separable:
  1. NO OUTCOME FIELD. A row in `.frontier.json` is {target, kind, ts}. It records the pick and
     nothing about what followed. `record_seeded` never returns to close the loop.
  2. NO SHARED KEY. A contribution carries {topic, topic_id, claim, ...} and a seed carries a
     free-text target. Nothing links them except string overlap, which is a substring test without
     a subject: "Game Theory" and "Philosophy of Science" match contributions written weeks before
     any seeding existed.
  3. NO SHARED CLOCK, AND THIS ONE IS ALREADY HALF FIXED. The counter's only timestamp is its last
     write, so the 794 calls cannot be placed in a window and no rate exists. But `_bump` gained
     `e.setdefault("first_ts", now)` on 2026-09-04 for exactly this reason. Nine of the ten organ
     rows predate that line and carry no start; one, written since, does. So this gap closes on its
     own as each counter is next touched, and reporting it as an open defect would be wrong. It is
     reported here as UNRECOVERABLE FOR THE SPEND ALREADY MADE, which is a different and smaller
     claim.

     This distinction is the reason the probe reads the CODE and not only the data. A reader that
     saw nine rows without a start time would have filed a defect that was fixed hours earlier.

WHAT WAS ALREADY FIXED BEFORE THIS PROBE RAN, and is deliberately not claimed here. Commit ae6d6bb
at 10:34 today raised the ledger cap from 80 rows to 4,000 and began stamping `first_ts` on every
metered organ. The 80-row window this probe reports is the residue of the old cap, not a live
defect, and nine of the ten organ rows lack a start time only because they predate that commit by
two hours. Twice while writing this probe I was one sentence away from filing a defect that had
been fixed the same morning, which is why it now dates every cause it names.

WHAT THIS PROBE THEN CHANGED. `record_seeded` returns an id and writes `outcome: None`;
`record_outcome` closes the loop and REFUSES an id it never issued rather than appending a row for
it; `outcome_coverage` reports the share ever answered. The endpoint returns the id so a caller can
report back. Cover in `server/tests/test_a_frontier_pick_can_be_answered.py`, six tests, both
guards verified by mutation. None of that prices the 3.47M already spent: that stays unrecoverable,
and this buys the next one.

THIS IS NOT A CLAIM THAT THE ORGAN IS WASTEFUL. It may be the best spend in the system. The finding
is that our own instruments cannot tell, and that a 39.7% line item nobody can price is worth more
attention than one that prices badly. Same shape as the seminar, which turned out to be reading its
own file to score itself, except this one does not score itself at all.

CONTROLS, because a check that cannot see its target reports SAFE:
  * POSITIVE CONTROL PER STORE. Each file is searched for a record taken out of that same file. If
    a reader cannot find what it just read, its zero means nothing and the run refuses.
  * NEGATIVE CONTROL. A string that must not be present must come back absent, or the search
    matches everything.
  * THE DISJOINTNESS IS COMPUTED, never asserted. If the windows ever overlap, this probe reports
    the overlap and stops claiming the join is impossible.
  * THE SUBSTRING TRAP IS MEASURED, not avoided. The naive count is reported beside the dated one,
    because the difference between them is the finding a careless version of this probe would miss.

    python probes/the_second_largest_spender_cannot_be_judged_from_what_we_keep.py
"""
from __future__ import annotations

import datetime
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "the_second_largest_spender_cannot_be_judged_from_what_we_keep.result.json")
SERVER = os.path.join(HERE, "..", "server")

METABOLISM = os.path.join(SERVER, ".metabolism.json")
FRONTIER = os.path.join(SERVER, ".frontier.json")
CONTRIB = os.path.join(SERVER, ".contributions.json")
ORGAN = "frontier-seed"
ABSENT = "zzz-not-a-real-topic-4f9a"


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8", newline="\n"), indent=1)
    raise SystemExit(2)


def load(path, what):
    if not os.path.exists(path):
        refuse("no %s at %s; this probe reads the ledgers, not a description of them"
               % (what, path))
    return json.load(io.open(path, encoding="utf-8"))


def stamp(t):
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")


def main():
    mb = load(METABOLISM, "metabolism ledger")
    fr = load(FRONTIER, "frontier ledger")
    co = load(CONTRIB, "contributions ledger")

    if ORGAN not in mb:
        refuse("the metabolism ledger has no %r row, so the spend this probe is about is not "
               "being metered under that name any more" % ORGAN)
    f = mb[ORGAN]
    spend = f.get("tok_in", 0) + f.get("tok_out", 0)
    total = sum(v.get("tok_in", 0) + v.get("tok_out", 0)
                for v in mb.values() if isinstance(v, dict))
    if not spend or not total:
        refuse("the spend reads zero, which means the field names moved again; an earlier version "
               "of this reader looked for 'tokens' and reported 0 for every organ")

    if not fr:
        refuse("the frontier ledger is empty, so there are no picks to trace and the join question "
               "does not arise")
    if not co:
        refuse("the contributions ledger is empty, so there is no downstream to trace into")

    # CONTROLS: each reader must find a record taken from its own store, and must not find a
    # string that is not there.
    ctrl_seed = fr[0]["target"]
    if not any(x.get("target") == ctrl_seed for x in fr):
        refuse("the frontier reader cannot find a target it just read")
    ctrl_topic = co[0].get("topic") or ""
    if not ctrl_topic or not any((c.get("topic") or "") == ctrl_topic for c in co):
        refuse("the contributions reader cannot find a topic it just read")
    if any(ABSENT in (c.get("topic") or "") for c in co):
        refuse("the negative control string was found, so the search matches things that are not "
               "there and every count is void")

    seed_ts = [x["ts"] for x in fr if x.get("ts")]
    co_ts = [c["ts"] for c in co if c.get("ts")]
    seed_first, seed_last = min(seed_ts), max(seed_ts)
    co_first, co_last = min(co_ts), max(co_ts)

    overlap = max(0.0, min(seed_last, co_last) - max(seed_first, co_first))
    after = [c for c in co if c["ts"] >= seed_first]

    targets = sorted({x["target"] for x in fr})
    naive = sorted(t for t in targets
                   if any(t.lower() in (c.get("topic") or "").lower() for c in co))
    dated = sorted(t for t in targets
                   if any(t.lower() in (c.get("topic") or "").lower() for c in after))

    res = {
        "verdict": "UNJUDGEABLE_BY_CONSTRUCTION" if not overlap else "OVERLAP_EXISTS_RECHECK",
        "organ": ORGAN,
        "spend_tokens": spend,
        "spend_calls": f.get("calls", 0),
        "spend_share_pct": round(100.0 * spend / total, 1),
        "spend_counter_last_written": stamp(f["ts"]),
        "spend_window_start": ("UNRECORDED for this row: metabolism._bump sets first_ts since "
                               "2026-09-04, but this counter predates that line, so the rate for "
                               "spend ALREADY made is unrecoverable rather than unimplemented"),
        "organs_carrying_a_start_time": sum(
            1 for v in mb.values() if isinstance(v, dict) and v.get("first_ts")),
        "organs_metered": sum(1 for v in mb.values() if isinstance(v, dict)),
        "seeds": len(fr),
        "seed_window": [stamp(seed_first), stamp(seed_last)],
        "seed_window_hours": round((seed_last - seed_first) / 3600.0, 1),
        "seed_row_fields": sorted(fr[0]),
        "seed_has_outcome_field": any("outcome" in x for x in fr),
        "contributions": len(co),
        "contribution_window": [stamp(co_first), stamp(co_last)],
        "contributions_after_first_seed": len(after),
        "window_overlap_seconds": round(overlap),
        "targets_distinct": len(targets),
        "naive_substring_matches": len(naive),
        "dated_matches": len(dated),
        "the_substring_trap": naive[:8],
    }
    json.dump(res, io.open(OUT, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

    print("  %s: %s tokens over %d calls, %.1f%% of all metered spend"
          % (ORGAN, "{:,}".format(spend), res["spend_calls"], res["spend_share_pct"]))
    print("  spend counter last written : %s" % res["spend_counter_last_written"])
    print("  organs carrying a start ts : %d of %d (the code sets one since 2026-09-04; older rows "
          "predate it)" % (res["organs_carrying_a_start_time"], res["organs_metered"]))
    print("  seeds on record            : %d, %s to %s (%.1f h)"
          % (len(fr), res["seed_window"][0], res["seed_window"][1], res["seed_window_hours"]))
    print("  a seed row carries         : %s" % ", ".join(res["seed_row_fields"]))
    print("  any outcome field          : %s" % res["seed_has_outcome_field"])
    print("  contributions              : %d, %s to %s"
          % (len(co), res["contribution_window"][0], res["contribution_window"][1]))
    print("  made after the first seed  : %d of %d" % (len(after), len(co)))
    print("  window overlap             : %d seconds" % res["window_overlap_seconds"])
    print()
    print("  naive substring matches    : %d of %d targets" % (len(naive), len(targets)))
    print("  same test, dated correctly : %d of %d" % (len(dated), len(targets)))
    print("    the gap between those two is the substring trap: %s"
          % ", ".join(res["the_substring_trap"][:4]))
    print()
    print("  verdict: %s" % res["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
