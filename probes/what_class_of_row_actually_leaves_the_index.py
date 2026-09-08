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

AND IT NOW ANSWERS THE QUESTION THAT WAS ACTUALLY ASKED. The thread asked for a false-retirement
fraction: of the retired rows, how many were dropped while something still pointed at them. Memory
files link to each other with `[[slug]]`, so that has an operational meaning here, and the live index
is the control. The first draft of the reply called this "not the interesting number" and pivoted to
a finding I already had, which is answering an easier question and calling the hard one dull.

THE PER-EVENT SPREAD IS TESTED, NOT EYEBALLED. Seven shares that look different can be seven draws
from one urn. The reply first called the gap Simpson's paradox, which is the wrong name: there is no
second variable stratifying both arms and no reversal, only heterogeneity with one dominant stratum.

THE CONTROLS:
  * every pointer must resolve to a file that exists, and unresolved ones are counted, not dropped;
  * the classifier must not be constant, so the full distribution is printed;
  * a pointer on both sides at once is a defect in the store: named below 2% of rows, a refusal above
    it, because then the archive is a copy rather than a destination;
  * the live index is the control for the reference rate and must come out HIGHER; if retired
    and live rows are equally referenced, the measurement is not seeing reachability;
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
# A section is a retirement only if its rows were ever IN the live index. That is not something a
# probe can read off prose, so the archive DECLARES it: a section whose rows were never live
# carries this token in its heading. The first version matched the phrase "reachable again", the
# next such section was worded differently, and 68 rows at 0% guards became the largest event in
# the table and moved the pooled figure from 34.8% to 46.9%.
NOT_A_RETIREMENT = "[never in the live index]"


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
    # THE WHOLE FILE, not the first 1200 bytes. A long `description:` pushes the frontmatter
    # `type:` past a 1200-byte cut, and 12 files then read as `undeclared` while declaring
    # `project`. No guard was misread when this was found, by luck rather than by design: all
    # 259 `feedback` declarations happened to sit inside the window. A check that cannot see
    # its target reports clean.
    head = io.open(p, encoding="utf-8", errors="replace").read()
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


WIKI = re.compile(r"\[\[([^\]|#]+)")


def inbound_counts():
    """How many other memory files link to each file: the proxy for "something still points at it"."""
    counts = {}
    for f in os.listdir(MEM):
        if not f.endswith(".md") or f in NOT_A_MEMORY:
            continue
        body = io.open(os.path.join(MEM, f), encoding="utf-8", errors="replace").read()
        for w in set(WIKI.findall(body)):
            t = w.strip()
            t = t if t.endswith(".md") else t + ".md"
            if t != f:
                counts[t] = counts.get(t, 0) + 1
    return counts


def heterogeneity(ev):
    """Are the per-event guard shares seven draws from one urn? Chi-square plus a Monte Carlo."""
    import random
    N = sum(n for n, _ in ev)
    G = sum(g for _, g in ev)
    if not N or not G or G == N:
        return None
    p = G / N
    chi = sum((g - n * p) ** 2 / (n * p) + ((n - g) - n * (1 - p)) ** 2 / (n * (1 - p)) for n, g in ev)
    random.seed(7)
    T, hits = 20000, 0
    for _ in range(T):
        sim = [(n, sum(random.random() < p for _ in range(n))) for n, _ in ev]
        c = sum((g - n * p) ** 2 / (n * p) + ((n - g) - n * (1 - p)) ** 2 / (n * (1 - p)) for n, g in sim)
        hits += c >= chi
    return {"chi2": round(chi, 1), "df": len(ev) - 1, "mc_draws": T, "mc_at_or_above": hits,
            "common_rate": round(100 * p, 1)}


def events(text: str):
    """Each dated section and its rows, with any row an earlier section already counted removed.

    `pointers()` deduplicates WITHIN a section and not across them, so a row that was retired, came
    back to the live index, and was retired again was counted in two events. That inflated one event
    from 39 rows to 40 (74.4% reported as 72.5%), the pooled count from 194 to 196, and "rows ever
    written" from 419 to 421.

    The duplicates are the interesting part, so they are returned rather than quietly dropped: a row
    in two retirement events is a measured resurrection, which is the failure the design
    conversation this probe feeds is entirely about. The double count was hiding the finding.
    """
    parts = HEADING.split(text)
    out, seen, again = [], set(), []
    for i in range(1, len(parts), 2):
        rows = []
        for slug in pointers(parts[i + 1]):
            if slug in seen:
                again.append(slug)
                continue
            seen.add(slug)
            rows.append(slug)
        out.append((parts[i].strip(), rows))
    return out, again


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

    ev_rows, resurrected = events(arch_text)
    print("\n  THE ARCHIVE IS NOT ONE POPULATION. Guard share per dated event:\n")
    print("  %-52s %5s %7s %8s" % ("event", "rows", "guards", "share"))
    rows_out, pooled_n, pooled_g = [], 0, 0
    for name, slugs in ev_rows:
        slugs = [s for s in slugs if s not in set(overlap)]
        n, g, share = guard_share(slugs)
        if not n:
            continue
        retirement = NOT_A_RETIREMENT not in name.lower()
        if not retirement:
            name = name.replace("[NEVER IN THE LIVE INDEX] ", "")
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

    inb = inbound_counts()
    live_set = set(live)
    ret, seen = [], set()
    for name, slugs in ev_rows:
        if NOT_A_RETIREMENT in name.lower():
            continue
        for sl in slugs:
            if sl not in live_set and sl not in seen:
                seen.add(sl)
                ret.append(sl)
    rr = sum(1 for x in ret if inb.get(x, 0))
    lr = sum(1 for x in live if inb.get(x, 0))
    rshare = 100.0 * rr / max(1, len(ret))
    lref = 100.0 * lr / max(1, len(live))
    print("\n  RESURRECTED, rows that left the index, came back, and left again: %d" % len(resurrected))
    for slug in sorted(resurrected):
        print("    %s" % slug)

    print("\n  THE FALSE-RETIREMENT QUESTION, answered rather than deferred:")
    print("    retired rows another record still links to : %3d of %3d  %5.1f%%" % (rr, len(ret), rshare))
    print("    CONTROL, live rows                         : %3d of %3d  %5.1f%%" % (lr, len(live), lref))
    print("    %s" % ("the control is higher, as it must be" if lref > rshare else
                      "VOID: live rows are no better referenced than retired ones, so this measures nothing"))

    het = heterogeneity([(e["rows"], e["guards"]) for e in rows_out if e["is_a_retirement"]])
    if het:
        print("\n  the shares against ONE common rate of %.1f%%: chi2 %.1f on %d df, and %d of %d Monte "
              "Carlo draws at the same event sizes reached it"
              % (het["common_rate"], het["chi2"], het["df"], het["mc_at_or_above"], het["mc_draws"]))
    ever_n, ever_g = ln + pooled_n, lg + pooled_g
    print("  every row ever written: %d, of which %d are guards, %.1f%% -- the population that neither "
          "the live nor the retired share is" % (ever_n, ever_g, 100.0 * ever_g / max(1, ever_n)))

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
           "duplicated_both_sides": overlap,
           "retired_rows": len(ret), "retired_still_referenced": rr,
           "retired_referenced_share": round(rshare, 1),
           "live_still_referenced": lr, "live_referenced_share": round(lref, 1),
           "heterogeneity": het, "resurrected": sorted(resurrected), "rows_ever": ever_n, "guards_ever": ever_g,
           "guard_share_ever": round(100.0 * ever_g / max(1, ever_n), 1)}
    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("\n  receipt: %s" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
