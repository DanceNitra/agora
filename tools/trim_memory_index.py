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
POINTER = re.compile(r"\(([A-Za-z0-9._\-]+\.md)\)")


def pointers(t: str) -> set:
    return set(POINTER.findall(t))


def _reader_control() -> None:
    """The pointer reader must see a mixed-case pointer, or every set comparison below is void."""
    probe = "- [x](a-lower-case.md) and [y](cascade-fidelity-B-killed-at-gate.md)"
    seen = pointers(probe)
    if seen != {"a-lower-case.md", "cascade-fidelity-B-killed-at-gate.md"}:
        raise SystemExit("REFUSED: the pointer reader saw %r, so it cannot see every pointer and "
                         "NO_POINTER_WAS_LOST would pass a trim that lost one" % sorted(seen))


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
    demoted, kept, seen = [], [], set()
    for l in lines:
        slug = next((d for d in DEMOTE if "(" + d + ".md)" in l), None)
        if slug:
            demoted.append(l)
            seen.add(slug)
            continue
        kept.append(l)
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
    # Seven spare lines is about a week of entries at the current rate, which is the point:
    # enough that the cut does not silently return before anyone looks again.
    v["headroom_is_a_week_not_a_day"] = (
        after["lines"] <= LINE_CAP - 5 and after["units"] <= UNIT_CAP - 800)

    print("            lines   units  delivered")
    print("  before  %7d %7d %10d" % (before["lines"], before["units"], before["delivered"]))
    print("  after   %7d %7d %10d" % (after["lines"], after["units"], after["delivered"]))
    print("  demoted %7d entries -> MEMORY_ARCHIVE.md" % len(demoted))
    print("  duplicate pointers still present: %s" % (dup or "none"))
    print()
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))

    if not all(v.values()):
        print("\nREFUSED: not writing. Fix the trim, not the check.")
        return 1
    if "--write" not in sys.argv:
        print("\n  dry run. Pass --write to apply.")
        return 0

    io.open(ARCHIVE, "w", encoding="utf-8", newline="").write(arch_new)
    io.open(INDEX, "wb").write(new.encode("utf-8"))   # `new` already carries its terminators
    print("\n  written. Re-measure with the same command to confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
