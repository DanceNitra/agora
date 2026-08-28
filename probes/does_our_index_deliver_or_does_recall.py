#!/usr/bin/env python3
"""Does our memory INDEX deliver the facts, or does direct recall?

Prompted by anthropics/claude-code#82056, where another store measured 99.75%
index reachability with neither cap binding -- a perfectly healthy receipt --
while 2.6% of sessions ever opened a hub sub-index and 50.9% still received topic
files, because the harness reads the store directly and does not walk the index.
If that holds here, every index measurement we have made (window occupancy,
crowding, recall@3 0.343 vs 0.216) has been scoring the wrong channel.

Our shape differs and that matters: our index names files DIRECTLY on its lines
rather than behind hub sub-indexes, so the hop-2 defect they found is mostly not
available to us. What transfers is the question, not their answer.

INSTRUMENT. A topic file's body carries `name: <slug>` in its frontmatter, a form
that appears NOWHERE in MEMORY.md (C1 asserts it), so finding it in a transcript
means the BODY arrived rather than a pointer to it.

WRITER SESSIONS ARE EXCLUDED, and this is the correction that inverts the answer.
A session that writes a memory file necessarily contains the slug it wrote, so
counting those measures authorship. Their first pass reported hop-1/hop-2 parity
and was garbage for exactly this reason.

CONTROLS, each able to fail:
  C1  the marker must not occur in the index, or a pointer is miscounted as a body
  C2  every slug named in the index window must resolve to a real file
  C3  the detector must find at least one delivery, or it is dead
  C4  writer sessions must be identified and their count reported
  C5  the parser must see tool calls at all. The first revision shelled out to
      grep with a quoted pattern; Windows mangled the quoting, grep answered
      "Invalid back reference" on stderr, and the code read the empty stdout as
      zero. It reported C4 = 0 writers and looked like a clean pass. Everything
      is parsed in-process now, and C5 exists so a dead parser cannot present
      itself as an empty result.
"""
import io
import json
import os
import re
import sys

HOME = os.path.expanduser("~")
PROJ = os.path.join(HOME, ".claude", "projects", "C--Users-Danculus-agora")
MEM = os.path.join(PROJ, "memory")
INDEX = os.path.join(MEM, "MEMORY.md")
LINE_CAP, UNIT_CAP = 200, 25_000
THIS_SESSION = "d58cd2cd-56c1-4dbb-973e-94c1b0a34285"   # contaminated by this investigation
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
MARK = re.compile(r"name: ([a-z0-9][a-z0-9-]+)")


def true_text(p):
    return io.open(p, "rb").read().decode("utf-8", "replace")


def window(text):
    """The loader rule: first 200 LINES, then cut at 25,000 UTF-16 units, whole lines."""
    out, units = [], 0
    for ln in text.split("\n")[:LINE_CAP]:
        u = len((ln + "\n").encode("utf-16-le")) // 2
        if units + u > UNIT_CAP:
            break
        out.append(ln)
        units += u
    return "\n".join(out)


def blocks(obj):
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            yield o
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)


def main():
    idx = true_text(INDEX)
    win = window(idx)
    assert "name: " not in win, "C1 FAIL: the frontmatter marker occurs in the index window"

    names = os.listdir(MEM)
    slugs = {}
    for fn in names:
        if fn.endswith(".md"):
            m = re.search(r"^name:\s*(\S+)\s*$", true_text(os.path.join(MEM, fn)), re.M)
            if m:
                slugs[m.group(1)] = fn
    assert slugs, "no memory files carry a frontmatter name"

    linked = set(re.findall(r"\]\(([^)]+)\.md\)", win))
    indexed = {s for s in slugs if s in linked}
    missing = [l for l in linked if l != "MEMORY_ARCHIVE" and l + ".md" not in names]

    print("STORE")
    print("  memory files with a frontmatter name : %d" % len(slugs))
    print("  index window                         : %d lines, %d UTF-16 units"
          % (len(win.split("\n")), len(win.encode("utf-16-le")) // 2))
    print("  which cap binds                      : lines %s / units %s"
          % (len(idx.split("\n")) > LINE_CAP, len(idx.encode("utf-16-le")) // 2 > UNIT_CAP))
    print("  slugs NAMED in the loaded window     : %d" % len(indexed))
    print("  slugs NOT named there                : %d" % (len(slugs) - len(indexed)))
    print("  C2 pointers resolving to nothing     : %d %s"
          % (len(missing), "-> " + ", ".join(missing[:4]) if missing else "(PASS)"))

    rows, tool_calls = [], 0
    for f in sorted(x for x in os.listdir(PROJ) if x.endswith(".jsonl")):
        path = os.path.join(PROJ, f)
        writer, got = False, set()
        with io.open(path, "rb") as fh:
            for raw in fh:
                line = raw.decode("utf-8", "replace")
                got |= {m for m in MARK.findall(line) if m in slugs}
                if '"tool_use"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                for b in blocks(obj):
                    if b.get("type") != "tool_use":
                        continue
                    tool_calls += 1
                    if b.get("name") in WRITE_TOOLS:
                        tgt = str((b.get("input") or {}).get("file_path", "")).replace("\\", "/")
                        if "C--Users-Danculus-agora" in tgt and "/memory/" in tgt:
                            writer = True
        rows.append((f[:-6], writer, got))

    assert tool_calls > 0, "C5 FAIL: the parser found no tool calls at all"

    writers = [r for r in rows if r[1]]
    read_only = [r for r in rows if not r[1] and not r[0].startswith(THIS_SESSION)]
    deliveries = sum(len(r[2]) for r in rows)

    print("\nSESSIONS")
    print("  transcripts                          : %d" % len(rows))
    print("  C5 tool calls parsed                 : %d (PASS)" % tool_calls)
    print("  C4 writer sessions (excluded)        : %d" % len(writers))
    print("  this session (excluded, contaminated): 1")
    print("  read-only sessions counted           : %d" % len(read_only))
    print("  C3 deliveries seen anywhere          : %d %s"
          % (deliveries, "(PASS)" if deliveries else "(FAIL - detector is dead)"))
    if not deliveries or not read_only:
        return 2

    def cohort(pool, universe):
        hits = {s: 0 for s in universe}
        for _, _, got in pool:
            for s in got & universe:
                hits[s] += 1
        never = sum(1 for v in hits.values() if v == 0)
        return (sum(hits.values()) / len(universe)) if universe else 0.0, never, len(universe)

    non_indexed = set(slugs) - indexed
    print("\nDELIVERY IN READ-ONLY SESSIONS (the body arrived, not merely a pointer)")
    print("  %-26s %-7s %-15s %s" % ("cohort", "files", "never seen", "mean sessions/file"))
    res = {}
    for label, uni in (("named in loaded index", indexed), ("not in loaded index", non_indexed)):
        mean, never, n = cohort(read_only, uni)
        res[label] = mean
        print("  %-26s %-7d %-15s %.2f"
              % (label, n, "%d (%d%%)" % (never, round(100 * never / n) if n else 0), mean))
    a, b = res["named in loaded index"], res["not in loaded index"]
    print("  ratio (named / not named)            : %s"
          % ("%.2fx" % (a / b) if b else "n/a"))

    with_bodies = sum(1 for r in read_only if r[2])
    print("\n  read-only sessions with >=1 topic body present: %d / %d (%.0f%%)"
          % (with_bodies, len(read_only), 100.0 * with_bodies / len(read_only)))
    print("\nBOUNDARY: %d transcripts, one box, one project -- against their 703. 'the slug\n"
          "appeared' is an upper bound on delivery, not evidence it was used. The cohorts are\n"
          "not randomised: files reach the index because they are standing rules, which biases\n"
          "the first row upward, so any ratio is a ceiling on the naming effect." % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
