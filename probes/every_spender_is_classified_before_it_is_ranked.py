"""Can an organ enter the spend ranking without anyone deciding whether it can be priced?

WHY. `roi_report` used to end every lookup with `value.get(organ, 0.0)`. An organ whose value key
the mapping could not reach therefore scored 0.0 and sat in the ranking beside an organ that
genuinely produced nothing. Those are opposite diagnoses wearing one number, and the churn detector
reads that number to decide what to rebuild.

Measured 2026-09-04 on the live store: all 10 spend organs read ROI 0.0 while 3,919 value points
sat in the ledgers. The cause was a vocabulary split. A spend label is a ROUTE name when the HTTP
middleware sets one and a MODULE name otherwise, and `_SPEND2VALUE` was written entirely against
route names, so `seminar`, `scan`, `match` and `directions` could never resolve.

WHAT THIS CHECKS:
  1. EVERY organ in the live store is classified, as `priced` or as `upstream` with a written
     reason. An unclassified organ is the defect this probe exists to catch.
  2. EVERY reason is a real sentence. A one-word exemption is a hole with a label on it.
  3. AN UNPRICED ORGAN CARRIES value None, never 0.0, so no reader can mistake "we cannot judge
     this" for "this produced nothing".
  4. MUTATION: an invented organ injected into the store must come back `unclassified`. A
     classifier that passes whatever it is given is the thing it is supposed to detect.
  5. CONTROL: a priced organ still gets a real number, otherwise check 3 would pass on a report
     that had simply stopped pricing anything.
"""
from __future__ import annotations

import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERVER = os.path.join(ROOT, "server")
OUT = os.path.join(HERE, "every_spender_is_classified_before_it_is_ranked.result.json")
sys.path.insert(0, SERVER)


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def main():
    from agora.execution import metabolism as M

    store = os.path.join(SERVER, ".metabolism.json")
    if not os.path.isfile(store):
        refuse("no .metabolism.json, so this check would pass by seeing no organs at all")

    r = M.roi_report()
    organs = r["organs"]
    if not organs:
        refuse("the store holds no organs, so every check below would pass vacuously")

    print("  organs in the live store: %d, spend %.1fk tokens" % (len(organs), r["total_ktok"]))
    for name, o in sorted(organs.items(), key=lambda kv: -kv[1]["ktok"]):
        print("     %-16s %8.1fk  %-13s value=%s" % (name, o["ktok"], o["cls"], o["value"]))

    # 1 + 3
    if r["unclassified"]:
        refuse("unclassified organ(s) in the ranking: %s. Classify each one in _SPEND2VALUE or in "
               "_NO_VALUE_LEDGER with a reason." % ", ".join(r["unclassified"]))
    for name, o in organs.items():
        if o["cls"] != "priced" and o["value"] is not None:
            refuse("%s is unpriced but carries value %r; an unpriced organ must read None so it "
                   "cannot be mistaken for one that produced nothing" % (name, o["value"]))

    # 2
    for organ, why in M._NO_VALUE_LEDGER.items():
        if len(why) < 30 or " " not in why:
            refuse("the reason for %r is %r, which is a label rather than a reason" % (organ, why))
    print()
    print("  every organ classified; every exemption carries a reason of >= 30 characters")

    # 5, the control: pricing must still work.
    priced = {k: v for k, v in organs.items() if v["cls"] == "priced"}
    if not priced:
        refuse("no organ is priced at all, so check 3 would pass on a report that prices nothing")
    print("  CONTROL: %d organ(s) still priced, e.g. %s -> value key %r"
          % (len(priced), *list(priced.items())[0][:1],
             list(priced.values())[0]["value_key"]))

    # 4, the mutation.
    raw = json.load(io.open(store, encoding="utf-8"))
    raw["a_brand_new_organ_nobody_classified"] = {"calls": 5, "tok_in": 100, "tok_out": 100}
    tmp = os.path.join(SERVER, ".metabolism.probe.json")
    json.dump(raw, io.open(tmp, "w", encoding="utf-8"))
    from pathlib import Path
    real = M._STORE
    M._STORE = Path(tmp)
    try:
        mutated = M.roi_report()
    finally:
        M._STORE = real
        os.remove(tmp)
    print()
    if "a_brand_new_organ_nobody_classified" not in mutated["unclassified"]:
        refuse("an invented organ was NOT reported as unclassified, so this check cannot see a new "
               "unpriced spender joining the ranking")
    print("  MUTATION: an invented organ was caught as unclassified")

    print()
    print("  window: %s   judgeable share: %s"
          % (("%s days" % r["window_days"]) if r.get("window_days")
             else "UNKNOWN (no first_ts recorded yet; it starts on the next call)",
             r["judgeable_share"]))
    print("  VERDICT: no organ can be ranked before it is classified.")

    json.dump({"script": os.path.basename(__file__),
               "organs": {k: {"ktok": v["ktok"], "cls": v["cls"], "value": v["value"]}
                          for k, v in organs.items()},
               "total_ktok": r["total_ktok"], "judgeable_share": r["judgeable_share"],
               "window_days": r["window_days"], "fails_total": r["fails_total"],
               "unclassified": r["unclassified"],
               "controls": {"mutation_caught": True, "pricing_still_works": len(priced),
                            "every_reason_is_a_sentence": True}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
