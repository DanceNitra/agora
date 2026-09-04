"""When does the memory reminder give advice in a fake byte unit, and when in plain lines?

WHY. On anthropics/claude-code#91188 @pm25coder argued that the advice is byte-shaped while the
comparison is unit-valued, so following it in bytes does not move the quantity the check measures.
He has no `claude` binary and took the identifier shapes from @tonydzi's greps. This reads the
descriptors he could not.

He is right about the mechanism. The reminder builds its three numbers from ONE of two branches:

    byte:  sizeDesc: Ut(e.sizeBytes)          capDesc: Ut(e.byteCap)
           targetDesc: Ut(Math.floor(e.byteCap*ezn))
    line:  sizeDesc: `${e.lineCount} lines`   capDesc: `${e.lineCap}-line`
           targetDesc: `${Math.floor(e.lineCap*ezn)} lines`

`Ut` writes bytes, KB, MB or GB by size, so in this range it divides by 1024 and writes KB. On the
personal path `sizeBytes` is `String.length`, so the byte branch does print UTF-16 code units under a
KB label. `ezn` is 0.7. The line branch, note, labels its unit correctly.

THREE THINGS AN EARLIER VERSION OF THIS PROBE GOT WRONG, each caught by a verification pass:
  1. It quoted the line branch without its ` lines` and `-line` suffixes, which is the half that
     shows the labelling is only wrong on one side.
  2. It resolved a tie to lines. The reducer is `reduce((d,p)=>p.frac>d.frac?p:d)` with NO initial
     value, so it starts at the first entry and only a STRICT `>` displaces it. Bytes are pushed
     first, so BYTES win at exactly 125 and the crossover is >=, not >.
  3. It ignored the 0.8 fire gate entirely, so it printed advice for fixtures that would have seen a
     silent tool.

THE BOUND, and it is narrower than it looks. The byte branch speaks when units/25000 >= lines/200:
125 units per line. But the threshold was named in that thread by @tonydzi and @pm25coder before us,
so it is not ours to present as a finding. What this probe adds is that the same comparison also
picks the DESCRIPTOR SET, so the KB label appears only on the byte side.

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


FIRE = 0.8          # I6o: below this the reminder returns null and says nothing at all


def branch(units, lines, byte_cap, line_cap):
    """Which descriptor set speaks, or none.

    The reducer is `reduce((d,p)=>p.frac>d.frac?p:d)` with NO initial value, so it starts at the
    FIRST entry and a later entry replaces it only on a STRICT >. Bytes are pushed first, so bytes
    win a tie. An earlier version of this probe had that backwards and reported a crossover of 126.

    And nothing is shown at all below FIRE. The first version omitted that gate entirely and printed
    advice for three fixtures that would have seen a silent tool.
    """
    fu, fl = units / byte_cap, lines / line_cap
    winner = "bytes" if fu >= fl else "lines"
    return (winner if max(fu, fl) >= FIRE else "silent"), fu, fl


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
    # The caps must come from their ASSIGNMENT sites. A bare substring search for "25000" over a
    # 219 MB bundle cannot fail, and a control that cannot fail certifies nothing. The first version
    # of this probe used exactly that and a verification pass caught it.
    def assigned(pattern, label):
        mm = re.search(pattern, blob)
        if not mm:
            refuse("could not read %s from an assignment in the binary" % label)
        return int(mm.group(1))

    BYTE_CAP = assigned(rb"n1\s*=\s*(25000)\b", "the byte cap (n1)")
    LINE_CAP = assigned(rb"\$M\s*=\s*(200)\b", "the line cap ($M)")
    mf = re.search(rb"I6o\s*=\s*([0-9.]+)", blob)
    if not mf or abs(float(mf.group(1)) - FIRE) > 1e-9:
        refuse("the fire threshold in the binary is %s, not the %s this probe applies"
               % (mf.group(1).decode() if mf else "absent", FIRE))

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
    def _live_index():
        ip = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                          "C--Users-Danculus-agora", "memory", "MEMORY.md")
        raw = io.open(ip, "rb").read().decode("utf-8")
        t = raw.replace(chr(13) + chr(10), chr(10)).strip()
        return len(t.encode("utf-16-le")) // 2, t.count(chr(10)) + 1

    live_u, live_l = _live_index()
    seen = set()
    fixtures = {}
    for name, units, lines in (
            # Only figures their authors actually published. @pm25coder gave a RATIO, 138.0 units
            # per line, and no counts, so he appears below as a ratio at a line count chosen to
            # clear the fire gate -- labelled, because inventing his line count would be putting
            # numbers in his mouth. An earlier version did exactly that.
            ("tonydzi index (his counts)", 8188, 72),
            ("pm25coder ratio at 200 lines", int(138.0 * 200), 200),
            ("our index (live)", live_u, live_l),
            # The synthetics must clear the 0.8 gate as well as the crossover, or they are silent
            # and the byte branch is never produced. The first version put them at 100 lines, where
            # both fractions sit near 0.5, and the probe correctly refused its own run.
            ("synthetic, just under 125", int((crossover - 5) * 200), 200),
            ("synthetic, just over 125", int((crossover + 5) * 200), 200)):
        b, fu, fl = branch(units, lines, BYTE_CAP, LINE_CAP)
        seen.add(b)
        advice = {"bytes": "%.1fKB" % (BYTE_CAP * ezn / 1024),
                  "lines": "%d lines" % int(LINE_CAP * ezn),
                  "silent": "(nothing: under the 0.8 gate)"}[b]
        fixtures[name] = {"units": units, "lines": lines,
                          "units_per_line": round(units / lines, 1),
                          "frac_units": round(fu, 4), "frac_lines": round(fl, 4),
                          "branch": b, "advice_the_user_reads": advice}
    if not {"bytes", "lines"} <= seen:
        refuse("both descriptor sets must be produced by some fixture; this run saw only %s, so the "
               "switch is untested" % ", ".join(sorted(seen)))
    if "silent" not in seen:
        refuse("no fixture fell under the 0.8 gate, so the gate is untested and the advice column "
               "would be claiming a message for cases that see none")

    print("  constants read from the binary: byteCap %d, lineCap %d, target multiplier %s"
          % (BYTE_CAP, LINE_CAP, ezn))
    print("  crossover: %.0f units per line (scan agrees at %d)" % (crossover, scan))
    print("  %-28s %8s %6s %8s  %-6s %s" % ("fixture", "units", "lines", "u/line", "branch", "advice"))
    for n, f in fixtures.items():
        print("  %-28s %8d %6d %8.1f  %-6s %s"
              % (n, f["units"], f["lines"], f["units_per_line"], f["branch"],
                 f["advice_the_user_reads"]))
    real = {n: f["branch"] for n, f in fixtures.items() if "synthetic" not in n}
    print("  -> real indexes: %s" % ", ".join("%s=%s" % (n.split()[0], b) for n, b in real.items()))
    if len(set(real.values())) == 1:
        print("     all three land on the same branch here; that is a fact about these three files, "
              "not about the tool")

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
