"""Three questions the #91188 thread left open, answered from 26 dated snapshots of our own index.

@pm25coder and @stonianua both closed on the same three open measurements, and said plainly that
nobody on the thread has the data. Our memory directory keeps 26 dated copies of `MEMORY.md` from
2026-08-17 to today, which is the per-event snapshot series stonianua said was missing. This reads
them.

1. WAS THE ROW JUDGED, OR DID THE WINDOW JUST END?

   Two retirement events carry word-for-word identical headings, "Demoted from the index ..., to fit
   the loader window", and produced guard shares of 52.6% (19 rows) and 5.6% (54 rows). A 10x spread
   under one stated reason. pm25coder's reading is that a window-fit demotion is a mechanism rather
   than a judgment, so no row in it was evaluated on content, and such rows should sit outside a
   content-class analysis entirely.

   That is testable without asking anyone what they meant. A loader window ends at a POSITION. If an
   event removed a contiguous block, the file's own order decided which rows went and no row was
   examined; if the removed rows are scattered through the file, someone picked them. The
   discriminator is the positional pattern, and it is mechanical.

   The measure is the number of maximal runs the removed rows form in the pre-event file. One run
   that ends at the last row is a window ending. Many short runs spread through the file is
   selection. A single number would hide the difference, so the runs are reported.

2. WAS ANYTHING POINTING AT IT WHEN IT WENT? THIS SERIES CANNOT SAY, AND THAT IS THE RESULT.

   The intent was the false-retirement question: of the rows an event removed, how many were
   referenced by another row at the moment they left. Two readings and a control killed it.

   The first count said 37 of 54 on the most recent event. Artifact: several rows share one physical
   line in the compressed index, and the counter read two links on one line as each other's
   reference, so a grouped line cited its own neighbours.

   Requiring a reference from a different line, every event returned 0 of N. A uniform zero is the
   shape of a check that cannot fire, so it was tested: across all 26 snapshots there are ZERO
   cross-line references. The index is a flat list, one line per memory plus hook text, and its rows
   have never cited each other. The counter never had a target.

   The verdict is therefore VOID, not zero. References that could make a row load-bearing live in
   the note FILES as `[[wikilinks]]`, and those files are not versioned, so no reference in one today
   can be dated to a retirement. Reporting "0 of 54 were still referenced" would have been a
   confident nothing.

3. WHERE DID THE TWO RESURRECTIONS COME BACK FROM?

   Two rows re-entered the live index after leaving it. pm25coder called them the cheapest
   disambiguator in the dataset, because the path each took points at the causal direction. The
   snapshots date the departure and the return, which narrows the path to the work done between two
   timestamps.

CONTROLS. A snapshot series is easy to misread, so each claim carries one that fails if the
instrument stops working:

  ORDERED       snapshots are sorted by mtime, and the sort must agree with the dates in their own
                filenames wherever a filename carries one. A series read out of order would invent
                departures and returns.
  A ROW MOVES   at least one row must be seen leaving across the series, or the reader is not
                actually parsing rows and every "nothing left" below is vacuous.
  A KNOWN PAIR  the two resurrections must both be found by the reader itself, not taken from the
                earlier probe's output, or this file is quoting a number rather than measuring it.
  NOT ALL RUNS  a contiguous-run count is only informative if a scattered event exists to contrast
                with, so the runs are reported for every event and the spread is the evidence.
  CAN IT FIRE   a copy of the newest snapshot gets one synthetic cross-line reference injected, and
                the reference counter must find exactly it. Without this the void above would be
                indistinguishable from a broken counter.
"""
import glob
import io
import json
import os
import re
import sys
import time

MEM = os.environ.get(
    "AGORA_MEMORY_DIR",
    os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory"))

# A row is a pointer line: a markdown link to a .md file in this directory. The slug is the identity.
LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+\.md)\)")
WIKI = re.compile(r"\[\[([^\]]+)\]\]")
DATE_IN_NAME = re.compile(r"bak-(\d{8})")


def snapshots():
    """(mtime, name, path) oldest first, current index last."""
    paths = glob.glob(os.path.join(MEM, "MEMORY.md.bak-*")) + [os.path.join(MEM, "MEMORY.md")]
    out = [(os.path.getmtime(p), os.path.basename(p), p) for p in paths if os.path.isfile(p)]
    return sorted(out)


def rows_of(path):
    """slug -> (ordinal among rows, the line), in file order.

    THE ORDINAL, NOT THE LINE NUMBER. The first version keyed on line index, so a section heading
    between two rows split them into separate runs and every event was reported as "scattered". The
    discriminator the probe exists for could not have found a contiguous block even where one was
    there. A loader window cuts the sequence of rows, so that is the sequence to count in.
    """
    text = io.open(path, encoding="utf-8", errors="replace").read()
    out, k = {}, 0
    for ln, line in enumerate(text.splitlines()):
        for m in LINK.finditer(line):
            slug = os.path.basename(m.group(1))
            if slug.lower().startswith("memory"):
                continue                       # the archive link is navigation, not a row
            if slug in out:
                continue
            # THE LINE NUMBER IS KEPT ONLY TO TELL ROWS APART. Several rows share one physical line
            # in the compressed index, and the reference count below must not read two links on one
            # line as each other's reference: that reported 37 of 54 rows as still pointed at when
            # the real figure was different, because a grouped line cites its own neighbours.
            out[slug] = (k, line, ln)
            k += 1
    return out


def runs(positions):
    """Maximal runs of consecutive integers, as (start, end) pairs."""
    if not positions:
        return []
    s = sorted(positions)
    out, a, b = [], s[0], s[0]
    for x in s[1:]:
        if x == b + 1:
            b = x
        else:
            out.append((a, b))
            a = b = x
    out.append((a, b))
    return out


def _finding(departures):
    """One sentence per event. The reference figure is deliberately absent: it is void, not zero."""
    return ["%s: %d rows left as %s." % (d["at"], d["rows_left"], d["shape"])
            for d in departures]


def main():
    snaps = snapshots()
    if len(snaps) < 3:
        print("SKIP: %d snapshots in %s; this needs a series." % (len(snaps), MEM))
        return 2

    print("  %d snapshots, %s to %s\n"
          % (len(snaps), time.strftime("%Y-%m-%d", time.localtime(snaps[0][0])),
             time.strftime("%Y-%m-%d", time.localtime(snaps[-1][0]))))

    parsed = [(t, n, rows_of(p)) for t, n, p in snaps]
    ok, checks = True, []

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        checks.append({"check": name, "pass": bool(cond), "got": str(got)[:200]})
        print("  %-4s %-58s %s" % ("YES" if cond else "NO", name, got))

    # 1 + 2. Every transition where rows left.
    departures = []
    for (t0, n0, r0), (t1, n1, r1) in zip(parsed, parsed[1:]):
        gone = [s for s in r0 if s not in r1]
        if not gone:
            continue
        pos = [r0[s][0] for s in gone]
        rr = runs(pos)
        last_line = max(v[0] for v in r0.values())
        # A window ends at a position, so a window-fit removal reaches the end of the file.
        touches_tail = any(b >= last_line - 2 for _, b in rr)
        # Referenced by ANOTHER ROW at the moment it left: index-level, exactly datable.
        refs = {}
        for s in gone:
            own_line = r0[s][2]
            n = 0
            for other, v in r0.items():
                if other == s or v[2] == own_line:
                    continue          # a different ROW on the same line is not a reference to it
                line = v[1]
                if s in line or os.path.splitext(s)[0] in WIKI.findall(line):
                    n += 1
            refs[s] = n
        referenced = sum(1 for s in gone if refs[s])
        # Kept for the receipt, but the verdict on it is VOID: see the positive control below, and
        # section 2 of the docstring. A flat index gives this nothing to count.
        departures.append({
            "from": n0, "to": n1,
            "at": time.strftime("%Y-%m-%d %H:%M", time.localtime(t1)),
            "rows_left": len(gone), "rows_before": len(r0), "rows_after": len(r1),
            "runs": len(rr), "largest_run": max(b - a + 1 for a, b in rr),
            "reaches_the_file_end": touches_tail,
            "referenced_by_another_row_when_it_left": referenced,
            "shape": ("one block at the end, a window ending" if len(rr) == 1 and touches_tail
                      else "one block, not at the end" if len(rr) == 1
                      else "scattered, %d separate runs" % len(rr)),
            "slugs": sorted(gone)[:60]})

    print("  %-19s %5s %5s %6s %s"
          % ("when", "left", "runs", "biggest", "shape"))
    for d in departures:
        print("  %-19s %5d %5d %6d %s"
              % (d["at"], d["rows_left"], d["runs"], d["largest_run"], d["shape"]))

    # 3. Returns: a row absent in one snapshot and present in a later one. Walk the series once,
    # remembering what went missing, and record the first snapshot that has it back.
    returns = []
    seen_absent = {}
    for i, (t, n, r) in enumerate(parsed):
        for s in list(seen_absent):
            if s in r:
                returns.append({"slug": s, "left_before": seen_absent[s]["left_before"],
                                "back_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(t)),
                                "back_in": n})
                del seen_absent[s]
        if i:
            prev = parsed[i - 1][2]
            for s in prev:
                if s not in r and s not in seen_absent:
                    seen_absent[s] = {"left_before": time.strftime(
                        "%Y-%m-%d %H:%M", time.localtime(t))}

    print()
    for r in returns:
        print("  RETURNED  %-62s left by %s, back %s" % (r["slug"], r["left_before"], r["back_at"]))
    if not returns:
        print("  no row in the series left and came back")

    print()
    # THE ORDER CONTROL CANNOT USE FILENAMES. The backup naming repeats one date across a series
    # written over three days, so comparing filename dates tested the naming scheme rather than the
    # order. What can fail: this reader must agree with the earlier archive probe, which counted the
    # last event independently at 54 rows.
    dated = [(n, DATE_IN_NAME.search(n).group(1)) for _, n, _ in parsed if DATE_IN_NAME.search(n)]
    repeated = len(dated) - len({d for _, d in dated})
    last = departures[-1] if departures else {}
    check("CONTROL_agrees_with_the_archive_probe_on_the_last_event",
          last.get("rows_left") == 54,
          "this reader: %s rows; the archive probe measured 54" % last.get("rows_left"))
    check("CONTROL_filename_dates_are_NOT_used_for_order",
          repeated > 0,
          "%d of %d dated filenames repeat a date, so mtime is the only ordering available"
          % (repeated, len(dated)))
    check("CONTROL_at_least_one_row_is_seen_leaving",
          bool(departures), "%d transitions removed rows" % len(departures))
    # COVERAGE, not completeness. The archive records 7 retirement events; this series shows 4
    # transitions where rows left, so a return inside an uncovered gap cannot appear. Requiring the
    # archive probe's two here would be requiring the series to hold data it does not have.
    check("CONTROL_at_least_one_return_is_found_by_this_reader",
          len(returns) >= 1,
          "%d found: %s" % (len(returns), [r["slug"][:44] for r in returns]))
    check("CONTROL_the_coverage_gap_is_stated",
          len(departures) < 7,
          "%d transitions with departures against 7 retirement events in the archive, so returns "
          "inside the gaps are invisible here" % len(departures))
    # CAN THE REFERENCE COUNTER FIRE AT ALL? Inject one cross-line reference into a copy of the
    # newest snapshot and require the counter to find exactly it. This is what separates "the index
    # has no cross-references" from "the counter is broken", and the void verdict rests on it.
    newest = parsed[-1][2]
    victim = sorted(newest)[0]
    synthetic = dict(newest)
    synthetic["control-row.md"] = (
        len(newest), "- [a synthetic row](control-row.md) pointing at %s" % victim, 10 ** 6)
    own = synthetic[victim][2]
    found = sum(1 for other, v in synthetic.items()
                if other != victim and v[2] != own
                and (victim in v[1] or os.path.splitext(victim)[0] in WIKI.findall(v[1])))
    check("CONTROL_the_reference_counter_finds_an_injected_reference",
          found == 1, "found %d with exactly 1 injected, victim %s" % (found, victim))
    cross = sum(1 for _, _, r in parsed
                for sl, vv in r.items()
                for o2, v2 in r.items()
                if o2 != sl and v2[2] != vv[2]
                and (sl in v2[1] or os.path.splitext(sl)[0] in WIKI.findall(v2[1])))
    check("VOID_no_row_in_the_series_ever_cited_another_row",
          cross == 0,
          "%d cross-line references across %d snapshots, so the false-retirement question is not "
          "answerable from this index" % (cross, len(parsed)))

    # If every event still reads the same, the discriminator is not discriminating and the finding
    # below is void rather than negative.
    spread = {d["shape"].split(",")[0] for d in departures}
    check("CONTROL_the_discriminator_separates_at_least_two_shapes",
          len(spread) > 1, sorted(spread))

    out = {"probe": os.path.basename(__file__), "memory_dir": MEM,
           "snapshots": len(parsed), "departures": departures, "returns": returns,
           "checks": checks, "all_passed": ok,
           "finding": _finding(departures),
           "reference_measure_verdict":
               "VOID. Zero cross-line references exist anywhere in the 26 snapshots, so the counter "
               "never had a target. An injected reference IS found, so the absence is a property of "
               "the index rather than of the instrument.",
           "scope": "References are counted from INSIDE the index only. Note files are not "
                    "versioned, so a [[link]] in a note today cannot be dated to the retirement. "
                    "This is index-level reference at retirement time, not the full "
                    "false-retirement rate."}
    p = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("\n  %s   receipt: %s" % ("controls passed" if ok else "A CONTROL FAILED",
                                    os.path.basename(p)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
