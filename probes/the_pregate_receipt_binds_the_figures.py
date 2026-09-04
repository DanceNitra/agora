"""Can a draft be sent carrying a figure the pre-check never saw?

WHY. `tools/pregate.py` checks CLAIMS before the prose exists, which is where seven of thirteen
gate refusals on 2026-09-04 should have been caught. Running it stayed a thing to remember, and a
thing to remember is a thing that gets skipped, so `send_approved` now refuses without it.

A receipt saying "the pre-check ran" would prove only that some claims were checked. It would not
prove the letter is made of them. So the receipt records the FIGURES it examined, and the send
compares them with the figures in the draft. The case that closes is the one that actually happens:
the claim list is cleared, and then a number nobody pre-checked is written into the prose anyway.

SIX CASES, five of which must refuse:
  1. no receipt at all
  2. a receipt that still has blocked claims
  3. a receipt missing some of the draft's figures, which must be NAMED in the refusal
  4. a complete receipt for a DIFFERENT thread
  5. a complete receipt for this thread, which must PASS
  6. the receipt removed again, to show case 5 was the receipt and not a cached decision

Case 5 is the load-bearing one. A gate that refuses everything is not a gate, it is an outage, and
it gets switched off within a day.
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "the_pregate_receipt_binds_the_figures.result.json")
D = os.path.join(ROOT, "agora_output", "pregate")
DRAFT = os.path.join(ROOT, "drafts", "edrn_table2_consequence.md")
THREAD = "luoxuejian000/edrn-dmrg-verification#2"
sys.path.insert(0, os.path.join(ROOT, "tools"))


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def main():
    import send_approved as sa
    if not os.path.isfile(DRAFT):
        refuse("no draft at %s, so every case below would grade an empty file" % DRAFT)
    os.makedirs(D, exist_ok=True)
    for f in glob.glob(os.path.join(D, "_probe*.json")):
        os.remove(f)

    body = io.open(DRAFT, encoding="utf-8").read()
    nums = sorted(set(re.findall(r"(?<![\w.])(\d+\.\d{3,}|\d{4,})(?![\w.])", body)))
    if len(nums) < 6:
        refuse("the draft carries only %d distinctive figures, too few for case 3 to remove three "
               "and still mean anything" % len(nums))
    print("  draft carries %d distinctive figures" % len(nums))

    def write(name, **kw):
        json.dump(dict(tool="pregate", **kw),
                  io.open(os.path.join(D, name), "w", encoding="utf-8"))

    def clear():
        for f in glob.glob(os.path.join(D, "_probe*.json")):
            os.remove(f)

    cases, ok = [], True
    def case(label, must_refuse, setup):
        nonlocal ok
        clear()
        setup()
        why = sa._pregate_gate_impl(DRAFT, THREAD)
        good = (why is not None) == must_refuse
        ok = ok and good
        cases.append({"case": label, "must_refuse": must_refuse,
                      "refused": why is not None, "why": (why or "")[:200], "ok": good})
        print("  %-4s %-38s %s" % ("ok" if good else "FAIL", label,
                                   (why[:64] if why else "passes")))
        return why

    case("1. no receipt at all", True, lambda: None)
    case("2. receipt with blocked claims", True,
         lambda: write("_probe_blocked.json", thread=THREAD, blocked=2, numbers_examined=nums))
    why3 = case("3. receipt missing three figures", True,
                lambda: write("_probe_partial.json", thread=THREAD, blocked=0,
                              numbers_examined=nums[:-3]))
    for n in nums[-3:]:
        if n not in (why3 or ""):
            refuse("case 3 refused without naming the missing figure %s, so the operator cannot "
                   "act on it" % n)
    print("       and it named the missing figures")
    case("4. complete receipt, WRONG thread", True,
         lambda: write("_probe_wrong.json", thread="someone/else#9", blocked=0,
                       numbers_examined=nums))
    case("5. complete receipt (must PASS)", False,
         lambda: write("_probe_ok.json", thread=THREAD, blocked=0, numbers_examined=nums))
    case("6. removed again", True, lambda: None)
    clear()

    print()
    if not ok:
        refuse("at least one case behaved backwards; see the table above")
    print("  VERDICT: the receipt binds the figures, and a complete one still lets work through.")
    json.dump({"script": os.path.basename(__file__), "draft_figures": len(nums), "cases": cases,
               "controls": {"a_complete_receipt_passes": True,
                            "missing_figures_are_named": True,
                            "wrong_thread_does_not_count": True}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
