"""One manifest entry per row id, however many pointers the row carries, enforced on every push.

WHY THIS EXISTS. @pm25coder named the same defect at three layers on anthropics/claude-code#91188
and asked for the invariant to be asserted in CI rather than only inside a trim:

  "assert the row-id-keyed invariant in CI -- one entry per row id per run, pointer count ignored --
   so layer 2 cannot regress into layer 1 the way layer 1 hid until a 15-row case surfaced it."

The three layers are one rule. The move tool addressed LINES, so a shared line dragged its
neighbour. The per-row manifest then addressed POINTERS, so a target linked twice on one line
produced two decisions for one row. The audit was keyed to the section HEADING, so six rows sat
under a heading that hid their decision record. Each time the operation addressed the
representation instead of the domain entity.

The de-dup that fixes layer 2 lives in `demote_rows` and is asserted inside `main()`, which runs
only when a trim runs. A trim runs when the index is over cap, which is occasional. So the
invariant was true and unwatched. This file makes it a standing check, and probes.yml now also
triggers on `tools/**` so editing the tool runs it.

IT CALLS THE REAL FUNCTION. `demote_rows` carries a warning that a probe once reimplemented the
logic it was meant to test, and a sabotage that mislabelled every side-effect row passed that probe
with exit 0 because the probe never ran the code carrying the defect. This imports the shipped
function from tools/trim_memory_index.py.

SEVEN FIXTURES, each an adversarial shape rather than a happy path: a target linked twice inside
one segment; the same target reachable from two segments of one line, and from three; the same
target reachable from two separate lines; a slug that is a prefix of another on the same line,
which is the case the substring reader got wrong; a phantom pointer inside a link label, which must
not become an entry; and two targets on one line, which must give two entries rather than one
merged row.

CONTROLS, AND THE FIRST VERSION GOT THEM WRONG IN A WAY WORTH KEEPING WRITTEN DOWN. Every fixture
is also run through a MUTATED builder that appends per pointer instead of per row id. The first
version then demanded that the mutation break every fixture, reported "1 of 5 mutations caught" and
failed the run. Four of those five have no shape the old builder reads differently: `pointers()`
returns a SET, so a target linked twice inside ONE segment gives one entry either way. The defect
needs the same target reachable from two MOVED rows. So a fixture counts as a mutation target only
where the two builders actually differ, which is measured per fixture rather than assumed, and a
separate control requires at least two fixtures to reach the defect. A suite the old builder reads
identically would otherwise pass while testing nothing, which is the shape this file exists to
stop.
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    from trim_memory_index import ROW_SEP, demote_rows, pointers
except Exception as exc:                              # pragma: no cover
    print("CANNOT RUN: tools/trim_memory_index.py did not import: %s" % exc)
    raise SystemExit(2)

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"


def fixtures():
    """(name, lines, targets, expected_row_ids)."""
    twice = ("- [first look](alpha-row.md) and again [second look](alpha-row.md) in one segment")
    two_segments = ("- [a](alpha-row.md)" + ROW_SEP + "[a again](alpha-row.md)")
    prefix = ("- [short](alpha-row.md)" + ROW_SEP + "[long](alpha-row-extended.md)")
    phantom = ("- [see (ghost.md) note](alpha-row.md)")
    two_targets = ("- [a](alpha-row.md)" + ROW_SEP + "[b](beta-row.md)" + ROW_SEP
                   + "[c](gamma-row.md)")
    three_segments = ("- [a](alpha-row.md)" + ROW_SEP + "[a again](alpha-row.md)" + ROW_SEP
                      + "[a third time](alpha-row.md)")
    across_lines = ["- [a](alpha-row.md)" + ROW_SEP + "[b](beta-row.md)",
                    "- [a elsewhere](alpha-row.md)"]
    return [
        ("one target linked twice inside one segment", [twice], {"alpha-row"}, {"alpha-row"}),
        ("one target linked from two segments", [two_segments], {"alpha-row"}, {"alpha-row"}),
        ("one target linked from three segments", [three_segments], {"alpha-row"}, {"alpha-row"}),
        ("one target reachable from two separate lines", across_lines, {"alpha-row"},
         {"alpha-row"}),
        ("a slug that is a prefix of another on the same line", [prefix], {"alpha-row"},
         {"alpha-row"}),
        ("a phantom pointer inside a link label", [phantom], {"alpha-row"}, {"alpha-row"}),
        ("two targets on one line", [two_targets], {"alpha-row", "beta-row"},
         {"alpha-row", "beta-row"}),
    ]


def entries_per_row(manifest):
    counts = {}
    for m in manifest:
        counts[m["slug"]] = counts.get(m["slug"], 0) + 1
    return counts


def mutated_manifest(lines, targets):
    """The layer-2 regression: one entry per POINTER instead of one per row id.

    This is the builder as it stood before the de-dup, reconstructed here only to prove the check
    can go red. It is never used to produce a reported number.
    """
    from trim_memory_index import move_rows
    manifest = []
    for l in lines:
        _, moved = move_rows(l, targets)
        for row in moved:
            named = sorted(p[:-3] for p in pointers(row) if p[:-3] in targets)
            for p in sorted(pointers(row)):
                manifest.append({"slug": p[:-3],
                                 "decision": "judged" if p[:-3] in targets else "side-effect",
                                 "of": None if p[:-3] in targets else (named[0] if named else None),
                                 "line_carried": sorted(q[:-3] for q in pointers(l))})
    return manifest


def main():
    checks, cases, exercised = [], [], []
    survivors = 0

    for name, lines, targets, want_rows in fixtures():
        _, demoted, manifest, _ = demote_rows(list(lines), set(targets))
        counts = entries_per_row(manifest)
        ids = set(counts)
        one_each = all(n == 1 for n in counts.values())
        rows_right = ids == want_rows

        # THE SAME FIXTURE THROUGH THE OLD BUILDER. Not every fixture can exercise the defect,
        # and the first version of this file scored them as if they all could: it reported "1 of 5
        # mutations caught" and failed, when four of the five simply have no shape the
        # pointer-addressed builder reads differently. `pointers()` returns a SET, so a target
        # linked twice inside ONE segment yields one entry from either builder. The defect needs
        # the same target reachable from two MOVED rows. So a fixture is a mutation target only
        # where the two builders differ, and that is measured rather than assumed.
        mut_counts = entries_per_row(mutated_manifest(list(lines), set(targets)))
        exercises = mut_counts != counts
        mutation_caught = (not exercises) or any(n > 1 for n in mut_counts.values())
        if exercises and not mutation_caught:
            survivors += 1
        if exercises:
            exercised.append(name)

        cases.append({"fixture": name, "entries_per_row": counts,
                      "row_ids": sorted(ids), "expected_row_ids": sorted(want_rows),
                      "pointer_addressed_counts": mut_counts,
                      "exercises_the_defect": exercises})
        checks.append({"check": "ONE_ENTRY_PER_ROW_ID: %s" % name, "pass": one_each,
                       "got": json.dumps(counts, sort_keys=True)})
        checks.append({"check": "THE_ROWS_ARE_THE_RIGHT_ONES: %s" % name, "pass": rows_right,
                       "got": "%s against %s" % (sorted(ids), sorted(want_rows))})
        if exercises:
            checks.append({"check": "CONTROL_THE_POINTER_ADDRESSED_BUILDER_BREAKS_IT: %s" % name,
                           "pass": mutation_caught,
                           "got": json.dumps(mut_counts, sort_keys=True)})

    # A vacuous pass is the failure mode this whole file exists to stop, so the fixture count is
    # asserted rather than trusted.
    checks.append({"check": "CONTROL_THE_SUITE_RAN_ITS_FIXTURES",
                   "pass": len(cases) >= 7,
                   "got": "%d fixtures" % len(cases)})
    # AND AT LEAST TWO OF THEM MUST REACH THE DEFECT. A suite of fixtures the old builder reads
    # identically would pass while testing nothing, which is the shape this file exists to stop.
    checks.append({"check": "CONTROL_AT_LEAST_TWO_FIXTURES_REACH_THE_DEFECT",
                   "pass": len(exercised) >= 2,
                   "got": "%d of %d reach it: %s" % (len(exercised), len(cases), exercised)})

    out = {
        "probe": os.path.basename(__file__),
        "asked_for_by": "pm25coder on anthropics/claude-code#91188",
        "invariant": ("one manifest entry per row id per run, pointer count ignored, asserted "
                      "against the shipped tools/trim_memory_index.demote_rows"),
        "cases": cases,
        "checks": checks,
        "all_passed": all(c["pass"] for c in checks),
        "fixtures_reaching_the_defect": exercised,
        "mutations_caught": len(exercised) - survivors,
        "mutations_run": len(exercised),
        "scope": ("Synthetic index lines only. This asserts the manifest's row-id keying and the "
                  "fixtures that broke it; it says nothing about whether a trim should have "
                  "demoted a given row."),
    }
    with io.open(RESULT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    for c in checks:
        print("  %s  %s" % ("YES" if c["pass"] else "no ", c["check"]))
    print("\n%d of %d mutations caught" % (out["mutations_caught"], out["mutations_run"]))
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
