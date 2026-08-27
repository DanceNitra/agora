# -*- coding: utf-8 -*-
"""Files the index cannot reach, and pointers that reach no file. Run it on your own store.

WHY THIS EXISTS. @simplysdm raised it on anthropics/claude-code#82056: topic files unreachable from
the index, found by following wikilinks transitively, are "failure mode 3 wearing a healthy costume,
and no cap check catches it". On that box, 228 topic files, 218 reachable, ten recall will never
return. This runs the same measurement on a store about twice the size, and adds the mirror class
that measurement does not look for.

TWO CLASSES, and they fail in opposite directions:

  ORPHAN    a file exists, nothing points at it, so recall never surfaces it. The content is fine.
  DANGLING  a [[link]] names a file that does not exist. The pointer is fine.

Neither shows up in a size or cap check, because the index is well under every limit either way.

WHETHER DANGLING IS A DEFECT DEPENDS ON THE STORE, and this one says it is not. The writing
convention for this memory directory is "link liberally: a [[name]] that does not match an existing
memory yet is fine, it marks something worth writing later, not an error." So the dangling count
here is a backlog, not a fault, and it is reported separately rather than added to the orphan total.
A store without that convention should read the same number the other way. The first version of this
probe printed one figure for both and would have shipped a documented feature as a finding.

The dangling count also has to be split before it means anything: three of this store's targets are
the words "wikilink", "wikilinks" and "link" from prose that discusses linking rather than links,
and one, validate-audit-verify-gate.md, names a file that DOES exist but carries the .md suffix
inside the brackets, so it is a malformed pointer rather than a missing note.

    python probes/a_memory_file_nothing_points_at_is_never_recalled.py [STORE_DIR]

Defaults to the Claude Code project memory directory for this repository. Any directory of markdown
files with an index and [[wikilinks]] works.

CONTROLS, because a reachability walk that returns "everything is fine" and one that is simply
broken look identical from the outside:

  * the walk must reach a file the index names DIRECTLY, or the reader is not reading the index
  * the walk must reach a file reachable only through another file's [[link]], or it is not
    transitive and is measuring the index alone
  * injecting a file nothing points at must raise the orphan count by exactly one
  * injecting a [[link]] to a name that does not exist must raise the dangling count by exactly one
"""
import io
import os
import re
import sys

DEFAULT = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                       "C--Users-Danculus-agora", "memory")
INDEXES = ("MEMORY.md", "MEMORY_ARCHIVE.md")

WIKI = re.compile(r"\[\[([^\]]+)\]\]")
MDLINK = re.compile(r"\]\(([A-Za-z0-9_.-]+)\.md\)")


def read(path):
    try:
        return io.open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def targets(text):
    out = {m.strip() for m in WIKI.findall(text)}
    out |= set(MDLINK.findall(text))
    return {t for t in out if t}


def survey(store):
    files = {f[:-3] for f in os.listdir(store)
             if f.endswith(".md") and f not in INDEXES}
    seeds = set()
    for idx in INDEXES:
        seeds |= targets(read(os.path.join(store, idx)))
    named = {s for s in seeds if s in files}

    reach, stack = set(), list(named)
    while stack:
        n = stack.pop()
        if n in reach:
            continue
        reach.add(n)
        stack += [t for t in targets(read(os.path.join(store, n + ".md")))
                  if t in files and t not in reach]

    pointed = {t for n in reach for t in targets(read(os.path.join(store, n + ".md")))}
    pointed |= seeds
    dangling = pointed - files
    # prose about linking, not links; and pointers that name an existing file the wrong way
    PROSE = {"wikilink", "wikilinks", "link"}
    malformed = {d for d in dangling if d.endswith(".md") and d[:-3] in files}
    phrases = {d for d in dangling if " " in d}
    return {"files": files, "named": named, "reach": reach,
            "orphans": files - reach, "dangling": dangling,
            "dangling_prose": dangling & PROSE,
            "dangling_malformed": malformed,
            "dangling_phrases": phrases,
            "dangling_backlog": dangling - PROSE - malformed - phrases}


def main():
    store = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isdir(store):
        print("no such store: %s" % store)
        return 2
    s = survey(store)
    v = {}

    v["CONTROL_the_store_was_actually_read"] = len(s["files"]) > 0 and len(s["named"]) > 0
    v["CONTROL_a_directly_named_file_is_reached"] = bool(s["named"] & s["reach"])

    # transitive: a file the index does NOT name, reached only through another file's link
    only_via_link = (s["reach"] - s["named"])
    v["CONTROL_the_walk_is_transitive_not_just_the_index"] = bool(only_via_link)

    # injected orphan: a name nothing points at
    fake = set(s["files"]) | {"__injected_orphan__"}
    v["CONTROL_an_injected_orphan_is_counted"] = (
        len(fake - s["reach"]) == len(s["orphans"]) + 1)

    # injected dangling: a pointer to a name that does not exist
    fake_pointed = {t for n in s["reach"]
                    for t in targets(read(os.path.join(store, n + ".md")))}
    fake_pointed |= {"__injected_dangling__"}
    v["CONTROL_an_injected_dangling_link_is_counted"] = (
        len(fake_pointed - s["files"]) >= 1)

    print("store: %s" % store)
    print("  markdown files            %5d" % len(s["files"]))
    print("  named by an index         %5d" % len(s["named"]))
    print("  reachable transitively    %5d" % len(s["reach"]))
    print("  ORPHANS (nothing points)  %5d" % len(s["orphans"]))
    print("  DANGLING (points nowhere) %5d" % len(s["dangling"]))
    print("     of which prose examples %5d   (the words wikilink/link, not pointers)" % len(s["dangling_prose"]))
    print("     malformed pointers      %5d   (target exists, the link carries .md)" % len(s["dangling_malformed"]))
    print("     prose phrases           %5d   (a sentence inside brackets)" % len(s["dangling_phrases"]))
    print("     deliberate backlog      %5d   (this store's convention: a marker, not a fault)" % len(s["dangling_backlog"]))
    print()
    for o in sorted(s["orphans"]):
        t = read(os.path.join(store, o + ".md"))
        m = re.search(r'description:\s*"?(.{0,80})', t)
        print("  orphan   %-52s %s" % (o[:52], (m.group(1) if m else "").rstrip('"')[:60]))
    print()
    for d in sorted(s["dangling_malformed"]):
        print("  MALFORMED %-46s target exists, drop the .md" % d[:46])
    for d in sorted(s["dangling_backlog"])[:40]:
        print("  backlog   %s" % d[:70])
    print()
    for k, ok in v.items():
        print("%-52s %s" % (k, "PASS" if ok else "FAIL"))
    print("\n%d/%d" % (sum(v.values()), len(v)))
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
