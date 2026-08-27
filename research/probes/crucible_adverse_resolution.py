"""What share of our own replications ruled AGAINST the claim we tested?

WHY THIS EXISTS. The falsifiable question to put to any outcome-conditioned trust scheme is not "are the
warrants checkable" but "what share of them ever resolved against the writer". A ledger whose adverse
fraction sits near zero has measured SELECTION, not accountability. It is cheap to compute and nobody
publishes it, so this publishes ours.

It is deliberately a count over the PUBLISHED artifact (public/crucible/crucible.json), not over an
internal store: a reader can fetch the same file and get the same answer without trusting us. There is no
parameter to sweep and no model to run -- the only way this number moves is if the ledger moves.

WHAT IT DOES NOT SHOW, and this is the honest half. It reports the adverse fraction of claims we CHOSE to
replicate. We pick the claims, so the denominator is ours; a low number here would be consistent with
either honesty or with only ever testing safe claims, and this script cannot separate those. The
complementary check is whether the ledger is complete (nothing withdrawn after an unwelcome result), which
lives in the ledger's own history, not here.

Exit 0 with the numbers, non-zero if the artifact is missing or unreadable -- an absent ledger must not
read as a clean one.
"""
from __future__ import annotations

import collections
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "public" / "crucible" / "crucible.json"

#: Verdicts that are a RULING on the claim. NOT_COMPUTABLE and RETRACTED are not rulings -- the first
#: says we could not decide, the second withdraws an entry -- so they belong in the overall denominator
#: and not in the computable one.
DECIDED = ("REPRODUCED", "FAILED")
ADVERSE = "FAILED"


def main() -> int:
    if not LEDGER.exists():
        print("REFUSED: %s is missing. An absent ledger is not an empty one." % LEDGER)
        return 2
    try:
        doc = json.load(io.open(LEDGER, encoding="utf-8", errors="replace"))
    except Exception as ex:
        print("REFUSED: %s is unreadable (%s)" % (LEDGER.name, type(ex).__name__))
        return 2

    entries = doc.get("entries") if isinstance(doc, dict) else doc
    if not isinstance(entries, list) or not entries:
        print("REFUSED: no entries in %s -- a count over nothing is not a measurement." % LEDGER.name)
        return 2

    counts = collections.Counter(e.get("verdict") for e in entries)
    total = len(entries)
    decided = sum(counts.get(v, 0) for v in DECIDED)
    adverse = counts.get(ADVERSE, 0)

    print("ledger: %s" % LEDGER.relative_to(ROOT).as_posix())
    print("entries: %d" % total)
    for verdict, n in sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        print("   %-16s %d" % (verdict, n))
    print()
    print("MEASURED: adverse_overall    = %d/%d = %.1f%%" % (adverse, total, 100.0 * adverse / total))
    if decided:
        print("MEASURED: adverse_decided    = %d/%d = %.1f%%" % (adverse, decided,
                                                                 100.0 * adverse / decided))
    else:
        print("MEASURED: adverse_decided    = n/a (no REPRODUCED/FAILED rulings)")

    print()
    print("VERDICT: %d of %d published replications ruled against the claim tested (%d of %d among "
          "those we could decide at all). The denominator is our own choice of claims, so this bounds "
          "selection from one side only." % (adverse, total, adverse, decided))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
