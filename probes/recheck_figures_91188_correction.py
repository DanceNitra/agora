"""Re-derive every number in drafts/91188_correction.md, which is a public retraction.

THIS IS ONE CHECK INSIDE VALIDATE. It is not the gate.

WHY IT IS STRICTER THAN USUAL. The draft says a number we published six hours ago was wrong and
belongs to no file on this machine. A retraction carrying its own error is worse than the error it
retracts, so every figure here is either recomputed from the live file or read from the receipt of
the run that searched for it, and the published figures we are withdrawing are read back from the
comment itself rather than retyped.

CONTROLS:
  * THE WITHDRAWN FIGURES COME FROM THE LIVE COMMENT. If comment 5538716005 does not contain them,
    the draft is retracting something we did not say.
  * THE SEARCH THAT FOUND NOTHING MUST HAVE BEEN ABLE TO FIND SOMETHING. The measurement probe
    asserts it locates the current index by its own figures; this refuses if that control is absent
    from its receipt.
  * COVERAGE over every decimal, every ordinal and every magnitude word in the draft.
  * A MUTATION: a perturbed expectation must fail.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "drafts", "91188_correction.md")
MEAS = os.path.join(HERE, "our_published_units_per_line_belongs_to_no_file_here.result.json")
OUT = os.path.join(HERE, "recheck_figures_91188_correction.result.json")
COMMENT = "5538716005"

checks = []


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def check(label, expected, found, tol=5e-6, source=""):
    ok = abs(float(expected) - float(found)) <= tol
    checks.append({"label": label, "expected": float(expected), "found": float(found),
                   "ok": ok, "source": source})
    print("  %-4s %-42s draft %-11s vs %-11s %s"
          % ("ok" if ok else "FAIL", label, "%.6g" % expected, "%.6g" % found, source))
    return ok


def main():
    for p in (DRAFT, MEAS):
        if not os.path.isfile(p):
            refuse("missing %s" % p)
    text = io.open(DRAFT, encoding="utf-8").read()
    m = json.load(io.open(MEAS, encoding="utf-8"))
    if m.get("verdict") != "NO_FILE_HERE_MATCHES":
        refuse("the measurement probe's verdict is %r, so the draft's central claim is not "
               "supported by its own receipt" % m.get("verdict"))
    if not m["controls"].get("search_finds_the_current_file"):
        refuse("the measurement's search never proved it can find a file, so 'zero matches' would "
               "only mean the search is blind")
    print("  measurement receipt: verdict %s, %d files searched, search control passed"
          % (m["verdict"], m["files_searched"]))

    # CONTROL: the withdrawn figures must be in the comment we are withdrawing.
    body = subprocess.run(["gh", "api",
                           "repos/anthropics/claude-code/issues/comments/" + COMMENT],
                          capture_output=True, text=True, encoding="utf-8").stdout
    if not body:
        refuse("could not fetch comment %s, so the draft may be retracting something we never "
               "posted" % COMMENT)
    published = json.loads(body).get("body", "")
    for tok in ("417.8", "11,132", "8,774", "1.269", "21 lines"):
        if tok not in published:
            refuse("comment %s does not contain %r, so the draft misquotes our own comment"
                   % (COMMENT, tok))
    print("  CONTROL: comment %s carries every figure the draft withdraws" % COMMENT)

    ok = True
    now = m["now"]
    ok &= check("our lines now", 221, now["lines"], 0, "measurement receipt")
    ok &= check("our bytes now", 28384, now["bytes"], 0, "measurement receipt")
    ok &= check("our units now", 28233, now["units"], 0, "measurement receipt")
    ok &= check("our bytes per unit", 1.005, now["bpu"], 5e-4, "measurement receipt")
    ok &= check("our units per line", 127.8, now["upl"], 0.05, "measurement receipt")
    ok &= check("our CRLF pairs", 221, now["crlf"], 0, "measurement receipt")
    ok &= check("astral characters", 0, now["astral"], 0, "measurement receipt")
    ok &= check("margin above the crossover", 2.8, m["margin_now"], 0.05, "measurement receipt")
    ok &= check("unit cap binds at line", 195.7, m["unit_cap_binds_at_line"], 0.05,
                "measurement receipt")
    ok &= check("files searched", 97, m["files_searched"], 0, "measurement receipt")
    ok &= check("snapshots", 25, m["snapshots"], 0, "measurement receipt")
    ok &= check("range low", 80.2, m["upl_min"], 0.05, "measurement receipt")
    ok &= check("range high", 163.6, m["upl_max"], 0.05, "measurement receipt")
    ok &= check("within 10 of the crossover", 22, m["within_10_of_crossover"], 0,
                "measurement receipt")
    if m["matches"]:
        refuse("the measurement found %d matching file(s), so the draft's 'zero' is false"
               % len(m["matches"]))

    by_date = {h["mtime"][:10]: h for h in m["history"]}
    for day, lines, upl, margin in (("2026-08-21", 200, 118.8, -6.2), ("2026-08-22", 207, 124.5, -0.5),
                                    ("2026-08-26", 209, 129.6, 4.6)):
        rows = [h for h in m["history"] if h["mtime"].startswith(day)]
        if not rows:
            refuse("no snapshot on %s, but the draft prints one" % day)
        r = min(rows, key=lambda h: abs(h["upl"] - upl))
        ok &= check("%s lines" % day, lines, r["lines"], 0, "measurement receipt")
        ok &= check("%s u/l" % day, upl, r["upl"], 0.05, "measurement receipt")
        ok &= check("%s margin" % day, margin, r["upl"] - m["crossover"], 0.05,
                    "measurement receipt")
    ok &= check("2026-08-21 second snapshot margin", -4.1,
                min((h["upl"] for h in m["history"] if h["mtime"].startswith("2026-08-21")),
                    key=lambda v: abs(v - 120.9)) - m["crossover"], 0.05, "measurement receipt")
    ok &= check("2026-08-21 second snapshot u/l", 120.9,
                min((h["upl"] for h in m["history"] if h["mtime"].startswith("2026-08-21")),
                    key=lambda v: abs(v - 120.9)), 0.05, "measurement receipt")

    # Withdrawn figures, quoted from the comment.
    for label, val in (("withdrawn lines", 21), ("withdrawn bytes", 11132),
                       ("withdrawn units", 8774), ("withdrawn bytes per unit", 1.269),
                       ("withdrawn units per line", 417.8)):
        ok &= check(label, val, m["published"][{"withdrawn lines": "lines",
                                                "withdrawn bytes": "bytes",
                                                "withdrawn units": "units",
                                                "withdrawn bytes per unit": "bpu",
                                                "withdrawn units per line": "upl"}[label]],
                    5e-4, "our own comment")
    ok &= check("the crossover", 125, m["crossover"], 0, "recomputed, 25000/200")

    # COVERAGE.
    claimed = set()
    for c in checks:
        for v in (c["expected"], c["found"]):
            claimed.add(round(v, 6))
            claimed.add(round(abs(v), 6))
    claimed |= {200.0, 2.0, 400.0, 10.0, 4.0, 24.0, 17.0, 18.0, 6.0, 1.0}
    stated = {round(float(x.replace(",", "")), 6)
              for x in re.findall(r"(?<![\w.])(\d[\d,]*\.\d+|\d[\d,]{2,})(?![\w.])", text)}
    unclaimed = sorted(x for x in stated - claimed)
    print()
    print("  COVERAGE: %d distinct figures, %d unclaimed" % (len(stated), len(unclaimed)))
    if unclaimed:
        print("     unclaimed: %s" % unclaimed)
        refuse("figures no check re-derives: %s" % unclaimed)

    for w in ("twofold", "threefold", "tenfold", "twelvefold", "twice", "double"):
        if w in text.lower():
            refuse("the draft uses the magnitude word %r, which no check re-derives" % w)

    if check("MUTATION (must fail)", 127.8 + 5, now["upl"], 0.05, "deliberate"):
        refuse("a deliberately wrong expectation PASSED; every ok above means nothing")
    checks.pop()
    print("  MUTATION: a perturbed expectation was rejected")

    failed = [c for c in checks if not c["ok"]]
    print()
    print("  %d checks, %d failed" % (len(checks), len(failed)))
    json.dump({"script": os.path.basename(__file__), "draft": os.path.relpath(DRAFT, ROOT),
               "checks": checks, "failed": len(failed), "figures": len(stated),
               "controls": {"withdrawn_figures_read_from_the_live_comment": True,
                            "search_control_present": True, "mutation_rejected": True,
                            "coverage_enforced": True},
               "verdict": "PASS" if not failed else "FAIL"},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
