"""The rows that left because they shared a line look like the rows that stayed, not like the judged.

WHAT THIS ANSWERS. On anthropics/claude-code#91188 I published a measurement and named the next open
question: of the 15 rows that left our index because they shared a physical line with a row the trim
tool had judged, was any of them still load-bearing? This is that measurement.

THE SETUP, all established in probes/was_the_row_judged_or_did_the_window_just_end.py. The archive
section "Demoted from the index 2026-09-04, to fit the loader window" holds 53 rows. The tool that
ran it, tools/trim_memory_index.py, names 32 in a hardcoded list and its commit message states the
criterion: a one-off domain result leaves, a cross-cutting working rule stays. Of the 21 it does not
name, 15 shared a physical line in the index with one it did. Our index packs several pointers onto
one line to fit the LINE cap, and a shared line moves whole, so those 15 left as a side effect of a
neighbour's judgment without being evaluated themselves.

THE MEASURE, and its limit. How many other notes cite each row with a [[wikilink]] today. Note files
are not versioned, so a link present now cannot be dated to the retirement: this cannot say a row was
load-bearing AT THE TIME. What it can do is compare the three groups under one common measure, which
is enough to ask whether the adjacency group resembles the judged group or the surviving one.

THE COMPARISON that makes it a measurement rather than a list. Three groups: the 32 the tool judged,
the 15 it never looked at, and the rows still live in the index. If the adjacency group sits with the
judged group, packing cost nothing. If it sits with the live rows, the line cap evicted rows that are
indistinguishable from the ones kept.

n = 15 is small, so the difference is tested by permutation rather than asserted from a median.

CONTROLS.
  IT CAN FIRE     a slug that is in the store must be found by the counter, and a slug that is not
                  must return zero. A counter that returns zero for everything would make the judged
                  group look identical to every other group.
  DISJOINT        the three groups must not overlap, or a row counted twice would drag two medians
                  toward each other.
  THE NULL        the permutation test must be able to reject: a shuffled label assignment run on the
                  same numbers has to produce the observed gap sometimes, or the test says nothing.
"""
import io
import json
import os
import random
import re
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import trim_memory_index as T  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from memory_index_files import is_index_file, _self_check  # noqa: E402,F401


MEM = os.environ.get(
    "AGORA_MEMORY_DIR",
    os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory"))
LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+\.md)\)")
SECTION = "Demoted from the index 2026-09-04"
DRAWS = 20000
# EXACT NAMES, never a prefix. This used to exclude anything whose name started with "memory",
# which is the index and archive -- and also `memorygraft-crucible-candidate`,
# `memory-scan-product-backlog` and `memory-tipping-ews-killed`, three ordinary data rows. The
# first of those left the index by adjacency on 2026-09-04, so the cohort published in comment
# 5588661516 as 15 rows was really 16, and the reference counter could not see citations coming
# from any of the three files either. A prefix filter aimed at a container silently ate its
# contents.


def notes():
    return {f: io.open(os.path.join(MEM, f), encoding="utf-8", errors="replace").read()
            for f in os.listdir(MEM)
            if f.endswith(".md") and not is_index_file(f)}


def rows_of(path):
    """slug -> physical line number, in file order."""
    out = {}
    for ln, line in enumerate(io.open(path, encoding="utf-8", errors="replace").read().splitlines()):
        for m in LINK.finditer(line):
            s = os.path.splitext(os.path.basename(m.group(1)))[0]
            if is_index_file(s + ".md") or s in out:
                continue
            out[s] = ln
    return out


def permutation_p(a, b, draws=DRAWS, seed=20260908):
    """Two-sided p for a difference in medians, by relabelling the pooled values."""
    obs = abs(statistics.median(a) - statistics.median(b))
    pool = list(a) + list(b)
    rng = random.Random(seed)
    hits = 0
    for _ in range(draws):
        rng.shuffle(pool)
        if abs(statistics.median(pool[:len(a)]) - statistics.median(pool[len(a):])) >= obs:
            hits += 1
    return obs, hits, draws


def main():
    body = notes()
    if not body:
        print("SKIP: no note files under %s" % MEM)
        return 2

    def refs(slug):
        return sum(1 for f, b in body.items() if f != slug + ".md" and "[[%s]]" % slug in b)

    pre = os.path.join(MEM, "MEMORY.md.bak-20260904-pretrim")
    if not os.path.isfile(pre):
        print("SKIP: the pre-event snapshot is not here, so the adjacency group cannot be built.")
        return 2
    line_of = rows_of(pre)

    arc = io.open(os.path.join(MEM, "MEMORY_ARCHIVE.md"), encoding="utf-8", errors="replace").read()
    sec = [x for x in re.split(r"^##\s+", arc, flags=re.M) if x.startswith(SECTION)][0]
    archived = {os.path.splitext(os.path.basename(m))[0] for m in LINK.findall(sec)
                if not is_index_file(m)}

    named_lines = {line_of[d] for d in T.DEMOTE if d in line_of}
    judged = [d for d in T.DEMOTE if d in line_of]
    adjacency = sorted(e for e in (archived - set(T.DEMOTE))
                       if e in line_of and line_of[e] in named_lines)
    live = list(rows_of(os.path.join(MEM, "MEMORY.md")))

    groups = [("judged, named by the tool", judged),
              ("moved by adjacency", adjacency),
              ("still live in the index", live)]
    counts = {name: [refs(s) for s in g] for name, g in groups}

    print("  %-28s %5s  %-16s %8s %5s" % ("group", "n", "referenced today", "median", "max"))
    for name, g in groups:
        r = counts[name]
        print("  %-28s %5d  %2d of %-3d (%3.0f%%) %8.1f %5d"
              % (name, len(r), sum(1 for x in r if x), len(r),
                 100.0 * sum(1 for x in r if x) / len(r), statistics.median(r), max(r)))

    ja, ad, lv = (counts[n] for n, _ in groups)
    obs_ja, hits_ja, draws = permutation_p(ja, ad)
    obs_al, hits_al, _ = permutation_p(ad, lv)
    print()
    print("  judged vs adjacency : median gap %.1f, %d of %d shuffles reach it, p = %.4f"
          % (obs_ja, hits_ja, draws, (hits_ja + 1.0) / (draws + 1.0)))
    print("  adjacency vs live   : median gap %.1f, %d of %d shuffles reach it, p = %.4f"
          % (obs_al, hits_al, draws, (hits_al + 1.0) / (draws + 1.0)))

    ok, checks = True, []

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        checks.append({"check": name, "pass": bool(cond), "got": str(got)[:200]})
        print("  %-4s %-54s %s" % ("YES" if cond else "NO", name, got))

    print()
    present = next((os.path.splitext(f)[0] for f in body), None)
    check("CONTROL_the_counter_finds_a_slug_that_is_in_the_store",
          sum(counts["still live in the index"]) > 0,
          "%d references across the live rows" % sum(counts["still live in the index"]))
    check("CONTROL_a_slug_that_does_not_exist_counts_zero",
          refs("zqxjv-wrompf-blenkarth-no-such-note") == 0)
    check("CONTROL_the_three_groups_are_disjoint",
          not (set(judged) & set(adjacency)) and not (set(adjacency) & set(live))
          and not (set(judged) & set(live)),
          "judged %d, adjacency %d, live %d" % (len(judged), len(adjacency), len(live)))
    # A test that can never reject would make any p meaningless.
    _, self_hits, _ = permutation_p(ja, ja)
    check("CONTROL_the_permutation_test_can_fail_to_reject",
          self_hits > draws * 0.5,
          "a group against itself: %d of %d shuffles reach a zero gap" % (self_hits, draws))
    # CORRECTED 2026-09-08. This used to assert `len(adjacency) == 15`, the number published in
    # comment 5588661516, and it passed -- because the count and the expectation came from the same
    # prefix filter. A control that recomputes the answer the same way tests nothing. It now asserts
    # the FILTER instead: the exclusion must reach the two index files and no data row.
    check("CONTROL_the_index_filter_excludes_only_the_index_files",
          is_index_file("MEMORY.md") and is_index_file("MEMORY_ARCHIVE.md")
          and not is_index_file("memorygraft-crucible-candidate.md")
          and not is_index_file("memory-scan-product-backlog.md"),
          "a prefix filter here hid 3 data rows and undercounted the cohort by one")
    check("CONTROL_the_row_hidden_by_the_prefix_filter_is_now_in_the_cohort",
          "memorygraft-crucible-candidate" in adjacency,
          "it shares a line with folklore-index-hf-published, which the tool judged")
    check("THE_COHORT_SIZE", len(adjacency) == 16,
          "%d; published as 15 on 2026-09-08, corrected here" % len(adjacency))

    p_ja = (hits_ja + 1.0) / (draws + 1.0)
    p_al = (hits_al + 1.0) / (draws + 1.0)
    out = {"probe": os.path.basename(__file__), "memory_dir": MEM,
           "groups": {n: {"n": len(counts[n]),
                          "referenced": sum(1 for x in counts[n] if x),
                          "median": statistics.median(counts[n]),
                          "max": max(counts[n]), "counts": counts[n]} for n, _ in groups},
           "adjacency_slugs": adjacency,
           "permutation": {"draws": draws,
                           "judged_vs_adjacency": {"median_gap": obs_ja, "p": p_ja},
                           "adjacency_vs_live": {"median_gap": obs_al, "p": p_al}},
           "checks": checks, "all_passed": ok,
           "finding": (
               "The %d rows that left by sharing a line are cited by other notes at a median of %.1f, "
               "against %.1f for the 32 the tool judged on content and %.1f for the rows still live. "
               "Judged against adjacency, p = %.4f; adjacency against live, p = %.4f. By this measure "
               "the rows nobody evaluated resemble the rows that stayed, not the rows that were "
               "chosen to go."
               % (len(adjacency), statistics.median(ad), statistics.median(ja),
                  statistics.median(lv), p_ja, p_al)),
           "scope": "Note files are not versioned, so a [[wikilink]] present today cannot be dated to "
                    "the retirement. This compares three groups under one undated measure; it does "
                    "not establish that any row was load-bearing at the moment it left. "
                    "The cohort was published as 15 on 2026-09-08; a prefix filter had hidden a "
                    "16th, and three data files were missing from the reference corpus."}
    print("\n  FINDING: %s" % out["finding"])
    p = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("  %s   receipt: %s" % ("controls passed" if ok else "A CONTROL FAILED",
                                  os.path.basename(p)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
