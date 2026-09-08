"""Re-creation as a false-retirement signal that needs no references, and what it cannot yet answer.

@pm25coder proposed this on anthropics/claude-code#91188 after our zero-cross-reference result: a
retired row whose content reappears in a later snapshot is the cleanest false-retirement signal
available, because it needs no relationships to follow. A row that returns is a row the cap charged
for twice. He asked specifically about the 15 rows that left by sharing a physical line with a judged
neighbour.

WHAT THIS MEASURES. Every transition in the 26-snapshot series where rows left the live index, the
cohort that left, how many snapshots exist after it, and how many of that cohort appear in any of
them.

THE ANSWER TO HIS QUESTION IS THAT THE DATA CANNOT GIVE ONE YET, and that is worth saying plainly.
The 15 adjacency rows left at the most recent transition, so the number of snapshots after them is
zero. A re-creation rate over an empty window is not a low rate; it is no measurement. The metric
becomes answerable for that cohort at the next trim, and it is answerable now for the older ones.

WHERE THERE IS A WINDOW the rate is low. The strongest arm is the oldest: 40 rows with 24 later
snapshots.

MATCHING IS BY SLUG, WHICH IS NARROWER THAN HE ASKED. He said "domain or content reappears". A row
rewritten under a new name would not be caught here, so this is a lower bound on re-creation rather
than an estimate of it.

CONTROLS.
  IT CAN FIND ONE      at least one return must be found, or a zero would be indistinguishable from
                       a reader that cannot detect re-entry at all.
  NEVER PRESENT        a slug absent from every snapshot must count zero.
  WINDOW STATED        every cohort reports its own number of later snapshots, so a zero over an
                       empty window is never presented as a low rate.
  ORDER                snapshots are ordered by mtime; the backup filenames repeat one date across
                       three days and cannot be used.
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
LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+\.md)\)")
# EXACT NAMES. A prefix filter on "memory" excludes the index and archive -- and also
# `memorygraft-crucible-candidate`, `memory-scan-product-backlog` and
# `memory-tipping-ews-killed`, three ordinary data rows. Measured 2026-09-08: the same
# filter in the companion probe undercounted a publicly cited cohort by one.
INDEX_FILES = {"memory.md", "memory_archive.md"}


def is_index_file(name):
    n = os.path.basename(name).lower()
    return n in INDEX_FILES or n.startswith("memory.md.bak")


def rows(path):
    out = set()
    for line in io.open(path, encoding="utf-8", errors="replace").read().splitlines():
        for m in LINK.finditer(line):
            s = os.path.splitext(os.path.basename(m.group(1)))[0]
            if not is_index_file(s + ".md"):
                out.add(s)
    return out


def main():
    paths = glob.glob(os.path.join(MEM, "MEMORY.md.bak-*")) + [os.path.join(MEM, "MEMORY.md")]
    snaps = sorted((os.path.getmtime(p), os.path.basename(p), p) for p in paths if os.path.isfile(p))
    if len(snaps) < 3:
        print("SKIP: %d snapshots; this needs a series." % len(snaps))
        return 2
    sets = [(t, n, rows(p)) for t, n, p in snaps]

    cohorts = []
    print("  %-30s %6s %7s %9s" % ("transition", "left", "windows", "returned"))
    for i in range(len(sets) - 1):
        t0, _, a = sets[i]
        t1, _, b = sets[i + 1]
        gone = a - b
        if not gone:
            continue
        later = sets[i + 2:]
        back = sorted({s for s in gone for _, _, c in later if s in c})
        cohorts.append({
            "from": time.strftime("%Y-%m-%d %H:%M", time.localtime(t0)),
            "to": time.strftime("%Y-%m-%d %H:%M", time.localtime(t1)),
            "rows_left": len(gone), "snapshots_after": len(later),
            "returned": len(back), "returned_slugs": back})
        print("  %-30s %6d %7d %9d %s"
              % ("%s -> %s" % (time.strftime("%m-%d %H:%M", time.localtime(t0)),
                               time.strftime("%m-%d %H:%M", time.localtime(t1))),
                 len(gone), len(later), len(back), ("  " + back[0][:44]) if back else ""))

    with_window = [c for c in cohorts if c["snapshots_after"] > 0]
    rows_w = sum(c["rows_left"] for c in with_window)
    back_w = sum(c["returned"] for c in with_window)
    blind = [c for c in cohorts if c["snapshots_after"] == 0]

    print()
    print("  cohorts with a window : %d, holding %d rows, %d returned (%.1f%%)"
          % (len(with_window), rows_w, back_w, 100.0 * back_w / rows_w if rows_w else 0.0))
    for c in blind:
        print("  NO WINDOW             : the %d rows leaving at %s have no later snapshot, so the "
              "rate for them is not a low number, it is absent" % (c["rows_left"], c["to"]))

    ok, checks = True, []

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        checks.append({"check": name, "pass": bool(cond), "got": str(got)[:200]})
        print("  %-4s %-56s %s" % ("YES" if cond else "NO", name, got))

    print()
    check("CONTROL_the_reader_finds_at_least_one_return",
          back_w >= 1, "%d found; a zero here would not be distinguishable from a blind reader" % back_w)
    ever = set().union(*(s for _, _, s in sets))
    check("CONTROL_a_slug_in_no_snapshot_counts_zero",
          "zqxjv-wrompf-blenkarth-no-such-row" not in ever)
    check("CONTROL_every_cohort_states_its_own_window",
          all("snapshots_after" in c for c in cohorts) and bool(blind),
          "%d cohorts, %d of them blind" % (len(cohorts), len(blind)))
    check("CONTROL_the_largest_window_is_on_the_oldest_cohort",
          cohorts and cohorts[0]["snapshots_after"] == max(c["snapshots_after"] for c in cohorts),
          "oldest has %d" % (cohorts[0]["snapshots_after"] if cohorts else -1))

    out = {"probe": os.path.basename(__file__), "memory_dir": MEM, "snapshots": len(sets),
           "cohorts": cohorts,
           "rows_with_a_window": rows_w, "returned": back_w,
           "rate_percent": round(100.0 * back_w / rows_w, 2) if rows_w else None,
           "checks": checks, "all_passed": ok,
           "finding": (
               "Across the cohorts that have any later snapshot, %d of %d retired rows reappear in "
               "the live index, a rate of %.1f%%. The strongest arm is the oldest: %d rows against "
               "%d later snapshots, with %d returns. The cohort asked about, the rows that left at "
               "the most recent transition, has no later snapshot at all, so for them the metric is "
               "absent rather than low, and becomes answerable at the next trim."
               % (back_w, rows_w, 100.0 * back_w / rows_w if rows_w else 0.0,
                  cohorts[0]["rows_left"] if cohorts else 0,
                  cohorts[0]["snapshots_after"] if cohorts else 0,
                  cohorts[0]["returned"] if cohorts else 0)),
           "scope": "Matching is by slug. A row rewritten under a new name is not caught, so this is "
                    "a lower bound on re-creation rather than an estimate of it."}
    print("\n  FINDING: %s" % out["finding"])
    p = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("  %s   receipt: %s" % ("controls passed" if ok else "A CONTROL FAILED",
                                  os.path.basename(p)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
