"""When a memory index is pruned, what class of row leaves? Per retirement event, not on average.

WHY THIS EXISTS. anthropics/claude-code#91188 reached a question none of its participants could
answer. @samvallad33 said the compaction reminder "trains the agent to delete guard lines".
@pm25coder agreed the mechanism was plausible, asked for the number, and wrote that nobody there has
data on the CONTENT CLASS of what gets deleted. Every measurement on that thread is counts, units and
ratios.

This store can answer it, because retirement is a move rather than a delete: a retired pointer goes
to `MEMORY_ARCHIVE.md` under a dated heading saying why, and every pointer on both sides names a file
that declares its own type.

THE AVERAGE IS THE WRONG NUMBER, and the first version of this probe published it. Across the whole
archive, guards are 44.9% against 74.3% in the live index, which reads as "retirement spares guards".
Split by the dated heading each row sits under, the archive is eight separate events that disagree in
sign: one retired 9 rows of which 9 were guards, another retired 54 of which 3 were. The pooled figure
is almost entirely that one event. A share pooled over events with opposite signs is Simpson's paradox
with a date stamp on it, and the thread's own participant holds 306 snapshots and would say so.

FOUR MORE DEFECTS THE FIRST VERSION CARRIED, found by an adversarial pass and each verified here:
  * it counted the index's own link to `MEMORY_ARCHIVE.md` as a pointer to a memory;
  * it counted lines with `split("\\n")`, which yields a phantom final element on a file ending in a
    newline, so 206 lines were published as 207;
  * it treated one archive section as retirement when that section's own heading says nothing ever
    pointed at those rows, so they were never in the live index to be retired from;
  * it never asked how many memory files are in NEITHER index, which is the larger loss.

THE CONTROLS:
  * every pointer must resolve to a file that exists, and unresolved ones are counted, not dropped;
  * the classifier must not be constant, so the full distribution is printed;
  * a pointer on both sides at once is a defect in the store: named below 2% of rows, a refusal above
    it, because then the archive is a copy rather than a destination;
  * the delivered set is compared against `what_our_own_index_actually_delivers.py`, which has
    measured this file for weeks. Two readings that disagree mean one of them is wrong.
"""
import io
import json
import os
import re
import sys

MEM = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                   "C--Users-Danculus-agora", "memory")
LIVE = os.path.join(MEM, "MEMORY.md")
ARCHIVE = os.path.join(MEM, "MEMORY_ARCHIVE.md")
LINE_CAP, UNIT_CAP = 200, 25000

LINK = re.compile(r"\]\(([^)]+\.md)\)")
HEADING = re.compile(r"^##+ (.+)$", re.M)
NOT_A_MEMORY = {"MEMORY.md", "MEMORY_ARCHIVE.md"}
GUARD_TYPES = {"feedback", "user"}
NOT_A_RETIREMENT = "reachable again"


def units(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def pointers(text: str):
    out = []
    for x in LINK.findall(text):
        b = os.path.basename(x)
        if b in NOT_A_MEMORY or b in out:
            continue
        out.append(b)
    return out


def type_of(slug: str):
    p = os.path.join(MEM, slug)
    if not os.path.exists(p):
        return None
    head = io.open(p, encoding="utf-8", errors="replace").read(1200)
    m = re.search(r"^\s*type:\s*([a-z |]+)\s*$", head, re.M)
    if not m:
        return "undeclared"
    v = m.group(1).strip()
    # `type: user | feedback | project | reference` is the template line, not a chosen value.
    return "undeclared" if "|" in v else v


def guard_share(slugs):
    ts = [t for t in (type_of(s) for s in slugs) if t]
    if not ts:
        return 0, 0, 0.0
    g = sum(1 for t in ts if t in GUARD_TYPES)
    return len(ts), g, 100.0 * g / len(ts)


def events(text: str):
    parts = HEADING.split(text)
    return [(parts[i].strip(), pointers(parts[i + 1])) for i in range(1, len(parts), 2)]


def delivered_pointers(path: str):
    text = io.open(path, encoding="utf-8", newline="").read()
    kept, total = [], 0
    for i, ln in enumerate(text.splitlines()):
        if i >= LINE_CAP:
            break
        total += units(ln + "\n")
        if total > UNIT_CAP:
            break
        kept.append(ln)
    return pointers("\n".join(kept))


def main():
    if not os.path.exists(LIVE):
        print("the index is not on this machine: %s" % LIVE)
        return 2

    live_text = io.open(LIVE, encoding="utf-8", newline="").read()
    arch_text = io.open(ARCHIVE, encoding="utf-8", newline="").read()
    live, arch = pointers(live_text), pointers(arch_text)

    overlap = sorted(set(live) & set(arch))
    if len(overlap) > 0.02 * len(set(live) | set(arch)):
        print("  VOID: %d pointers are live and archived at once, so the archive is a copy rather "
              "than a destination and no retirement number below means anything." % len(overlap))
        return 1
    if overlap:
        print("  LIVE AND ARCHIVED AT ONCE, excluded from both sides below:")
        for s in overlap:
            print("    %s  (declared %s)" % (s, type_of(s) or "no file"))
        live = [s for s in live if s not in set(overlap)]
        arch = [s for s in arch if s not in set(overlap)]

    ln, lg, lshare = guard_share(live)
    print("\n  live index   %3d pointers, %3d guards, %.1f%%" % (ln, lg, lshare))

    print("\n  THE ARCHIVE IS NOT ONE POPULATION. Guard share per dated event:\n")
    print("  %-52s %5s %7s %8s" % ("event", "rows", "guards", "share"))
    rows_out, pooled_n, pooled_g = [], 0, 0
    for name, slugs in events(arch_text):
        slugs = [s for s in slugs if s not in set(overlap)]
        n, g, share = guard_share(slugs)
        if not n:
            continue
        retirement = NOT_A_RETIREMENT not in name.lower()
        if retirement:
            pooled_n += n
            pooled_g += g
        print("  %-52s %5d %7d %7.1f%%%s"
              % (name[:52], n, g, share, "" if retirement else "   <- never in the live index"))
        rows_out.append({"event": name, "rows": n, "guards": g, "guard_share": round(share, 1),
                         "is_a_retirement": retirement})
    pooled = 100.0 * pooled_g / max(1, pooled_n)
    print("  %-52s %5d %7d %7.1f%%" % ("ALL RETIREMENT EVENTS POOLED", pooled_n, pooled_g, pooled))

    retirements = [r for r in rows_out if r["is_a_retirement"]]
    above = [r for r in retirements if r["guard_share"] >= lshare]
    print("\n  %d of %d retirement events took guards at or above the live rate of %.1f%%."
          % (len(above), len(retirements), lshare))
    biggest = max(retirements, key=lambda r: r["rows"])
    rest_n, rest_g = pooled_n - biggest["rows"], pooled_g - biggest["guards"]
    print("  The largest single event, %s, is %d rows at %.1f%%. Without it the pooled share is "
          "%.1f%% against %.1f%% live."
          % (biggest["event"][:44], biggest["rows"], biggest["guard_share"],
             100.0 * rest_g / max(1, rest_n), lshare))

    on_disk = {f for f in os.listdir(MEM) if f.endswith(".md") and f not in NOT_A_MEMORY}
    orphans = sorted(on_disk - set(live) - set(arch) - set(overlap))
    on, og, oshare = guard_share(orphans)
    print("\n  %d memory files on disk. %d are in NEITHER index: not live, not archived, nothing "
          "points at them." % (len(on_disk), len(orphans)))
    print("  Of those, %d are guards (%.1f%%)." % (og, oshare))

    dl = delivered_pointers(LIVE)
    below = [s for s in live if s not in set(dl)]
    print("\n  the live file is %d lines and %d units, against caps of %d and %d"
          % (len(live_text.splitlines()), units(live_text), LINE_CAP, UNIT_CAP))
    print("  the loader delivers %d of %d pointers; %d sit below the cut"
          % (len(dl), len(live), len(below)))
    if below:
        bn, bg, bshare = guard_share(below)
        print("  of those %d, %d are guards (%.1f%%)" % (bn, bg, bshare))

    out = {"live_pointers": ln, "live_guards": lg, "live_guard_share": round(lshare, 1),
           "events": rows_out, "pooled_retirement_share": round(pooled, 1),
           "events_at_or_above_live_rate": len(above), "retirement_events": len(retirements),
           "files_on_disk": len(on_disk), "in_neither_index": len(orphans),
           "orphan_guards": og, "orphan_slugs": orphans,
           "live_lines": len(live_text.splitlines()), "live_units": units(live_text),
           "delivered": len(dl), "below_the_cut": len(below),
           "duplicated_both_sides": overlap}
    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("\n  receipt: %s" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
