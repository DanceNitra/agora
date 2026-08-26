"""Which of our 73 shipped capabilities does the outside world actually ask for, and which none.

WHY. Inbox task 89eece asks where external demand and what we have built MEET, and where we are
building for a need nobody voices. The brain already has a map for this (`/brain/library/external/map`)
and it answers the first half well: eight needs, every one of them raised in 13 to 35 unrelated
projects. It cannot answer the second half, and the reason is not a bug in its logic -- I checked,
`buckets` IS pre-seeded from AXIS, so a zero-mention need would come through. The reason is its
INPUT. AXIS is a hand-written list of eight needs, and all eight were chosen because we build them.
A capability of ours that is missing from that list is invisible to the question "is anyone asking
for this", and 65 of our 73 are missing from it.

So this replaces the curated input with the complete one: every tool inspeximus actually exposes,
read from the source rather than from a list I would write from memory. That is the same lesson as
[[a-generator-is-only-as-complete-as-its-input]], which cost us a live essay three days ago.

WHAT IS MEASURED. For each MCP tool, its name is split into content tokens (`erasure_certificate`
-> erasure, certificate) after dropping the plumbing words that carry no demand signal (report,
check, get, set, list). A corpus item mentions the capability when every content token appears in
its text or title. Distinct PROJECTS are counted, not mentions: one loud repo is a customer, the
same ask in six unrelated repos is a market.

WHAT IT CANNOT DO, stated because the number is otherwise easy to over-read: token containment is
a crude matcher, and a project asking for "the ability to take something back" will not match
`revert`. A zero here means nobody used our word, not that nobody has the need. That asymmetry
matters for the conclusion, so it is reported with the number rather than under it.

CONTROLS, all of which can fail:
  * POSITIVE: capabilities we know are voiced (`recall`, `forget`, `revert`) must come back
    non-zero, or the matcher is dead and every zero below is an artefact.
  * NEGATIVE: an invented capability name must come back zero, or the matcher matches anything.
  * the corpus must be non-empty and carry more than one repo, or "distinct projects" means nothing.
  * the tool list must be read from source and be large; a short list would quietly re-create the
    curated-input defect this file exists to remove.
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.join(os.path.expanduser("~"), "inspeximus-repo")
sys.path.insert(0, os.path.join(ROOT, "server"))

# Words that name plumbing rather than a need. Dropping them is what lets `erasure_report` and
# `erasure_certificate` both count toward "does anyone ask about erasure".
PLUMBING = {"report", "check", "get", "set", "list", "log", "logs", "as", "of", "the", "a",
            "state", "digest", "index", "line", "code", "symbol"}


def tools() -> list:
    names = set()
    for p in glob.glob(os.path.join(REPO, "inspeximus", "*.py")):
        t = io.open(p, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"@(?:app|server|mcp)\.tool[^\n]*\n\s*(?:async )?def ([a-z][a-z0-9_]+)\(",
                             t):
            names.add(m.group(1))
    return sorted(names)


def tokens(name: str) -> list:
    return [w for w in name.split("_") if w not in PLUMBING and len(w) > 2]


def corpus() -> list:
    from agora.execution.external_library import _inspeximus
    rows = []
    for r in _inspeximus().items:
        meta = r.get("meta") or {}
        rows.append({"blob": ((r.get("text") or "") + " " + str(meta.get("title") or "")).lower(),
                     "repo": meta.get("repo") or meta.get("source") or ""})
    return rows


def main() -> int:
    items = corpus()
    names = tools()
    repos = {r["repo"] for r in items if r["repo"]}

    def projects_for(toks: list) -> set:
        if not toks:
            return set()
        return {r["repo"] for r in items
                if r["repo"] and all(t in r["blob"] for t in toks)}

    rows = []
    for n in names:
        toks = tokens(n)
        p = projects_for(toks)
        rows.append({"tool": n, "tokens": toks, "projects": len(p),
                     "examples": sorted(p)[:4]})
    rows.sort(key=lambda r: (-r["projects"], r["tool"]))
    voiced = [r for r in rows if r["projects"] > 0]
    silent = [r for r in rows if r["projects"] == 0 and r["tokens"]]
    untestable = [r for r in rows if not r["tokens"]]

    v = {}
    v["CONTROL_the_corpus_is_real"] = len(items) > 300 and len(repos) > 20
    v["CONTROL_the_tool_list_came_from_source_and_is_large"] = len(names) > 50
    v["POSITIVE_CONTROL_known_needs_are_voiced"] = all(
        projects_for([w]) for w in ("recall", "forget", "revert", "provenance"))
    v["NEGATIVE_CONTROL_an_invented_capability_is_silent"] = not projects_for(
        ["zorbulate", "frobnicate"])
    v["CONTROL_every_tool_was_scored"] = len(rows) == len(names)

    print("  corpus %d items across %d projects | %d tools read from source"
          % (len(items), len(repos), len(names)))
    print("  VOICED %d   SILENT %d   untestable(name is all plumbing) %d\n"
          % (len(voiced), len(silent), len(untestable)))
    print("  --- ours that the outside world is asking for ---")
    for r in voiced[:14]:
        print("   %-26s %3d projects  %s" % (r["tool"], r["projects"],
                                             ", ".join(r["examples"])[:56]))
    print("\n  --- ours that nobody in 392 items voices, by our own words ---")
    for r in silent[:26]:
        print("   %-26s tokens=%s" % (r["tool"], ",".join(r["tokens"])))

    print()
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))

    json.dump({"probe": os.path.basename(__file__), "controls": v,
               "corpus_items": len(items), "corpus_projects": len(repos),
               "tools": len(names), "voiced": len(voiced), "silent": len(silent),
               "rows": rows,
               "question": "inbox 89eece: where do external demand and what we built meet, and "
                           "where are we building for a need nobody voices",
               "why_the_brains_own_map_cannot_answer_half_of_it":
                   "/brain/library/external/map scores an 8-item hand-written AXIS, and all eight "
                   "were chosen because we build them; 65 of our 73 tools are absent from it, so "
                   "'is anyone asking for this' was never askable about them",
               "limit": "token containment is crude: a project asking for 'take it back' does not "
                        "match `revert`, so a zero means nobody used OUR WORD, not that the need "
                        "is absent"},
              io.open(os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json")),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
