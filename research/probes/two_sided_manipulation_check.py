"""Would the two-sided manipulation check have caught the id patch that nearly confirmed my hypothesis?

The failure being re-created: to test whether record ids drove a spread, I replaced the random id with
`f"{i:032x}"`. The store takes `hex[:10]`, and for every small i those ten characters are "0000000000" --
so every record got the SAME id. The arm collapsed (0.40 -> 0.0133), the spread went to zero, and that
reads exactly like a confirmed hypothesis.

The old gate asked one question: did the manipulation take effect? It had. The ids were exactly what I
wrote. It passed.

jacksonxly's correction (2026-07-27): the check wants to be TWO-SIDED -- the thing you meant to change
changed, AND nothing else did -- and the all-keys diff we already ran between two BUILDS is the instrument,
just pointed before-and-after the patch instead.

This runs both gates against both patches and prints what each one says. No network, no LLM, no dataset.

RUN:  python research/probes/two_sided_manipulation_check.py
"""
from __future__ import annotations

import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "..", "inspeximus-repo"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "..", "agora_output", "lab", "memops"))
from probe_gate import GateFailed, ProbeGate  # noqa: E402

N = 400


def build(id_fn):
    """One build of the same scenario. `id_fn(i)` supplies the record id, which is the manipulated field.

    Deliberately a plain dict store, not inspeximus: the point under test is the GATE, and using our own
    library here would make the demonstration depend on the thing it is meant to police.
    """
    records, seen = [], set()
    for i in range(N):
        rid = id_fn(i)[:10]                     # the store truncates, which is where the collapse happened
        if rid in seen:
            continue                            # ...and deduplicates, which is where the records went
        seen.add(rid)
        records.append({"id": rid, "text": f"fact number {i}", "key": f"k{i % 40}",
                        "object": f"v{i}", "status": "active", "mtype": "semantic",
                        "good": 0, "bad": 0})
    return records


def score(records):
    """A stand-in metric with the one property that matters: it degrades when records disappear."""
    return round(len({r["key"] for r in records}) / 40.0, 4)


def main() -> int:
    baseline = build(lambda i: uuid.uuid4().hex)

    honest = build(lambda i: f"{i:010x}" + "0" * 22)        # the fix: 10 DISTINCT hex chars
    broken = build(lambda i: f"{i:032x}")                   # the bug: hex[:10] == "0000000000" for all i

    print(f"records: baseline={len(baseline)}  honest-patch={len(honest)}  broken-patch={len(broken)}")
    print(f"score  : baseline={score(baseline)}  honest-patch={score(honest)}  "
          f"broken-patch={score(broken)}\n")

    rows = []
    for label, patched in (("honest patch (ids distinct)", honest),
                           ("broken patch (ids collapse)", broken)):
        one = ProbeGate(f"ONE-SIDED / {label}", operating_point={"n": N, "field": "id"})
        one.manipulation_landed("ids are the ones I wrote",
                                lambda p=patched: all(not r["id"].startswith("u") for r in p))
        one_ok = True
        try:
            one.report({"score": score(patched)})
        except GateFailed:
            one_ok = False

        two = ProbeGate(f"TWO-SIDED / {label}", operating_point={"n": N, "field": "id"})
        two.manipulation("only the id may move", before=baseline, after=patched, expect_changed=["id"])
        two_ok = True
        try:
            two.report({"score": score(patched)})
        except GateFailed:
            two_ok = False

        rows.append({"patch": label, "records": len(patched), "score": score(patched),
                     "one_sided_gate": "PASS" if one_ok else "FAIL",
                     "two_sided_gate": "PASS" if two_ok else "FAIL"})
        print()

    print("=" * 92)
    for r in rows:
        print(f"  {r['patch']:32s} records={r['records']:4d} score={r['score']:.4f}  "
              f"one-sided={r['one_sided_gate']}  two-sided={r['two_sided_gate']}")
    print("=" * 92)

    broken_row = next(r for r in rows if "broken" in r["patch"])
    honest_row = next(r for r in rows if "honest" in r["patch"])
    verdict_ok = (broken_row["one_sided_gate"] == "PASS" and broken_row["two_sided_gate"] == "FAIL"
                  and honest_row["two_sided_gate"] == "PASS")
    print("\nThe broken patch passes the one-sided gate and fails the two-sided one; the honest patch\n"
          "passes both. That is the whole claim." if verdict_ok else
          "\nMISMATCH: this demonstration does not show what it says it shows.")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "two_sided_manipulation_check_result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"n": N, "rows": rows, "verdict_reproduces": verdict_ok}, fh, indent=1)
    print(f"wrote {os.path.basename(out)}")
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
