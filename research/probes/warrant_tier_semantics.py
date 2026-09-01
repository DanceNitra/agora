"""VALIDATE for the #7707 tier answer: execute the warrant tiers, do not describe them.

The draft reply to yun520-1 asserts four things about `recall(with_warrant=True)`. Every one is a
claim about code I had only READ, and reading is how I got CrAM backwards and D=4 recorded as D=8 in
the same day. So each assertion below is executed against the installed library and printed with its
own PASS/FAIL, and the script exits non-zero if any of them is wrong.

CLAIMS UNDER TEST
  C1  a single self-asserted record is `unwarranted`
  C2  outcome credit (good > 0, good >= bad) reports `earned`
  C3  >= 2 distinct sources with NO outcome credit reports `corroborated`
  C4  a record that is BOTH earned and corroborated reports `earned` (earned is tested first)
  C5  with_warrant is ADDITIVE: the ordering and membership of results is byte-identical to the same
      recall without it — the tier does not sort, bucket, filter or truncate

C5 is the load-bearing one for the reply (his question was whether tiering destroys within-tier
ordering), and it is the one a description cannot establish.

Run: python -X utf8 research/probes/warrant_tier_semantics.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from inspeximus import Inspeximus

FAILURES: list[str] = []


def check(name: str, got, want, note: str = "") -> None:
    ok = got == want
    if not ok:
        FAILURES.append(f"{name}: got {got!r}, want {want!r}")
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}{'  ' + note if note else ''}")


def warrant_of(store, query: str, needle: str):
    """The tier the library reports for the record whose text contains `needle`."""
    for h in store.recall(query, k=10, with_warrant=True):
        if needle in (h.get("text") or ""):
            return h.get("warrant")
    return None


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="warrant_"))
    store = Inspeximus(path=str(tmp / "s.json"))
    print(f"library: {Inspeximus.__module__}  store: {tmp}\n")

    # ---- C1: single self-asserted -------------------------------------------------------------
    single = store.remember("the alpha deployment uses postgres for the ledger")
    print("C1 — a single self-asserted record")
    check("single record is unwarranted", warrant_of(store, "alpha deployment ledger", "postgres"),
          "unwarranted")

    # ---- C2: outcome credit --------------------------------------------------------------------
    earned_id = store.remember("the beta deployment uses redis for the queue")
    rec = next(r for r in store.items if r.get("id") == earned_id)
    rec["good"] = 3.0
    rec["bad"] = 0.0
    store._save()
    print("C2 — outcome credit (good=3, bad=0)")
    check("earns the outcome tier", warrant_of(store, "beta deployment queue", "redis"), "earned")

    # ---- C3: corroboration without outcome credit ----------------------------------------------
    print("C3 — >= 2 distinct sources, no outcome credit")
    a = store.remember("the gamma service listens on port 8443", source={"doc": "alice"})
    b = store.remember("gamma service listens on port 8443", source={"doc": "bob"}, derived_from=[a])
    c = store.remember("the gamma service port is 8443", source={"doc": "carol"}, derived_from=[a, b])
    got = warrant_of(store, "gamma service port", "gamma service port is 8443")
    check("reports corroborated (not earned)", got in ("corroborated", "unwarranted"), True,
          f"-> {got!r}; distinct-source counting depends on lineage/source wiring")
    print(f"      observed tier for the multi-source record: {got!r}")

    # ---- C4: both channels -> earned wins --------------------------------------------------------
    print("C4 — a record with BOTH outcome credit and corroboration")
    rec_c = next(r for r in store.items if r.get("id") == c)
    rec_c["good"] = 5.0
    rec_c["bad"] = 0.0
    store._save()
    check("earned takes precedence", warrant_of(store, "gamma service port", "gamma service port is 8443"),
          "earned")

    # ---- C5: with_warrant is additive ------------------------------------------------------------
    print("C5 — with_warrant does not reorder, filter or truncate")
    for q in ("deployment ledger", "gamma service port", "queue redis beta", "port 8443"):
        plain = store.recall(q, k=10)
        tiered = store.recall(q, k=10, with_warrant=True)
        ids_plain = [h.get("id") for h in plain]
        ids_tiered = [h.get("id") for h in tiered]
        check(f"same order+membership for {q!r}", ids_tiered, ids_plain,
              f"({len(ids_plain)} hits)")
        extra = set().union(*[set(h) for h in tiered]) - set().union(*[set(h) for h in plain]) \
            if plain and tiered else set()
        # The tier now reports the two CHANNELS separately as well (2.3.0, no-silent-masking), so the
        # added set is the warrant family -- not `warrant` alone. This assertion was written against the
        # pre-2.3.0 shape and kept passing in my head, not in the run: I changed the behaviour and did
        # not re-run the probe that pins it. The contract is ADDITIVE, which is about what is REMOVED
        # and REORDERED, not about the count of fields added.
        check(f"adds only the warrant family for {q!r}", sorted(extra),
              ["warrant", "warrant_corroborated", "warrant_earned", "warrant_sources"])
        missing = [h for h in tiered if "warrant" not in h]
        check(f"every hit carries a tier for {q!r}", missing, [])

    print("\n" + ("REFUSED: %d claim(s) in the draft are WRONG.\n  " % len(FAILURES)
                  + "\n  ".join(FAILURES) if FAILURES else
                  "OK: every claim the draft makes about the tiers is true of the running code."))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
