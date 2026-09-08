"""Can `gate_tier` still say FULL? Eleven cases, and the ones that must escalate are the point.

WHY THIS EXISTS. `tools/gate_tier.py` decides whether a draft's red-team and verify passes run as
subagent panels or through the Skill tool in this session. A classifier that drifts toward LIGHT
saves tokens by removing the depth of the pass, which is the failure this repository keeps having in
other shapes: a check that never sees its target reports safe.

So the control is asymmetric on purpose. Two cases must come back LIGHT, and nine must escalate. A
version of the classifier that answered LIGHT to everything would pass a suite made only of the
first two, which is why they are outnumbered.

TWO REAL DEFECTS THIS CONTROL CAUGHT, both false LIGHT:

  `#233` after a space   the address filter opened with `\\b`, which needs a word character on its
                         left, so it never matched a `#` preceded by a space. Every issue reference
                         leaked through as a figure, and the tier escalated when it should not have.
                         That one erred safe.
  `63.9%`                the same filter treated any two-part decimal as a version number and
                         stripped it, so a PERCENTAGE read as an address and the draft came back
                         LIGHT. That one erred the dangerous way, on the figure class we have
                         published wrong before.

WHAT THIS DOES NOT SHOW. That the tier is correct for prose. The classifier reads surface features,
so a claim written with no digit, no name and no citation reads LIGHT. The backstop is elsewhere:
LIGHT still requires all three receipts, so it lowers the depth of a pass and never its existence.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from gate_tier import classify  # noqa: E402

CASES = [
    ("a bare procedural note", "Rebased onto latest main and force-pushed, so the conflict is "
                               "resolved.", "LIGHT"),
    ("addresses are not figures", "Fixed in PR 10649 on 2026-09-08, version 1.2.3, see issue "
                                  "#233.", "LIGHT"),
    ("one figure", "Rebased onto latest main. The diff is 1 added line.", "FULL"),
    ("a percentage", "Recall improved to 63.9% on the same store.", "FULL"),
    ("a bare decimal", "The median was 0.85 seconds.", "FULL"),
    ("names a person", "Thanks @punkpeye, the branch is rebased.", "FULL"),
    ("a claim about their code", "Rebased. Your parser folds the raw dict away.", "FULL"),
    ("length alone", "word " * 130, "FULL"),
    ("a url", "See https://arxiv.org/abs/2608.07622 for the method.", "FULL"),
    ("an arxiv id", "Reported in arXiv:2608.07622 last month.", "FULL"),
    ("a long quotation", 'He wrote "the branch still needs a rebase before it can merge".', "FULL"),
]


def main():
    rows, ok = [], True
    for name, text, want in CASES:
        got, reasons = classify(text)
        passed = got == want
        ok = ok and passed
        rows.append({"case": name, "want": want, "got": got, "pass": passed,
                     "triggers": [r[0] for r in reasons]})
        print("  %-4s %-26s want %-5s got %-5s  %s"
              % ("YES" if passed else "NO", name, want, got,
                 ", ".join(r[0] for r in reasons) or "-"))

    n_full = sum(1 for c in CASES if c[2] == "FULL")
    print()
    # A suite of LIGHT cases alone would be passed by a classifier that never escalates.
    print("  %d of %d cases MUST escalate, so a classifier stuck on LIGHT fails this suite."
          % (n_full, len(CASES)))

    out = {"probe": os.path.basename(__file__), "cases": rows, "all_passed": ok,
           "must_escalate": n_full, "total": len(CASES),
           "note": "The classifier reads surface features. A claim in pure prose with no digit, "
                   "name or citation reads LIGHT; the backstop is that LIGHT still requires all "
                   "three receipts, so depth drops and the pass never disappears."}
    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("  %s   receipt: %s" % ("all cases behave as specified" if ok else "FAILED",
                                  os.path.basename(path)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
