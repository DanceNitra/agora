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
# The cohort, pinned as a LITERAL. This used to read the set out of the sibling probe's
# .result.json, which that probe rewrites on every run -- so the check compared two live
# constructions and its name ("the published set") described neither. Published as 15 in comment
# 5588661516; a prefix filter had hidden the 16th, corrected 2026-09-08.
COHORT_16 = {
    "adaptation-corruption-separation-law-breaktruth",
    "agent-memory-integrity-leaderboard",
    "agora-defensible-edge-ai-claim-crucible",
    "agora-seminar",
    "breaktruth-candidates-liveness-replay-and-behavior-integrity",
    "campaign-poison-defense-capability-gradient",
    "consolidation-gate-coupling-breaktruth",
    "crucible-ragdead-longcontext-probe",
    "diversity-flip-law-breakthrough",
    "erasure-selfcheck-tool-published",
    "frontier-generativity-predictability-ceiling",
    "gate-decorrelation-adversary-controlled",
    "graphshift-orthogonal-gate-poison-defense",
    "memorygraft-crucible-candidate",
    "ramr-benchmark-published",
    "seo-program-setup",
}


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
    """What it does now. Calls the SHIPPED path, never a copy of it.

    This used to reimplement the manifest loop. A sabotage that mislabelled every side-effect row
    as "judged" inside the real `main()` then passed this probe with exit 0, because the probe never
    ran the code carrying the defect.
    """
    kept, moved, manifest, _seen = t.demote_rows(lines, demote)
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

    # Run the SHIPPED manifest builder over a line-addressed move, by swapping move_rows for the
    # pre-fix behaviour. Restored in a finally, so a failure here cannot leave the module mutated.
    real_move = t.move_rows
    try:
        def line_move(line, targets):
            if any("(" + x + ".md)" in line for x in targets):
                return None, [line]
            return line, []
        t.move_rows = line_move
        _k, _d, mman, _s = t.demote_rows(lines, demote)
    finally:
        t.move_rows = real_move
    if t.move_rows is not real_move:
        raise SystemExit("REFUSED: the mutation was not undone")
    mutated = {"side_effect": sorted(m["slug"] for m in mman if m["decision"] == "side-effect"),
               "of": {m["slug"]: m["of"] for m in mman}}
    dragged = sorted(old_out - demote)
    side_effects = sorted(m["slug"] for m in manifest if m["decision"] != "judged")

    checks = [
        ("CONTROL_the_input_still_reproduces_the_drag", len(dragged) > 0,
         "%d rows leave under the line-addressed path that nobody judged" % len(dragged)),
        ("CONTROL_the_demote_list_is_reachable_in_this_input", demote <= before,
         "%d of %d targets present" % (len(demote & before), len(demote))),
        ("THE_DRAGGED_SET_IS_THE_PINNED_COHORT", set(dragged) == COHORT_16,
         "replay %d, published %d, symmetric difference %s"
         % (len(dragged), len(COHORT_16),
            sorted(set(dragged) ^ COHORT_16) or "none")),
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
        # MUTATION CONTROL. Revert move_rows to the line-addressed behaviour and require the
        # SHIPPED manifest builder to label the 16 as side-effect. This replaces two things that
        # could not fail: a second check asserting `len(dragged) > 0` under a new name, and an
        # assertion that no row was a side-effect, made against a code path with no reachable
        # producer of that label.
        ("MUTATION_the_shipped_manifest_labels_16_rows_side_effect_under_the_old_move",
         mutated["side_effect"] == dragged,
         "%d side-effect entries, naming %s"
         % (len(mutated["side_effect"]), "the same 16" if mutated["side_effect"] == dragged
            else mutated["side_effect"][:3])),
        ("MUTATION_and_every_one_names_the_row_it_left_with",
         all(mutated["of"].get(x) in demote for x in mutated["side_effect"]),
         "each side-effect entry carries the judged row that took it"),
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
