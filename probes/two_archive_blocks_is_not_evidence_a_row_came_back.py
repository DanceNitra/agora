"""Can our archive tell a resurrection from a second archive write? Measured: no.

WHY. In comment 5580153257 on anthropics/claude-code#91188 we published this inference:

    "Two rows appear in two separate retirement events, and that is only possible if they returned
    to the live index in between: real-vector-sampling-cannot-see-a-degeneracy and
    tenant-filtered-view-persisted-drops-everyone-elses-rows. Two in 194 retirements, 1.0%."

The "only possible if" is an assumption about the archive, not a reading of the index. It holds only
where the archive is append-only AND each block lists exactly the rows leaving at that moment. This
asks the live index instead, through the 26 dated MEMORY.md snapshots, and finds that the instrument
cannot answer for either row.

WHAT DECIDES IT is snapshot COVERAGE, so coverage is measured rather than assumed. A row can only be
shown to have returned if a snapshot sits between its two archive events. For both published rows,
none does.

THE OTHER INSTRUMENT DISAGREES, AND THAT IS THE POINT. Scanning the snapshot series directly
(probes/a_retired_row_that_comes_back_is_the_cap_charging_twice.py) finds one row that demonstrably
left and came back, and it appears in ZERO archive blocks. So the two instruments have disjoint
answer sets because they measure different things: archive-block membership records what a trim
WROTE, and snapshot presence records what the index HELD. Neither contains the other.

CONTROLS.
  IT CAN SEE A ROW     a slug known to be in a snapshot must read present there, and a slug in no
                       snapshot must read absent everywhere. A reader that saw nothing would report
                       "no returns" for every row.
  IT CAN SEE A RETURN  the row the companion probe found must show a 0 then a 1 in this series. A
                       series-reader that cannot detect the one known return proves nothing by
                       failing to detect others.
  COVERAGE IS REAL     for every row named in two archive blocks, report whether any snapshot falls
                       between the two block dates. That number, not the verdict, is the finding.
"""
from __future__ import annotations

import datetime
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from memory_index_files import is_index_file, _self_check  # noqa: E402,F401


MEM = os.environ.get(
    "AGORA_MEMORY_DIR",
    os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory"))
LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+\.md)\)")
# The index/data test lives in tools/memory_index_files.py, imported above. It is not restated
# here: four probes each carried their own copy and every copy was the wrong one.
# The two rows we published as resurrections, and the one the snapshot scan actually found.
PUBLISHED = ["real-vector-sampling-cannot-see-a-degeneracy",
             "tenant-filtered-view-persisted-drops-everyone-elses-rows"]
OBSERVED = "the-index-we-optimised-was-truncated-before-it-was-read"
DATE_IN_HEADING = re.compile(r"(20\d\d)-(\d\d)-(\d\d)")
WITNESS_POOL = []


def slugs_in(text):
    out = set()
    for m in LINK.findall(text):
        s = os.path.splitext(os.path.basename(m))[0]
        if not is_index_file(s + ".md"):
            out.add(s)
    return out


def witnesses(dates):
    """Snapshots that could witness a return between two archive events.

    STRICTLY LATER DAY, STRICTLY EARLIER DAY, and the boundary days are excluded on purpose. An
    archive heading carries a DATE, never a time, so a snapshot taken on the same calendar day as an
    event cannot be ordered against it. The first version of this counted `dates[0] <= t <=
    dates[-1]` and reported one witness for real-vector-sampling: the 08-26 08:46 PRE-TRIM backup,
    which is the state BEFORE the very event it was supposed to come after. That is a witness that
    cannot see the thing it is called to witness.
    """
    if len(dates) < 2:
        return []
    lo = dates[0] + datetime.timedelta(days=1)
    hi = dates[-1]
    return [t for t in WITNESS_POOL if lo <= t < hi]


def main() -> int:
    paths = glob.glob(os.path.join(MEM, "MEMORY.md.bak-*")) + [os.path.join(MEM, "MEMORY.md")]
    snaps = sorted((os.path.getmtime(p), p) for p in paths if os.path.isfile(p))
    if len(snaps) < 3:
        print("SKIP: %d snapshots; this needs a series." % len(snaps))
        return 2
    series = [(t, slugs_in(io.open(p, encoding="utf-8", errors="replace").read()))
              for t, p in snaps]
    stamp = [datetime.datetime.fromtimestamp(t) for t, _ in series]
    global WITNESS_POOL
    WITNESS_POOL = stamp
    gap_days = max((stamp[i + 1] - stamp[i]).total_seconds()
                   for i in range(len(stamp) - 1)) / 86400.0

    arc = io.open(os.path.join(MEM, "MEMORY_ARCHIVE.md"),
                  encoding="utf-8", errors="replace").read()
    blocks = [(b.splitlines()[0].strip(), slugs_in(b))
              for b in re.split(r"^##\s+", arc, flags=re.M)[1:]]

    def block_date(head):
        m = DATE_IN_HEADING.search(head)
        return datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

    in_blocks = {}
    for head, ss in blocks:
        for s in ss:
            in_blocks.setdefault(s, []).append(head)
    multi = {s: h for s, h in in_blocks.items() if len(h) > 1}

    def presence(slug):
        return "".join("1" if slug in st else "0" for _, st in series)

    rows_out = []
    for slug, heads in sorted(multi.items()):
        dates = sorted(d for d in (block_date(h) for h in heads) if d)
        covered = witnesses(dates)
        seq = presence(slug)
        first_seen = seq.find("1")
        rows_out.append({
            "slug": slug,
            "archive_blocks": heads,
            "dated_blocks": [d.strftime("%Y-%m-%d") for d in dates],
            "presence_across_snapshots": seq,
            "snapshots_between_the_two_blocks": [t.strftime("%Y-%m-%d %H:%M")
                                                 for t in covered],
            "a_return_is_visible_in_the_series": bool(
                first_seen >= 0 and "01" in seq[first_seen:]),
            "verdict": ("UNCHECKABLE: no snapshot between the two archive events"
                        if len(covered) == 0 else
                        "CHECKABLE: %d snapshot(s) fall between them" % len(covered)),
        })

    obs_seq = presence(OBSERVED)
    obs_first = obs_seq.find("1")
    control_sees_return = obs_first >= 0 and "01" in obs_seq[obs_first:]
    live = series[-1][1]
    absent_slug = "zqxjv-wrompf-blenkarth-no-such-note"

    checks = [
        ("CONTROL_the_reader_sees_a_slug_that_is_present",
         len(live) > 0 and presence(sorted(live)[0]).endswith("1"),
         "%d slugs in the newest snapshot" % len(live)),
        ("CONTROL_a_slug_in_no_snapshot_reads_absent_everywhere",
         set(presence(absent_slug)) == {"0"}, absent_slug),
        ("CONTROL_the_series_can_detect_the_one_known_return",
         control_sees_return, "%s -> %s" % (OBSERVED, obs_seq)),
        ("BOTH_PUBLISHED_ROWS_ARE_NAMED_IN_TWO_BLOCKS",
         all(s in multi for s in PUBLISHED),
         "%d rows appear in 2 or more archive blocks" % len(multi)),
        ("NEITHER_PUBLISHED_ROW_SHOWS_A_RETURN_IN_THE_SERIES",
         not any(r["a_return_is_visible_in_the_series"]
                 for r in rows_out if r["slug"] in PUBLISHED), ""),
        ("AND_THE_SERIES_CANNOT_CHECK_EITHER_ONE",
         all(not r["snapshots_between_the_two_blocks"]
             for r in rows_out if r["slug"] in PUBLISHED),
         "no snapshot falls between the two archive events, for either row"),
        # The criterion must be able to FIND a witness, or "no witness" is a property of the code.
        ("CONTROL_the_witness_rule_finds_snapshots_over_a_covered_span",
         len(witnesses([datetime.datetime(2026, 8, 18), datetime.datetime(2026, 8, 22)])) > 0,
         "%d snapshots fall strictly inside 2026-08-18..2026-08-22"
         % len(witnesses([datetime.datetime(2026, 8, 18), datetime.datetime(2026, 8, 22)]))),
        ("CONTROL_the_witness_rule_excludes_a_same_day_snapshot",
         not witnesses([datetime.datetime(2026, 8, 26), datetime.datetime(2026, 8, 27)]),
         "the 08-26 08:46 pre-trim backup is not a witness to the 08-26 event"),
        ("THE_OBSERVED_RETURN_IS_IN_NO_ARCHIVE_BLOCK",
         OBSERVED not in in_blocks,
         "the archive instrument structurally cannot see it"),
    ]

    for r in rows_out:
        print("  %-56s %s" % (r["slug"][:56], r["presence_across_snapshots"]))
        for h in r["archive_blocks"]:
            print("        block: %s" % h[:72])
        print("        %s" % r["verdict"])
    print("\n  observed return  %-38s %s" % (OBSERVED[:38], obs_seq))
    print()
    for name, ok, got in checks:
        print("  %-4s %-52s %s" % ("YES" if ok else "NO", name, got))

    out = {
        "probe": os.path.basename(__file__),
        "snapshots": len(series),
        "snapshot_span": [stamp[0].strftime("%Y-%m-%d %H:%M"),
                          stamp[-1].strftime("%Y-%m-%d %H:%M")],
        "largest_gap_days": round(gap_days, 1),
        "archive_blocks": len(blocks),
        "rows_in_two_or_more_blocks": rows_out,
        "observed_return": {"slug": OBSERVED, "presence": obs_seq,
                            "in_archive_blocks": in_blocks.get(OBSERVED, [])},
        "checks": [{"check": c, "pass": bool(ok), "got": str(got)[:200]} for c, ok, got in checks],
        "all_passed": all(ok for _, ok, _ in checks),
        "finding": (
            "We published that two rows appearing in two archive blocks each is 'only possible if "
            "they returned to the live index in between'. The snapshot series cannot check that for "
            "either row: no snapshot falls between the two archive events in either case, and the "
            "largest gap in the series is %.0f days. Neither row shows a return in the series. "
            "Meanwhile the one row that demonstrably left and came back appears in no archive block "
            "at all. Archive-block membership records what a trim WROTE; snapshot presence records "
            "what the index HELD. Neither instrument contains the other, so the 1.0 percent figure "
            "rests on an assumption the data does not support." % gap_days),
        "scope": ("This does not show the two rows did NOT return. It shows the instrument we cited "
                  "cannot tell a return from a second archive write, and that our series has no "
                  "observation in the window where it would matter."),
    }
    print("\n  FINDING: %s" % out["finding"])
    io.open(os.path.splitext(os.path.abspath(__file__))[0] + ".result.json",
            "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=1) + "\n")
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
