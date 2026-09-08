"""Replay the 2026-09-04 trim twice, line-addressed and row-addressed, on its real input.

WHY. On 2026-09-04 `tools/trim_memory_index.py` moved a named 32-row list out of MEMORY.md, and 15
rows nobody had judged left with them, because the move selected a line by slug and relocated the
whole line. `NO_POINTER_WAS_LOST` passed: a dragged row does arrive in the archive, so a pointer-set
check cannot see the defect it exists to catch. The 16 are cited by other notes at a median of 3.0
against 0.5 for the 32 the tool judged (permutation p = 0.0068,
probes/packing_the_index_evicted_rows_nobody_judged.py).

@pm25coder separated the two mechanisms on anthropics/claude-code#91188: packing pointers onto one
line to survive a line cap is a layout adaptation, while moving whole lines when rows share them is
a granularity bug. The move has to be row-addressable even when storage is not line-per-row. This
measures the fix against the input that produced the defect, rather than against a fixture.

THE CONTROL THAT MATTERS. The old path must still drag rows on this input. Without it, a run where
the backup stopped carrying shared lines would report a clean fix while measuring nothing.
"""
from __future__ import annotations

import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import trim_memory_index as t  # noqa: E402

PRETRIM = os.path.join(t.MEM, "MEMORY.md.bak-20260904-pretrim")
# The cohort the companion probe measures. Published as 15 in comment 5588661516; a prefix
# filter had hidden a 16th, corrected 2026-09-08. The replay must recover exactly this set.
PUBLISHED_15 = set(json.load(io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "packing_the_index_evicted_rows_nobody_judged.result.json"),
    encoding="utf-8"))["adjacency_slugs"])


def line_addressed(lines, demote):
    """What the tool did before the fix: select by slug, move the LINE."""
    moved, kept = [], []
    for l in lines:
        if any("(" + d + ".md)" in l for d in demote):
            moved.append(l)
        else:
            kept.append(l)
    return kept, moved


def row_addressed(lines, demote):
    """What it does now: select by row id, rewrite the line."""
    moved, kept, manifest = [], [], []
    for l in lines:
        keep_line, rows, dragged = t.move_rows(l, demote)
        for row in rows:
            moved.append(row)
            named = sorted(p[:-3] for p in t.pointers(row) if p[:-3] in demote)
            for p in sorted(t.pointers(row)):
                slug = p[:-3]
                manifest.append({"slug": slug,
                                 "decision": "judged" if slug in demote else "side-effect",
                                 "of": None if slug in demote else (named[0] if named else None)})
        for slug in dragged:
            manifest.append({"slug": slug, "decision": "side-effect", "of": None})
        if keep_line is not None:
            kept.append(keep_line)
    return kept, moved, manifest


def slugs(lines):
    return {p[:-3] for l in lines for p in t.pointers(l)}


def main() -> int:
    t._reader_control()
    t._move_control()
    raw = io.open(PRETRIM, "rb").read().decode("utf-8")
    lines = raw.replace(t.CR + t.NL, t.NL).split(t.NL)
    demote = set(t.DEMOTE)
    before = slugs(lines)

    old_kept, old_moved = line_addressed(lines, demote)
    new_kept, new_moved, manifest = row_addressed(lines, demote)

    old_out, new_out = slugs(old_moved), slugs(new_moved)
    dragged = sorted(old_out - demote)
    side_effects = sorted(m["slug"] for m in manifest if m["decision"] != "judged")

    checks = [
        ("CONTROL_the_input_still_reproduces_the_drag", len(dragged) > 0,
         "%d rows leave under the line-addressed path that nobody judged" % len(dragged)),
        ("CONTROL_the_demote_list_is_reachable_in_this_input", demote <= before,
         "%d of %d targets present" % (len(demote & before), len(demote))),
        ("THE_DRAGGED_SET_IS_THE_ONE_MEASURED_BY_THE_COMPANION_PROBE", set(dragged) == PUBLISHED_15,
         "replay %d, published %d, symmetric difference %s"
         % (len(dragged), len(PUBLISHED_15),
            sorted(set(dragged) ^ PUBLISHED_15) or "none")),
        ("THE_ROW_ADDRESSED_MOVE_TAKES_ONLY_THE_JUDGED", new_out == demote,
         "moved %d, judged %d, extra %s" % (len(new_out), len(demote),
                                            sorted(new_out - demote) or "none")),
        ("EVERY_DRAGGED_ROW_STAYS_IN_THE_INDEX",
         set(dragged) <= slugs(new_kept),
         "%d of %d retained" % (len(set(dragged) & slugs(new_kept)), len(dragged))),
        ("NO_POINTER_WAS_LOST", before <= (slugs(new_kept) | new_out),
         "missing %s" % (sorted(before - (slugs(new_kept) | new_out)) or "none")),
        ("EVERY_ARCHIVED_ROW_HAS_ONE_DECISION",
         sorted(m["slug"] for m in manifest) == sorted(new_out),
         "%d decisions for %d archived rows" % (len(manifest), len(new_out))),
        ("NO_ROW_LEFT_AS_A_SIDE_EFFECT", not side_effects, str(side_effects or "none")),
        ("CONTROL_the_line_addressed_path_would_fail_that_check",
         len(dragged) > 0,
         "the same manifest over the old path carries %d side-effect rows" % len(dragged)),
    ]

    out = {
        "probe": os.path.basename(__file__),
        "input": PRETRIM,
        "index_lines": len(lines),
        "judged_targets": len(demote),
        "line_addressed": {"rows_archived": len(old_out),
                           "unjudged_rows_archived": len(dragged),
                           "dragged": dragged},
        "row_addressed": {"rows_archived": len(new_out),
                          "unjudged_rows_archived": len(side_effects),
                          "index_lines_after": len(new_kept)},
        "checks": [{"check": c, "pass": bool(ok), "got": got} for c, ok, got in checks],
        "all_passed": all(ok for _, ok, _ in checks),
        "finding": ("Replaying the 2026-09-04 trim on its own input, the line-addressed move "
                    "archives %d rows of which %d were never judged, and those %d are exactly the "
                    "set published in comment 5588661516. The row-addressed move archives %d rows, "
                    "all %d of them judged, keeps every dragged row in the index, and loses no "
                    "pointer. Per-row decisions make the difference visible: the old path leaves %d "
                    "rows with no decision of their own, which a pointer-set check cannot see."
                    % (len(old_out), len(dragged), len(dragged), len(new_out), len(demote),
                       len(dragged))),
        "scope": ("One trim, the only one whose pre-trim input was kept. The earlier trims of "
                  "2026-08-26 and 2026-09-08 have no backup of their input here, so this measures "
                  "the fix rather than the historical rate."),
    }
    print(json.dumps(out, indent=1))
    io.open(__file__.replace(".py", ".result.json"), "w",
            encoding="utf-8", newline="\n").write(json.dumps(out, indent=1) + "\n")
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
