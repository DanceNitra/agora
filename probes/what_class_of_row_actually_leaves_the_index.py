"""When a memory index is pruned, what class of row leaves? And what leaves without anyone pruning it?

WHY THIS EXISTS. anthropics/claude-code#91188 converged on a reminder design, and then hit a question
none of the three participants could answer. @samvallad33 said the compaction reminder "trains the
agent to delete guard lines". @pm25coder agreed the mechanism is plausible, asked for the number, and
said plainly that nobody in the thread has data on the CONTENT CLASS of what actually gets deleted.
Every measurement on that thread so far is about counts, units and ratios.

This store can answer it, because retirement here is not a delete. A retired row moves from
`MEMORY.md` to `MEMORY_ARCHIVE.md`, and every row on both sides points at a topic file that declares
its own type. So the class of what left is recoverable, row by row, without inferring anything from
the prose.

TWO KINDS OF LEAVING, and the second is the one the thread has not considered.

  RETIRED   a person or a session moved the row to the archive. Deliberate, recorded, reversible.
  UNREAD    the row is still in the live index and never reaches the model, because the loader stops
            at a cap partway down the file. Nothing was deleted. The row is simply below the cut.

The second is silent. A guard that falls below the cut is as absent as a deleted one, and no
compaction reminder was involved, so a thread reasoning only about what the reminder provokes cannot
see it.

WHAT IS CLASSIFIED. Each row resolves to its topic file, whose frontmatter declares
`metadata.type` as one of user, feedback, project or reference. Two of those are guards in the sense
@samvallad33 means, rules about how the work is done: `feedback` (corrections and confirmed
approaches) and `user` (who the user is and what they want). The other two are the record of work:
`project` and `reference`. That mapping is the only judgement here and it is written down rather
than implied.

THE CONTROLS, because each number can be produced by a broken reader:
  * every row must resolve to a file that exists. Rows that do not are counted and excluded, and if
    many fail the classification is measuring parse failures rather than content;
  * the classifier must not be constant. The distribution over the whole corpus is printed, so a
    result of "everything is a guard" is visible as such;
  * a row must not appear on both sides. An overlap means the archive is a copy rather than a
    destination, and the retirement numbers would be fiction;
  * the loader cut is READ FROM THE LOADER'S OWN RULE, not guessed, and the probe reports what the
    rule yields on this file rather than assuming the file is over it.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                   "C--Users-Danculus-agora", "memory")
LIVE = os.path.join(MEM, "MEMORY.md")
ARCHIVE = os.path.join(MEM, "MEMORY_ARCHIVE.md")

# The loader's documented rule, quoted in the index's own header: it keeps the smaller of 200 lines
# and 25,000 UTF-16 units, whole lines, counting CR.
LINE_CAP, UNIT_CAP = 200, 25000

# THE SAME PATTERN `what_our_own_index_actually_delivers.py` USES, deliberately identical. This
# probe first required a leading dash, and the index carries several pointers on one line, so it
# missed 48 of 222 links and reported 5 rows below the loader cut where that probe measured 9 files
# outside the window. Two definitions of "a row" is how two measurements of one file disagree.
ROW = re.compile(r"\]\(([^)]+\.md)\)")
GUARD_TYPES = {"feedback", "user"}
RECORD_TYPES = {"project", "reference"}


def units(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def rows_of(path: str):
    if not os.path.exists(path):
        return []
    text = io.open(path, encoding="utf-8").read()
    seen, out = set(), []
    for m in ROW.finditer(text):
        slug = os.path.basename(m.group(1))
        if slug in seen:                 # a pointer repeated in the file is one pointer
            continue
        seen.add(slug)
        out.append((slug, slug, m.start()))
    return out


def type_of(slug: str):
    p = os.path.join(MEM, slug)
    if not os.path.exists(p):
        return None
    head = io.open(p, encoding="utf-8", errors="replace").read(1200)
    m = re.search(r"^\s*type:\s*([a-z |]+)\s*$", head, re.M)
    if not m:
        return "undeclared"
    # `type: user | feedback | project | reference` is the TEMPLATE line, not a value. A file that
    # still carries it never had its type chosen, and counting the first alternative as the answer
    # would silently label every unfinished note "user".
    v = m.group(1).strip()
    return "undeclared" if "|" in v else v


def loader_cut(path: str) -> int:
    """How many rows the loader actually delivers, by its own rule."""
    text = io.open(path, encoding="utf-8", newline="").read()
    lines = text.split("\n")
    kept, total = [], 0
    for i, ln in enumerate(lines):
        if i >= LINE_CAP:
            break
        total += units(ln + "\n")
        if total > UNIT_CAP:
            break
        kept.append(ln)
    delivered = "\n".join(kept)
    return len(set(os.path.basename(x) for x in ROW.findall(delivered)))


def main():
    if not os.path.exists(LIVE):
        print("the index is not on this machine: %s" % LIVE)
        return 2

    live, arch = rows_of(LIVE), rows_of(ARCHIVE)
    live_slugs = {s for _t, s, _o in live}
    arch_slugs = {s for _t, s, _o in arch}

    # A ROW ON BOTH SIDES IS A FINDING AT ONE, AND A VOID AT MANY. If the archive is largely a copy
    # of the live index, no retirement number means anything and the run must refuse. A handful is a
    # defect in the store worth naming, and excluding those rows keeps the comparison honest.
    overlap = sorted(live_slugs & arch_slugs)
    total_rows = len(live_slugs | arch_slugs)
    if len(overlap) > 0.02 * total_rows:
        print("  VOID: %d of %d row(s) appear in BOTH the live index and the archive, so the archive "
              "is a copy rather than a destination and no retirement number below means anything."
              % (len(overlap), total_rows))
        return 1
    if overlap:
        print("  DUPLICATED, live and archived at once, and excluded from both sides below:")
        for slug in overlap:
            print("    %s  (declared %s)" % (slug, type_of(slug) or "no file"))
        live = [r for r in live if r[1] not in set(overlap)]
        arch = [r for r in arch if r[1] not in set(overlap)]
    out_overlap = overlap

    out = {"duplicated_both_sides": out_overlap,
           "live_rows": len(live), "archived_rows": len(arch),
           "total_ever": len(live) + len(arch), "classes": {}}
    print("  live index      : %d rows" % len(live))
    print("  archive         : %d rows" % len(arch))
    print("  ever written    : %d, of which %.1f%% retired"
          % (len(live) + len(arch), 100.0 * len(arch) / max(1, len(live) + len(arch))))

    tally = {}
    unresolved = {"live": 0, "archive": 0}
    for label, rows in (("live", live), ("archive", arch)):
        counts = {}
        for _title, slug, _off in rows:
            t = type_of(slug)
            if t is None:
                unresolved[label] += 1
                continue
            counts[t] = counts.get(t, 0) + 1
        tally[label] = counts

    print("\n  %-12s %-9s %-9s" % ("type", "live", "archived"))
    every = sorted(set(tally["live"]) | set(tally["archive"]))
    for t in every:
        print("  %-12s %-9d %-9d" % (t, tally["live"].get(t, 0), tally["archive"].get(t, 0)))
    print("  %-12s %-9d %-9d  (row points at a file that is not there)"
          % ("unresolved", unresolved["live"], unresolved["archive"]))
    out["classes"] = tally
    out["unresolved"] = unresolved

    resolved = {k: sum(v.values()) for k, v in tally.items()}
    if min(resolved.values()) < 5:
        print("\n  VOID: too few rows resolve to a file to compare classes (%s)." % resolved)
        return 1
    if len(every) < 2:
        print("\n  VOID: every row classifies the same way, so the classifier cannot separate "
              "anything and no comparison below is available.")
        return 1

    def share(counts, group):
        n = sum(counts.values())
        return 100.0 * sum(counts.get(t, 0) for t in group) / max(1, n)

    gl, ga = share(tally["live"], GUARD_TYPES), share(tally["archive"], GUARD_TYPES)
    rl, ra = share(tally["live"], RECORD_TYPES), share(tally["archive"], RECORD_TYPES)
    print("\n  guards (feedback, user)   live %5.1f%%   archived %5.1f%%" % (gl, ga))
    print("  record (project, reference) live %5.1f%%   archived %5.1f%%" % (rl, ra))
    out["guard_share_live"], out["guard_share_archived"] = round(gl, 1), round(ga, 1)

    print()
    if ga > gl:
        print("  RETIREMENT FAVOURS GUARDS on this store: a retired row is more likely to be a rule "
              "about how to work than a live row is, %.1f%% against %.1f%%." % (ga, gl))
        out["retirement_verdict"] = "guards_over_represented_in_the_archive"
    elif gl > ga:
        print("  RETIREMENT SPARES GUARDS on this store: guards are %.1f%% of the live index and "
              "only %.1f%% of the archive, so what leaves is mostly the record of work." % (gl, ga))
        out["retirement_verdict"] = "guards_under_represented_in_the_archive"
    else:
        print("  Retirement is indifferent to the class here.")
        out["retirement_verdict"] = "indifferent"

    # THE SECOND KIND OF LEAVING, which no delete is involved in.
    delivered = loader_cut(LIVE)
    below = len(live) - delivered
    total_units, total_lines = units(io.open(LIVE, encoding="utf-8", newline="").read()), \
        len(io.open(LIVE, encoding="utf-8", newline="").read().split("\n"))
    print("\n  the live file is %d lines and %d UTF-16 units, against caps of %d and %d"
          % (total_lines, total_units, LINE_CAP, UNIT_CAP))
    print("  the loader delivers %d of its %d rows; %d sit below the cut and never arrive"
          % (delivered, len(live), below))
    out.update({"live_lines": total_lines, "live_units": total_units,
                "rows_delivered": delivered, "rows_below_the_cut": below})

    if below > 0:
        cut_rows = live[delivered:]
        cut_types = {}
        for _t, slug, _o in cut_rows:
            k = type_of(slug) or "unresolved"
            cut_types[k] = cut_types.get(k, 0) + 1
        gshare = 100.0 * sum(cut_types.get(t, 0) for t in GUARD_TYPES) / max(1, len(cut_rows))
        print("  of those %d, %.1f%% are guards: %s"
              % (below, gshare, ", ".join("%s %d" % kv for kv in sorted(cut_types.items()))))
        out["below_the_cut_classes"] = cut_types
        out["below_the_cut_guard_share"] = round(gshare, 1)
        print("\n  A row below the cut was not deleted and no reminder was involved. It is in the "
              "file, it is not in the model, and nothing reports the difference.")
    else:
        print("  Nothing sits below the cut on this file today, so the silent half does not arise "
              "here and only the retirement result above stands.")

    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("\n  receipt: %s" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
