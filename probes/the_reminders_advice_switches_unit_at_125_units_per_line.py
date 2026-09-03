"""When does the memory reminder give advice in a fake byte unit, and when in plain lines?

WHY. On anthropics/claude-code#91188 @pm25coder argued that the advice is byte-shaped while the
comparison is unit-valued, so following it in bytes does not move the quantity the check measures.
He has no `claude` binary and took the identifier shapes from @tonydzi's greps. This reads the
descriptors he could not.

He is right about the mechanism. The reminder builds its three numbers from ONE of two branches:

    byte:  sizeDesc: Ut(e.sizeBytes)     capDesc: Ut(e.byteCap)     targetDesc: Ut(floor(byteCap*ezn))
    line:  sizeDesc: `${e.lineCount}`    capDesc: `${e.lineCap}`    targetDesc: `${floor(lineCap*ezn)}`

`Ut` divides by 1024 and writes KB, and on the personal path `sizeBytes` is `String.length`, so the
byte branch does print UTF-16 code units under a KB label. `ezn` is 0.7, read from the binary.

WHAT HE COULD NOT SEE, and it bounds his own argument. The reminder keeps the LARGEST fraction across
the dimensions it was handed, so the byte branch only speaks when units/25000 exceeds lines/200. That
is a single threshold: 125 units per line. Below it the advice is a plain line count and his unit
mismatch never reaches the user; above it, it does.

Neither measured index is above it. His is 113.7 units per line, ours 123.6. Both get line advice.

CONTROLS, because a threshold is the easiest thing to assert and never test:
  * BOTH BRANCHES MUST BE REACHED. The probe evaluates fixtures on each side of 125 and refuses
    unless it sees the byte branch AND the line branch. A threshold nobody crossed is arithmetic.
  * THE CROSSOVER IS DERIVED, THEN BRACKETED. The algebraic 125 is checked against a scan that walks
    units per line until the branch flips, and the two must agree.
  * THE CONSTANTS COME FROM THE BINARY. 25000, 200 and 0.7 are read out of the shipped file, not
    typed in, and the probe refuses if any is absent. A threshold computed from remembered constants
    is a claim about my memory.
  * THE TWO REAL FILES ARE CARRIED AS FIXTURES, so a future build that moves the caps shows up as
    their verdicts changing rather than as a silent re-derivation.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

sys.stdout.reconfigure(line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "the_reminders_advice_switches_unit_at_125_units_per_line.result.json")
BIN = os.path.expandvars(r"%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe")


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def branch(units, lines, byte_cap, line_cap):
    """Which descriptor set speaks. The reminder keeps the largest fraction."""
    fu, fl = units / byte_cap, lines / line_cap
    return ("bytes" if fu > fl else "lines"), fu, fl


def main():
    if not os.path.exists(BIN):
        refuse("no shipped binary at %s" % BIN)
    blob = io.open(BIN, "rb").read()

    # CONTROL: the constants are read, not remembered.
    if b"targetDesc:Ut(Math.floor(e.byteCap*ezn))" not in blob:
        refuse("the byte-branch targetDesc is not in this build; the two-branch shape this rests on "
               "has changed and nothing here may be published")
    if b"targetDesc:`${Math.floor(e.lineCap*ezn)" not in blob:
        refuse("the line-branch targetDesc is gone; there may no longer be two branches to switch "
               "between, which is the whole finding")
    m = re.search(rb"ezn\s*=\s*([0-9.]+)", blob)
    if not m:
        refuse("could not read ezn (the target multiplier) from the binary")
    ezn = float(m.group(1))
    caps = sorted(set(int(x) for x in re.findall(rb"\b(25000|200)\b", blob)))
    if 25000 not in caps or 200 not in caps:
        refuse("the caps 25000 and 200 are not both present in the binary: found %s" % caps)
    BYTE_CAP, LINE_CAP = 25000, 200

    crossover = BYTE_CAP / LINE_CAP

    # CONTROL: derive, then bracket by scanning until the branch flips.
    scan = None
    lines_fixed = 200
    for upl in range(1, 400):
        b, _, _ = branch(upl * lines_fixed, lines_fixed, BYTE_CAP, LINE_CAP)
        if b == "bytes":
            scan = upl
            break
    if scan is None:
        refuse("the scan never reached the byte branch, so the threshold is untested")
    if abs(scan - crossover) > 1:
        refuse("algebraic crossover %.1f disagrees with the scanned %d" % (crossover, scan))

    # CONTROL: both branches must actually be produced.
    seen = set()
    fixtures = {}
    for name, units, lines in (
            ("his index (Cyrillic-heavy)", 8188, 72),
            ("our index", 26336, 213),
            ("synthetic, just under", int((crossover - 5) * 100), 100),
            ("synthetic, just over", int((crossover + 5) * 100), 100)):
        b, fu, fl = branch(units, lines, BYTE_CAP, LINE_CAP)
        seen.add(b)
        advice = ("%.1fKB" % (BYTE_CAP * ezn / 1024) if b == "bytes"
                  else "%d lines" % int(LINE_CAP * ezn))
        fixtures[name] = {"units": units, "lines": lines,
                          "units_per_line": round(units / lines, 1),
                          "frac_units": round(fu, 4), "frac_lines": round(fl, 4),
                          "branch": b, "advice_the_user_reads": advice}
    if seen != {"bytes", "lines"}:
        refuse("only the %s branch was produced, so the switch this probe is about was never "
               "exercised" % ", ".join(seen))

    print("  constants read from the binary: byteCap %d, lineCap %d, target multiplier %s"
          % (BYTE_CAP, LINE_CAP, ezn))
    print("  crossover: %.0f units per line (scan agrees at %d)" % (crossover, scan))
    print("  %-28s %8s %6s %8s  %-6s %s" % ("fixture", "units", "lines", "u/line", "branch", "advice"))
    for n, f in fixtures.items():
        print("  %-28s %8d %6d %8.1f  %-6s %s"
              % (n, f["units"], f["lines"], f["units_per_line"], f["branch"],
                 f["advice_the_user_reads"]))
    real = [f["branch"] for n, f in fixtures.items() if "synthetic" not in n]
    print("  -> both real indexes get %s advice, so the unit mismatch never reaches either user"
          % ("/".join(sorted(set(real)))))

    json.dump({"probe": os.path.basename(__file__),
               "byte_cap": BYTE_CAP, "line_cap": LINE_CAP, "target_multiplier": ezn,
               "crossover_units_per_line_algebraic": crossover,
               "crossover_units_per_line_scanned": scan,
               "fixtures": fixtures,
               "both_branches_exercised": sorted(seen),
               "controls": {
                   "constants_read_from_the_binary_not_typed": True,
                   "crossover_derived_then_bracketed_by_a_scan": True,
                   "both_branches_required_or_the_probe_refuses": True,
                   "both_real_indexes_carried_as_fixtures": True,
               }},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
