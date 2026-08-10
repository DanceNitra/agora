"""Could WE detect staleness in our own memory index? Measured on the production stores, not a simulation.

WHY THIS EXISTS. A researcher asked how teams find stale content before a user sees a wrong answer.
The method we advocate is the only one that works for deletions: enumerate the SOURCE and diff against
the index, because a deleted document emits exactly one event and an index-side query cannot notice
something that is missing from it. Before recommending that to anyone, we ran it against ourselves.

WHAT IT MEASURES, over every inspeximus store on this machine:
  * how many records exist;
  * how many carry a `source` at all;
  * how many carry a source that RESOLVES to something re-checkable -- a path, a URL, a document id
    you could fetch again -- as opposed to a writer identity like `agent:scholar` or `seminar:9f3a`.

The second and third numbers are the whole point. A `source` field at 100% coverage looks like
provenance and answers nothing if what it holds is the name of the writer. Reconciliation is then not
"unimplemented" but structurally impossible: there is no key to diff against.

CONTROL: the resolver is run against strings that MUST classify as re-checkable (a vault path, an
https URL, a DOI, an arXiv id). If those do not classify, the classifier is broken and a 0% result
below would be an artefact of the instrument rather than a fact about the stores.

Exit 0 with the table. Read the RESOLVABLE column, not the coverage column.
"""
from __future__ import annotations

import io
import json
import os
import re
from collections import Counter

HOME = os.path.expanduser("~")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CANDIDATES = [
    os.path.join(HOME, ".inspeximus", "mcp_memory.json"),
    os.path.join(ROOT, "server", ".inspeximus_brain.json"),
]
CANDIDATES += [os.path.join(ROOT, "agora-game-server", ".agent_memory", f)
               for f in ("scholar.json", "king.json", "thief.json", "priest.json",
                         "guard_l.json", "guard_r.json", "artificer.json", "cartographer.json")]

#: A source is RE-CHECKABLE if you could go back to it and see whether it still says the same thing.
_RECHECKABLE = re.compile(
    r"^(https?://"                      # a URL
    r"|doi:|10\.\d{4,}/"                # a DOI
    r"|arxiv:|\d{4}\.\d{4,5}"           # an arXiv id
    r"|[a-zA-Z]:[\\/]"                  # an absolute Windows path
    r"|[\\/])"                          # an absolute POSIX path
    r"|.*\.(md|pdf|txt|html?|docx?|csv|json)$",   # a filename
    re.I)

CONTROL_MUST_RESOLVE = [
    r"C:\Users\Danculus\my-second-brain\04 Resources\Concepts\Phase_Transitions.md",
    "https://arxiv.org/abs/2401.05856",
    "10.5281/zenodo.21875878",
    "runbook.md",
]
CONTROL_MUST_NOT = ["agent:scholar", "seminar:fcf6366e", "", "king"]


def _doc(rec):
    s = rec.get("source")
    if isinstance(s, dict):
        return s.get("doc") or s.get("url") or s.get("path")
    return s if isinstance(s, str) else None


def main() -> int:
    for c in CONTROL_MUST_RESOLVE:
        assert _RECHECKABLE.match(c), "CONTROL FAILED: %r should classify as re-checkable" % c
    for c in CONTROL_MUST_NOT:
        assert not (c and _RECHECKABLE.match(c)), "CONTROL FAILED: %r must NOT classify" % c
    print("classifier control: 4 re-checkable forms accepted, 4 identity forms rejected\n")

    tot = has = res = 0
    kinds = Counter()
    print("  %-34s %9s %9s %11s" % ("store", "records", "source", "RESOLVABLE"))
    for p in CANDIDATES:
        if not os.path.exists(p):
            print("  %-34s %9s" % (os.path.basename(p), "(absent)"))
            continue
        raw = json.load(io.open(p, encoding="utf-8"))
        items = raw["items"] if isinstance(raw, dict) and "items" in raw else raw
        n = len(items)
        h = r = 0
        for rec in items:
            d = _doc(rec)
            if d:
                h += 1
                kinds[str(d).split(":")[0][:18] if ":" in str(d) else "(other)"] += 1
                if _RECHECKABLE.match(str(d)):
                    r += 1
        tot += n; has += h; res += r
        print("  %-34s %9d %8.1f%% %10.2f%%"
              % (os.path.basename(p), n, 100 * h / n if n else 0, 100 * r / n if n else 0))

    print("\n  %-34s %9d %8.1f%% %10.2f%%"
          % ("TOTAL", tot, 100 * has / tot if tot else 0, 100 * res / tot if tot else 0))
    print("\n  most common source PREFIXES (what the field actually holds):")
    for k, c in kinds.most_common(6):
        print("     %-20s %8d" % (k, c))

    print("\nMEASURED: %d records; source coverage %.1f%%; RE-CHECKABLE source %.2f%% (%d records)."
          % (tot, 100 * has / tot if tot else 0, 100 * res / tot if tot else 0, res))
    if res == 0:
        print("\nVERDICT: source-diff reconciliation is not unimplemented here -- it is IMPOSSIBLE."
              "\n         Every record names its WRITER, not its origin, so there is no key to diff"
              "\n         against a source of truth. A field at 100% coverage that cannot answer the"
              "\n         question it appears to answer is the failure this probe exists to find, and"
              "\n         it is ours.")
    else:
        print("\nVERDICT: %d records could be reconciled against a source; the rest could not." % res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
