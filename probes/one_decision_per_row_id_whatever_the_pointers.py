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

EIGHT FIXTURES, each an adversarial shape rather than a happy path: a target linked twice inside
one segment; the same target reachable from two segments of one line, and from three; the same
target reachable from two separate lines; a slug that is a prefix of another on the same line,
which is the case the substring reader got wrong; a phantom pointer inside a link label, which must
not become an entry; two targets on one line, which must give two entries rather than one merged
row; and an untargeted row dragged out by a targeted one it shares a segment with, which is the
only shape that produces a row labelled "side-effect".

TWO MUTATIONS, BECAUSE THE MANIFEST HAS TWO HALVES. Every fixture runs through a builder that
appends per pointer instead of per row id, which attacks the KEYING. Every fixture also runs
through a sabotage that labels every row "judged", which attacks the LABELS. The second was added
after a verifier applied exactly that sabotage to the shipped function and this file passed with
exit 0: nothing here read `decision` or `of`, and no fixture produced a side-effect row to read.

A fixture counts as a mutation target only where the mutated and real builders actually differ,
measured per fixture rather than assumed, and a control requires at least two to reach the keying
defect and at least one to reach the label sabotage. A suite the mutation reads identically would
otherwise pass while testing nothing, which is the shape this file exists to stop. The first
version of the keying control got this wrong in the other direction: it demanded the mutation break
every fixture, reported "1 of 5 mutations caught" and failed the run. That figure is a self-report,
since the version producing it was never committed. The reason four fixtures do not reach the
keying defect is per-fixture rather than one mechanism: `pointers()` returns a SET, which explains
the twice-in-one-segment case, and the other three agree because each moved row carries exactly one
pointer. The defect needs the same slug reachable from two MOVED rows.
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
    """(name, lines, targets, expected_row_ids, expected_labels).

    `expected_labels` maps each row id to (decision, of). It exists because a verifier sabotaged
    the shipped `demote_rows` to label every row "judged" and this suite passed with exit 0: no
    check read `decision` or `of`, and no fixture produced a side-effect row at all. The suite
    asserted the KEYING and nothing about the LABELS, while paragraph 3 of the reply it supported
    invited a reader to think otherwise.

    A second reader then argued the side-effect path was unreachable after the row-addressed fix,
    which would have made the gap moot. Measured instead of chosen: calling the shipped function on
    a single segment carrying two slugs, one of them targeted, returns beta-row labelled
    "side-effect" with `of` naming alpha-row. It is reachable, so the last fixture below builds it.
    """
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
    dragged = "- [a](alpha-row.md) hook and [b](beta-row.md) hook, one segment"
    judged = ("judged", None)
    return [
        ("one target linked twice inside one segment", [twice], {"alpha-row"}, {"alpha-row"},
         {"alpha-row": judged}),
        ("one target linked from two segments", [two_segments], {"alpha-row"}, {"alpha-row"},
         {"alpha-row": judged}),
        ("one target linked from three segments", [three_segments], {"alpha-row"}, {"alpha-row"},
         {"alpha-row": judged}),
        ("one target reachable from two separate lines", across_lines, {"alpha-row"},
         {"alpha-row"}, {"alpha-row": judged}),
        ("a slug that is a prefix of another on the same line", [prefix], {"alpha-row"},
         {"alpha-row"}, {"alpha-row": judged}),
        ("a phantom pointer inside a link label", [phantom], {"alpha-row"}, {"alpha-row"},
         {"alpha-row": judged}),
        ("two targets on one line", [two_targets], {"alpha-row", "beta-row"},
         {"alpha-row", "beta-row"}, {"alpha-row": judged, "beta-row": judged}),
        ("an untargeted row dragged out by a targeted one it shares a segment with",
         [dragged], {"alpha-row"}, {"alpha-row", "beta-row"},
         {"alpha-row": judged, "beta-row": ("side-effect", "alpha-row")}),
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


def labels_of(manifest):
    """slug -> (decision, of), the half the keying checks never look at."""
    return {m["slug"]: (m.get("decision"), m.get("of")) for m in manifest}


def everything_judged(manifest):
    """The label sabotage: call every row judged, exactly as the defect in `main()` once did.

    Only used to prove the label check can go red. It never produces a reported number.
    """
    return {slug: ("judged", None) for slug in labels_of(manifest)}


def main():
    checks, cases, exercised, label_exercised = [], [], [], []
    survivors = 0
    label_survivors = 0

    for name, lines, targets, want_rows, want_labels in fixtures():
        _, demoted, manifest, _ = demote_rows(list(lines), set(targets))
        counts = entries_per_row(manifest)
        ids = set(counts)
        one_each = all(n == 1 for n in counts.values())
        rows_right = ids == want_rows
        got_labels = labels_of(manifest)
        labels_right = got_labels == want_labels

        # THE LABEL SABOTAGE, and the first attempt at this control could not fail. It asked
        # whether the sabotage differs from what we expect, then called that "caught", which is the
        # same expression twice: the check IS an equality against want_labels, so it catches the
        # sabotage exactly when the sabotage differs. Writing a guard whose two sides are one
        # statement is the defect this file exists to stop, in the file itself.
        #
        # What is actually worth measuring is whether any fixture reaches the sabotage at all. A
        # suite where every row is legitimately judged asserts labels vacuously: mislabelling every
        # row "judged" changes nothing it looks at. So a fixture reaches it only when it expects a
        # row that is NOT judged, and a control below requires at least one.
        sabotaged = everything_judged(manifest)
        if sabotaged != want_labels:
            label_exercised.append(name)

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
                      "labels": {k: list(v) for k, v in sorted(got_labels.items())},
                      "expected_labels": {k: list(v) for k, v in sorted(want_labels.items())},
                      "pointer_addressed_counts": mut_counts,
                      "exercises_the_defect": exercises,
                      "reaches_the_label_sabotage": name in label_exercised})
        checks.append({"check": "ONE_ENTRY_PER_ROW_ID: %s" % name, "pass": one_each,
                       "got": json.dumps(counts, sort_keys=True)})
        checks.append({"check": "THE_ROWS_ARE_THE_RIGHT_ONES: %s" % name, "pass": rows_right,
                       "got": "%s against %s" % (sorted(ids), sorted(want_rows))})
        checks.append({"check": "THE_LABELS_ARE_THE_RIGHT_ONES: %s" % name, "pass": labels_right,
                       "got": "%s against %s" % (sorted(got_labels.items()),
                                                 sorted(want_labels.items()))})
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
    # AND AT LEAST ONE MUST CARRY A ROW THAT IS NOT JUDGED. Without it the label assertion is
    # vacuous: mislabelling every row "judged" would change nothing the suite reads. A verifier
    # sabotaged the shipped function exactly that way and this file passed with exit 0.
    checks.append({"check": "CONTROL_A_FIXTURE_REACHES_THE_LABEL_SABOTAGE",
                   "pass": len(label_exercised) >= 1,
                   "got": "%d of %d reach it: %s" % (len(label_exercised), len(cases),
                                                     label_exercised)})

    out = {
        "probe": os.path.basename(__file__),
        "asked_for_by": "pm25coder on anthropics/claude-code#91188",
        "invariant": ("one manifest entry per row id per run, pointer count ignored, asserted "
                      "against the shipped tools/trim_memory_index.demote_rows"),
        "cases": cases,
        "checks": checks,
        "all_passed": all(c["pass"] for c in checks),
        "fixtures_reaching_the_defect": exercised,
        "fixtures_reaching_the_label_sabotage": label_exercised,
        "mutations_caught": len(exercised) - survivors,
        "mutations_run": len(exercised),
        "scope": ("Synthetic index lines only. This asserts the manifest's row-id keying AND the "
                  "decision labels, each against a mutation that could break it; it says nothing "
                  "about whether a trim should have demoted a given row in the first place."),
    }
    with io.open(RESULT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    for c in checks:
        print("  %s  %s" % ("YES" if c["pass"] else "no ", c["check"]))
    print("\n%d of %d mutations caught" % (out["mutations_caught"], out["mutations_run"]))
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
