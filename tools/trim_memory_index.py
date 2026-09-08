"""Trim MEMORY.md back inside the loader window, and prove nothing was lost doing it.

WHY. Measured today: 216 lines, 26,016 UTF-16 units. The loader keeps min(200 lines, 25,000 units),
whole-line, CR counted, so the cut lands at line 201 and SIXTEEN lines are outside the window --
including the whole "Infra / ops" section and the architecture pointers. The index that tells this
session what it knows has been silently dropping its own tail, which is the exact failure we have
been writing about in anthropics/claude-code#82056 all week.

WHICH CAP BINDS decides the remedy, and here it is the LINE cap: 26,016 over 216 lines is 120 units
per line, under the ~125 crossover, so the file runs out of lines before it runs out of size.
Shortening hooks would therefore buy nothing. Lines have to go.

AND PACKING IS THE WRONG LEVER. It is free against the line cap to put two pointers on one line, and
we measured that it costs retrieval: recall@3 0.325 un-crowded against 0.208 crowded, with co-tenancy
rather than hook length as the cause. So this moves whole entries OUT to MEMORY_ARCHIVE.md rather
than merging them onto shared lines.

WHAT LEAVES, and the criterion is stated so it can be argued with: entries that record a ONE-OFF
domain result (a specific EDRN degeneracy, a LOCOMO ceiling, an inspeximus internal) rather than a
cross-cutting working rule. Everything about gates, sending, measurement discipline and the index
itself stays, because those fire on unrelated work. The safety block stays where it is.

THE CHECK THAT MATTERS. A trim is a deletion, so the only interesting question is whether anything
was really deleted. This compares POINTER SETS, not counts: every pointer in the old index must be
present in the new index or in the archive. Counting would pass a trim that dropped one entry and
added another, which is how three pointers went missing here on 2026-08-25.
"""
from __future__ import annotations

import io
import os
import re
import sys

MEM = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                   "C--Users-Danculus-agora", "memory")
INDEX = os.path.join(MEM, "MEMORY.md")
ARCHIVE = os.path.join(MEM, "MEMORY_ARCHIVE.md")
MANIFEST = os.path.join(MEM, "MEMORY_ARCHIVE_MANIFEST.jsonl")
LINE_CAP, UNIT_CAP = 200, 25000
NL = chr(10)
CR = chr(13)

# Slugs demoted out of the index. Named by slug, not by line number, so re-running after an
# edit cannot demote whatever happens to sit at that offset. One slug per LINE is enough: a line
# carrying two pointers moves whole, and both land in the archive.
#
# 2026-09-04 list. The 2026-08-26 list is gone from the index, so the tool refused with all 19
# targets missing, which is the check working. The criterion is unchanged: a ONE-OFF domain result
# leaves, a cross-cutting working rule stays.
#
# WHAT THE CUT WAS COSTING TODAY. At 224 lines the loader delivered 189, so the whole
# "Collaborations / projects" and "Infra / ops" sections never reached a session, including the
# live Marat and EDRN pointers and `claude-inbox-pending-field`, the .pending gotcha CLAUDE.md
# calls out by name. Eleven "Benchmarks / laws" lines were already outside the window, so moving
# those to the archive costs nothing that was arriving.
DEMOTE = [
    # Recent / open: settled one-off results. The EDRN and TAT rules that still bind live in the
    # Collaborations section and in the files themselves.
    "the-threshold-that-made-a-notice-immortal",
    "the-biggest-spender-was-scoring-itself",
    "a-real-rotation-cannot-reach-a-complex-manifold",
    "the-file-we-dismissed-was-the-correct-method",
    "the-grid-we-told-him-to-use-produced-none-of-his-numbers",
    "awesome-ai-agents-merged-limitations-were-the-reason",
    "i-burned-a-session-on-agents-instead-of-asking-for-a-file",
    "the-registry-did-not-contain-the-field-the-task-assumed",
    "meta-sha-is-wasgeneratedby-not-wasderivedfrom",
    "a-hung-xdist-worker-has-no-pytest-in-its-name",
    "erasure-verification-is-a-market-someone-already-sells",
    "a-gate-can-measure-the-machine-not-the-code",
    "zero-of-24-surfaces-demonstrated",
    "our-pypi-downloads-are-not-people",
    # Benchmarks / laws: every one of these was already past the cut and reaching nobody.
    "prediction-ledger-is-reliably-worse-than-chance",
    "ramr-integrity-conditioned-recall-metric",
    "adversarial-conflict-the-real-inspeximus-moat",
    "separability-ceiling-synthesis",
    "scarce-memory-eviction-regime-law",
    "replication-prediction-program",
    "two-channel-freshness-poison-pareto",
    "layer2-veracity-frontier-to-bedrock",
    "grounding-meter-capstone",
    "cascade-fidelity-B-killed-at-gate",
    "match-organ-is-cost-of-rigor-not-leak",
    # Collaborations: stale project pointers. Marat, EDRN, HOTRG and the arXiv rule stay.
    "kgai-converged-on-our-design-and-has-the-two-things-we-lack",
    "adk-docs-open-but-maturity-gated",
    "folklore-index-hf-published",
    "agent-memory-observatory-frontier",
    "ramr-outreach-candidates",
    "github-pages-root-robots-and-indexing",
    "agora-idea-forge",
]

HEADER = [
    "# Memory Index",
    "",
    ("_One line per memory; detail is in the linked file. \"Standing rules\" is PERMANENT. "
     "Loader keeps min(200 lines, 25,000 UTF-16 units), whole-line, CR counted; "
     "`probes/what_our_own_index_actually_delivers.py` measures what actually arrives. "
     "Older entries: **[MEMORY_ARCHIVE.md](MEMORY_ARCHIVE.md)**._"),
    "",
]


EOL = NL          # set from the file being trimmed; every measurement below uses it


def units(t: str) -> int:
    return len(t.encode("utf-16-le")) // 2


def as_written(lines: list) -> str:
    """The exact text that will land on disk, terminators included. Measure THIS, never a
    normalised copy: an earlier version stripped the CRs, measured 25,804 for a 26,016-unit file,
    and would have reported headroom it did not have."""
    return EOL.join(lines) + EOL


# CORRECTED 2026-09-04. This used to read `[a-z0-9\-]+`, which is blind to any slug carrying an
# uppercase letter: `cascade-fidelity-B-killed-at-gate.md` and
# `competitors-CAN-erase-revert-inspeximus-moat-is-determinism.md` were both invisible to it. The
# pointer-set comparison is the one check that makes this tool safe to run, so a reader that cannot
# see a pointer would have passed a trim that deleted it. Caught by the check refusing its own run.
# CORRECTED AGAIN 2026-09-08: it matched ANY parenthesised name, so a label containing a
# parenthesis made a phantom pointer. In `[see (foo.md) note](real.md)` it read `foo.md`,
# and demoting `foo` then swept out the unrelated `real.md` on the same line. A pointer is
# the target of a markdown link, so the `](` is required.
POINTER = re.compile(r"\]\(([A-Za-z0-9._\-]+\.md)\)")


def pointers(t: str) -> set:
    return set(POINTER.findall(t))


def _reader_control() -> None:
    """The pointer reader must see a mixed-case pointer, or every set comparison below is void."""
    probe = ("- [x](a-lower-case.md) and [y](cascade-fidelity-B-killed-at-gate.md)"
             + ROW_SEP + "[see (phantom.md) note](real.md)")
    seen = pointers(probe)
    want = {"a-lower-case.md", "cascade-fidelity-B-killed-at-gate.md", "real.md"}
    if seen != want:
        raise SystemExit("REFUSED: the pointer reader saw %r, wanted %r. Missing a pointer makes "
                         "NO_POINTER_WAS_LOST pass a trim that lost one; an extra one makes the "
                         "move sweep out an unrelated row." % (sorted(seen), sorted(want)))


# --- ROW-ADDRESSABLE MOVE -----------------------------------------------------------------------
# Storage here is not line-per-row: a line can carry several pointers separated by ROW_SEP. The
# move below addresses ROW IDS and rewrites the line, instead of relocating the line whole.
#
# WHY THIS CHANGED. The previous loop selected a line by slug and appended the WHOLE line, so a row
# sharing a line with a demoted neighbour left with it. On 2026-09-04 that moved 15 rows nobody had
# judged. NO_POINTER_WAS_LOST could not see it: the dragged row does arrive in the archive, so a
# pointer-set check passes on a move that nobody decided. The 15 are cited by other notes at a
# median of 3.0, against 0.5 for the 32 the tool judged, so they resemble the rows that stayed.
# Reported by @pm25coder on anthropics/claude-code#91188: the fix is the row-addressable move, not
# the layout.
ROW_SEP = " " + chr(183) + " "
LIST_PREFIX = re.compile(r"^(\s*[-*]\s+)(.*)$")


def split_rows(line: str):
    """(list prefix, [row segments]) for an index line, or (None, None) if it is not one."""
    m = LIST_PREFIX.match(line)
    if not m:
        return None, None
    return m.group(1), m.group(2).split(ROW_SEP)


def move_rows(line: str, targets):
    """Move only the named rows off `line`.

    Returns (kept_line_or_None, [moved_row_lines]).

    THERE IS NO THIRD "dragged" RETURN, and there was: it was provably always empty. Reaching it
    required the remainder to carry no pointer, and it was built from exactly those pointers. A
    check asserting no row was dragged therefore could not fail, and the manifest's "side-effect"
    vocabulary had no reachable producer. Dead code that looks like a safety net is worse than no
    safety net. Side-effect labels are produced by the LINE-addressed path, which is what the
    replay probe mutates in to prove the manifest can emit them.
    """
    prefix, segs = split_rows(line)
    if segs is None:
        return line, []
    # By PARSED pointer, never by substring. A substring test matched a phantom inside a label,
    # and it also matched a slug that is a prefix of a longer one on the same line.
    want = set(targets)
    hit = [i for i, s in enumerate(segs) if {p[:-3] for p in pointers(s)} & want]
    if not hit:
        return line, []
    rest = [s for i, s in enumerate(segs) if i not in hit]
    moved = [prefix + segs[i] for i in hit]
    if rest and any(POINTER.search(s) for s in rest):
        return prefix + ROW_SEP.join(rest), moved
    # Nothing pointer-bearing survives, so the whole line leaves, residue included.
    return None, moved + ([prefix + ROW_SEP.join(rest)] if rest else [])


def demote_rows(lines, targets):
    """Move `targets` off their lines and record one decision per row that leaves.

    THE WHOLE PATH, in one function, so a probe can exercise what SHIPS. It used to live inline in
    `main()` and a probe reimplemented it to test it; a sabotage that mislabelled every side-effect
    row as "judged" in `main()` then passed that probe with exit 0, because the probe never ran the
    code carrying the defect.

    Returns (kept_lines, demoted_rows, manifest, slugs_seen).
    """
    kept, demoted, manifest, seen = [], [], [], set()
    by_slug = set()

    def record(slug, named, source_line):
        # ONE ENTRY PER SLUG. The manifest is keyed by row id, and the same target can be linked
        # from two segments of one line, which produced two entries for one row. A second entry is
        # not a second decision.
        #
        # NO COUNT HERE ANY MORE, and the reason is worse than the arithmetic. This said "a fuzz
        # run produced 227 double entries". The harness partitioned 227 lines carrying the shape
        # from 34 that reached a double entry, so the figure was wrong on its own terms. Then a
        # verify pass ran the harness against this tree and it raised ValueError: it unpacks three
        # values from move_rows, which returns two here and on origin/main. So both counts were
        # measured against a move_rows that exists in neither tree. The shape is real and the
        # de-dup above is the fix; the numbers were about nothing.
        if slug in by_slug:
            return
        by_slug.add(slug)
        manifest.append({
            "slug": slug,
            "decision": "judged" if slug in targets else "side-effect",
            "of": None if slug in targets else (named[0] if named else None),
            "line_carried": sorted(q[:-3] for q in pointers(source_line)),
        })

    for l in lines:
        keep_line, moved = move_rows(l, targets)
        for row in moved:
            demoted.append(row)
            named = sorted(p[:-3] for p in pointers(row) if p[:-3] in targets)
            seen.update(named)
            for p in sorted(pointers(row)):
                record(p[:-3], named, l)
        if keep_line is not None:
            kept.append(keep_line)
    return kept, demoted, manifest, seen


def _move_control() -> None:
    """The move must leave a neighbour behind, and the fixture must still reproduce the drag.

    Two assertions, because either one alone is worthless. The first says the fix works. The second
    says the fixture is still a case the old behaviour got wrong -- without it, a fixture that
    stopped carrying two rows would let the first assertion pass while measuring nothing.
    """
    shared = "- [A](judged-row.md) - hook one" + ROW_SEP + "[B](neighbour-row.md) - hook two"
    kept, moved = move_rows(shared, ["judged-row"])
    if kept is None or "neighbour-row.md" not in kept:
        raise SystemExit("REFUSED: the move dropped the neighbour, so it is still line-addressed")
    if len(moved) != 1 or "judged-row.md" not in moved[0] or "neighbour-row.md" in moved[0]:
        raise SystemExit("REFUSED: the move carried the wrong rows: %r" % (moved,))
    # CONTROL, and it must run through move_rows or it proves nothing. The first version compared
    # two string literals defined two lines apart, referenced neither move_rows nor DEMOTE, and so
    # could not fail for ANY change to the code it was guarding.
    #
    # The property: the fixture carries two rows on one line, so a LINE-addressed move would take
    # both. Asserted by asking move_rows for the union of what leaves and what stays, and requiring
    # it to be the whole line -- which is only interesting because the two are different objects.
    if len(split_rows(shared)[1]) < 2:
        raise SystemExit("REFUSED: the fixture no longer carries two rows on one line, so the "
                         "assertions above cannot distinguish a row move from a line move")
    both = pointers(kept) | {p for m in moved for p in pointers(m)}
    if both != pointers(shared):
        raise SystemExit("REFUSED: move_rows lost or invented a pointer: %r vs %r"
                         % (sorted(both), sorted(pointers(shared))))
    # A slug that is a strict PREFIX of its neighbour must not drag it.
    pre = "- [A](row.md) hook" + ROW_SEP + "[B](row-extended.md) hook"
    k2, m2 = move_rows(pre, ["row"])
    if k2 is None or "row-extended.md" not in k2 or len(m2) != 1:
        raise SystemExit("REFUSED: a prefix slug dragged its neighbour: kept=%r moved=%r" % (k2, m2))
    # A phantom pointer inside a label must not select the row.
    ph = "- [see (phantom.md) note](real.md) hook"
    k3, m3 = move_rows(ph, ["phantom"])
    if m3:
        raise SystemExit("REFUSED: a parenthesis in a label selected a row: %r" % (m3,))


def window(lines: list) -> int:
    """The number of lines the loader actually delivers."""
    acc = 0
    size_cut = None
    for i, l in enumerate(lines, 1):
        acc += units(l + EOL)
        if acc > UNIT_CAP:
            size_cut = i
            break
    line_cut = LINE_CAP + 1 if len(lines) > LINE_CAP else None
    cuts = [c for c in (size_cut, line_cut) if c]
    return (min(cuts) - 1) if cuts else len(lines)


def main() -> int:
    global EOL
    _reader_control()
    _move_control()
    raw = io.open(INDEX, "rb").read().decode("utf-8")     # binary: text mode eats the CRs
    crlf = CR + NL in raw
    EOL = (CR + NL) if crlf else NL
    lines = raw.replace(CR + NL, NL).split(NL)
    while lines and lines[-1] == "":
        lines.pop()
    # `before` measures the RAW file, not a reconstruction of it, so the two numbers printed
    # side by side are the same kind of thing.
    before = {"lines": len(lines), "units": units(raw),
              "delivered": window(lines), "pointers": pointers(NL.join(lines))}

    # --- 1. demote the named entries -------------------------------------------------------------
    kept, demoted, manifest, seen = demote_rows(lines, DEMOTE)
    missing = [d for d in DEMOTE if d not in seen]
    if missing:
        raise SystemExit("REFUSED: %d demote targets are not in the index, so the trim is aimed at "
                         "an index that no longer exists: %s" % (len(missing), missing))

    # --- 2. structural waste: the header, and every doubled blank ---------------------------------
    body = kept[kept.index("## Recent / open"):] if "## Recent / open" in kept else kept
    out, prev_blank = list(HEADER), True
    for l in body:
        blank = not l.strip()
        if blank and prev_blank:
            continue                       # a run of blanks costs lines and delivers nothing
        out.append(l)
        prev_blank = blank
    while out and not out[-1].strip():
        out.pop()

    # --- 3. one pointer appears twice; the second copy is dead weight -----------------------------
    dup = [p for p in before["pointers"]
           if NL.join(out).count("(" + p + ")") > 1]

    new = as_written(out)
    after = {"lines": len(out), "units": units(new), "delivered": window(out),
             "pointers": pointers(new)}

    # --- 4. append the demoted entries to the archive ----------------------------------------------
    arch = io.open(ARCHIVE, "rb").read().decode("utf-8") if os.path.exists(ARCHIVE) else ""
    add = (NL + "## Demoted from the index 2026-09-04, to fit the loader window" + NL + NL
           + NL.join(demoted) + NL)
    arch_new = arch.rstrip(NL) + NL + add

    # --- 5. the checks ------------------------------------------------------------------------------
    v = {}
    v["THE_INDEX_NOW_FITS_THE_LINE_CAP"] = after["lines"] <= LINE_CAP
    v["THE_INDEX_NOW_FITS_THE_UNIT_CAP"] = after["units"] <= UNIT_CAP
    v["EVERY_LINE_IS_NOW_DELIVERED"] = after["delivered"] == after["lines"]
    v["CONTROL_it_did_not_before"] = before["delivered"] < before["lines"]
    # SETS, not counts. A count would pass a trim that dropped one entry and added another.
    v["NO_POINTER_WAS_LOST"] = before["pointers"] <= (after["pointers"] | pointers(arch_new))
    v["THE_DEMOTED_ONES_REALLY_LEFT_THE_INDEX"] = not (
        {d + ".md" for d in DEMOTE} & after["pointers"])
    v["AND_REALLY_ARRIVED_IN_THE_ARCHIVE"] = (
        {d + ".md" for d in DEMOTE} <= pointers(arch_new))
    v["the_safety_block_is_still_delivered"] = "vault-push-ntfs-gotcha.md" in NL.join(
        out[:after["delivered"]])
    v["the_standing_rules_heading_survives"] = "## Standing rules" in new
    # PER-ROW ACCOUNTING. Every row that leaves carries one decision of its own. A pointer-set
    # check cannot see a row that left by adjacency, because that row does arrive in the archive.
    v["EVERY_ARCHIVED_ROW_HAS_ONE_DECISION"] = (
        sorted(m["slug"] for m in manifest)
        == sorted({p[:-3] for l in demoted for p in pointers(l)}))
    v["NO_ROW_LEFT_AS_A_SIDE_EFFECT"] = not [m for m in manifest
                                             if m["decision"] != "judged"]
    # Proved by MUTATION in probes/a_move_that_addresses_rows_must_not_drag_the_line.py: running
    # the same manifest builder over a line-addressed move produces 16 side-effect entries on the
    # real 2026-09-04 input. Asserting it here from the row-addressed path could not fail.
    # Seven spare lines is about a week of entries at the current rate, which is the point:
    # enough that the cut does not silently return before anyone looks again.
    v["headroom_is_a_week_not_a_day"] = (
        after["lines"] <= LINE_CAP - 5 and after["units"] <= UNIT_CAP - 800)

    print("            lines   units  delivered")
    print("  before  %7d %7d %10d" % (before["lines"], before["units"], before["delivered"]))
    print("  after   %7d %7d %10d" % (after["lines"], after["units"], after["delivered"]))
    print("  demoted %7d entries -> MEMORY_ARCHIVE.md" % len(demoted))
    print("  duplicate pointers still present: %s" % (dup or "none"))
    print("  per-row decisions: %s" % ", ".join(
        "%s=%d" % (d, sum(1 for m in manifest if m["decision"] == d))
        for d in sorted({m["decision"] for m in manifest})) or "none")
    print()
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))

    if not all(v.values()):
        print("\nREFUSED: not writing. Fix the trim, not the check.")
        return 1
    if "--write" not in sys.argv:
        print("\n  dry run. Pass --write to apply.")
        return 0

    # BACK UP THE STATE BEING REPLACED, because a trim is a deletion and the file it deletes is a
    # data point. Measured 2026-09-04: this tool cut 224 lines to 190 and kept no copy, so the only
    # record of the pre-trim state was a scratchpad file that dies with the session. Every OTHER
    # writer of this index leaves a `MEMORY.md.bak-*`, which is what makes the 25-snapshot series
    # measurable at all; this one was the gap in it.
    import shutil as _shutil
    stamp = __import__("datetime").datetime.now().strftime("%Y%m%d-%H%M%S")
    _shutil.copy2(INDEX, os.path.join(MEM, "MEMORY.md.bak-%s-pretrim" % stamp))

    # THE MANIFEST. One record per row that left, with its own decision, so a row that leaves
    # without one is findable by audit instead of invisible. Appended, never rewritten.
    import json as _json
    with io.open(MANIFEST, "a", encoding="utf-8", newline="") as fh:
        for m in manifest:
            fh.write(_json.dumps(dict(m, trim=stamp), sort_keys=True) + NL)

    io.open(ARCHIVE, "w", encoding="utf-8", newline="").write(arch_new)
    io.open(INDEX, "wb").write(new.encode("utf-8"))   # `new` already carries its terminators
    print("\n  written. Re-measure with the same command to confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
