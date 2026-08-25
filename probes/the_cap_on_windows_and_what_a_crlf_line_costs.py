"""@pjt222's decisive arm, on Windows -- the one platform nobody in #82056 has measured.

WHY THIS EXISTS.

@pjt222 (anthropics/claude-code#82056, 2026-08-25) applied a ruler to every table in that thread
and disqualified most of it, ours included: `floor(25000 / units-per-line)` reproduces 13 of 14
size-bound published cells, so a model that read the index and never attended to where it was cut
produces the same table by arithmetic over a width it can see. Our `147 x 180 -> 168` is one of
those cells (`floor(25000/148) = 168`). So are our 198, 115 and 200.

His replacement is behavioural and it holds: invented VALUES rather than instructions (JhouCode's
six-for-six refusals show planted instructions get declined), needles flush to the line end,
classification on presence of the exact planted value and nothing else, three trials per needle, a
disk-only decoy asserting tool-zero behaviourally rather than trusting the flag. That yields
[24999, 25023), every bound measured, no truncation model assumed.

AND OUR OWN BEHAVIOURAL RUN OF THIS MORNING IS VOID, by his caveat 1, checked rather than conceded:
`the_cut_measured_by_what_the_index_DOES_not_what_it_says.py` put each needle at the START of its
line with padding after it. Line 168 spans 24,717-24,863 and `TWIRPAZ` occupies 24,804-24,810, so
"168 IN" proves only cap >= 24,810 -- 189 units below his measured floor of 24,999, which every
candidate cap already satisfies. It discriminated nothing while looking exactly like a result. And
line 169's word sits at 24,952-24,959, BELOW that same floor, so our "169 absent" has to be a false
negative if his floor is right. Our absence data is noise; his rule that only presence is evidence
is the reason we do not get to read it either way.

WHAT IS ACTUALLY OURS TO ADD. He is linux-x64, one machine, one operator. @JhouCode is linux-x64.
@tonydzi is darwin-arm64 and has annotated his own Windows figure as unverified. There is no
behavioural measurement off linux and mac anywhere in the thread, and he writes that "the only
cross-build evidence that survives is behavioural". So: his geometry, his controls, his classifier,
on Windows.

ARM 1 (this file, LF): 199 chars + LF = 200 units/line, 140 lines. Line 125's digits end at exactly
24,999 and its LF sits at 25,000. Needle rows reproduce his table cell for cell:

    line   3  digits   596-599    positive control
    line 124  digits 24796-24799  control, below the bracket
    line 125  digits 24996-24999  THE CLAIM
    line 126  digits 25196-25199  control, above the bracket
    line 138  digits 27596-27599  negative control
    (disk)    a fact only in a file in cwd, never in the index -- tool-leak control

ARM 2 (CRLF, run separately) is the part only Windows raises, and it is DISCRIMINATING rather than
reconstructible, which is the property his section 3 asks every arm to have. The identical 199-char
lines terminated CRLF cost 201 units if the harness counts the CR and 200 if it does not:

    CR counted      -> line 124 ends 24,924 IN,  line 125 ends 25,125 OUT
    CR not counted  -> line 125 ends 25,000 IN

Reading and the two truncation models predict different cells, so the arm cannot be satisfied by
arithmetic over a constant. CRLF is also the Windows-native case: an index written by an ordinary
editor here has it by default, which is the configuration real users are in and nobody has measured.

COST, stated before running because that is the rule here: 6 rows x 3 trials + 1 init = 19
`claude -p` sessions for this arm. Tools allowlisted to zero, asserted at init AND behaviourally by
the disk-only decoy, because a probe that can read MEMORY.md off disk is reading the file rather
than reporting its context.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import is_the_cap_counted_in_bytes_or_utf16_units as U  # noqa: E402

WIDTH = 199              # characters of content; + the terminator = the unit cost per line
LINES = 140
TRIALS = 3
EOL = "\n"               # ARM 1. The CRLF sibling runs from the same file with --crlf.

# Invented tokens carrying invented VALUES. A fabricated value is instantly distinguishable from
# the planted one, which a fabricated LINE NUMBER is not -- that is the whole reason this design
# beats canary echo, and @pjt222's one hallucination in 51 absent trials (9284 for a planted 8907)
# is what it looks like when it happens.
NEEDLES = {
    3:   ("ZORVAXQ", "8431"),
    124: ("PLIMWEK", "5207"),
    125: ("TWIRPAZ", "9163"),      # THE CLAIM: digits end at exactly 24,999
    126: ("BROQUEND", "6742"),
    138: ("YAMBRIXO", "3518"),
}
DECOY = ("SKELVUNT", "7096")       # on disk only, never in the index


def line_for(i: int) -> str:
    """One index line of exactly WIDTH characters, with any needle FLUSH to the end.

    Flush, and with no trailing period. @pjt222's caveat 2: a trailing period moves the bound one
    unit, and the honest figure is the position of the last character actually READ, so the digits
    must be the last thing on the line.
    """
    head = f"- [E{i:04d}](e-{i:04d}.md) "
    if i in NEEDLES:
        tok, val = NEEDLES[i]
        tail = f"CALIBRATION TOKEN {tok} VALUE {val}"
    else:
        tail = "routine index entry with no calibration token"
    pad = WIDTH - len(head) - len(tail)
    if pad < 1:
        raise SystemExit(f"REFUSED: line {i} does not fit in {WIDTH} characters")
    return head + ("x" * pad) + tail


def build(eol: str) -> str:
    return eol.join(line_for(i) for i in range(1, LINES + 1)) + eol


def digits_end(i: int, per_line: int) -> int:
    """The unit position of the LAST DIGIT of line i's planted value."""
    return (i - 1) * per_line + WIDTH


def ask(tok: str) -> str:
    return (f"What is the VALUE recorded for calibration token {tok}? "
            f"Reply with only the four-digit number, or the single word UNKNOWN if you do not "
            f"have it. Do not use any tool.")


def main() -> int:
    crlf = "--crlf" in sys.argv
    eol = "\r\n" if crlf else "\n"
    per_line = WIDTH + len(eol)
    text = build(eol)
    label = "CRLF" if crlf else "LF"
    t0 = time.time()

    print(f"  ARM {label}: {LINES} lines x {WIDTH} chars, terminator {len(eol)} unit(s) "
          f"-> {per_line} units/line, {len(text)} units total")
    for i in sorted(NEEDLES):
        print(f"    line {i:>3}  {NEEDLES[i][0]:<9} value {NEEDLES[i][1]}  "
              f"digits end at {digits_end(i, per_line)}")
    print(flush=True)

    v: dict = {}
    lines = text.split(eol)[:-1]
    v["every_line_is_exactly_the_declared_width"] = all(len(l) == WIDTH for l in lines)
    v["the_line_count_is_right"] = len(lines) == LINES
    v["each_planted_value_occurs_exactly_once"] = all(
        text.count(val) == 1 for _, val in NEEDLES.values())
    v["each_token_occurs_exactly_once"] = all(text.count(tok) == 1 for tok, _ in NEEDLES.values())
    v["the_decoy_is_NOT_in_the_index"] = DECOY[0] not in text and DECOY[1] not in text
    v["every_needle_is_FLUSH_to_its_line_end"] = all(
        lines[i - 1].endswith(NEEDLES[i][1]) for i in NEEDLES)
    v["the_file_is_over_the_size_cap"] = len(text) > 25200
    v["the_line_count_is_under_the_200_line_rule"] = LINES <= 200
    if not crlf:
        v["ARM_LF_line_125_digits_end_at_exactly_24999"] = digits_end(125, per_line) == 24999
    else:
        # The discriminating property: the two truncation models disagree about line 125.
        v["ARM_CRLF_is_discriminating_CR_counted_puts_125_out"] = 125 * per_line > 25100
        v["ARM_CRLF_is_discriminating_CR_ignored_would_put_125_in"] = 125 * (WIDTH + 1) == 25000
    if not all(v.values()):
        for k, ok in v.items():
            print(f"  {'YES' if ok else 'no '}  {k}")
        raise SystemExit("REFUSED: the fixture is wrong; no session below would be evidence")

    U.CLAUDE = U.claude_bin()
    root = tempfile.mkdtemp(prefix=f"cap{label.lower()}_")
    cwd = os.path.join(root, "arm")
    os.makedirs(cwd, exist_ok=True)
    # The disk-only decoy. If a session ever answers with 7096 it read a FILE, and every "IN" in
    # this run would be a disk read rather than a context read. Asserting the flag is not the same
    # as asserting the behaviour, which is @pjt222's point and the reason this row exists.
    io.open(os.path.join(cwd, "calibration_notes.txt"), "w", encoding="utf-8").write(
        f"CALIBRATION TOKEN {DECOY[0]} VALUE {DECOY[1]}\n")

    print(f"[{time.time() - t0:6.1f}s] init session", flush=True)
    store, _, offered, _ = U.run(cwd, "Reply with only: INIT")
    if offered:
        raise SystemExit(f"REFUSED: {len(offered)} tools offered: {offered[:8]}")
    if not store:
        raise SystemExit("REFUSED: the store path was not resolved")
    os.makedirs(store, exist_ok=True)
    with open(os.path.join(store, "MEMORY.md"), "wb") as f:
        f.write(text.encode("utf-8"))       # bytes: text mode would rewrite the terminator, which
    U.CREATED.append(store)                 # is the variable under test in the CRLF arm
    print(f"[{time.time() - t0:6.1f}s] wrote {len(text)} units, {len(text.encode())} bytes\n",
          flush=True)

    rows = []
    plan = [(i, NEEDLES[i][0], NEEDLES[i][1]) for i in sorted(NEEDLES)] + \
           [("disk", DECOY[0], DECOY[1])]
    for line_id, tok, val in plan:
        verdicts = []
        for t in range(1, TRIALS + 1):
            _, ans, off_i, used_i = U.run(cwd, ask(tok))
            ans = ans or ""
            # THE CLASSIFIER, and it is his: presence of the EXACT planted value, nothing else.
            # Not "said UNKNOWN" (three distinct absent-shapes appear, including a raw tool-call
            # block emitted as text) and not "returned a number" (1 in 51 absent trials fabricates
            # one, with truncation named as the reason it knew it -- exactly backwards).
            got = val in ans
            other = [x for x in re.findall(r"\b\d{4}\b", ans) if x != val]
            verdicts.append(got)
            rows.append({"line": line_id, "token": tok, "trial": t, "hit": got,
                         "other_4digit_numbers": other, "tools_offered": len(off_i),
                         "tool_uses": used_i, "reply": ans})
            print(f"[{time.time() - t0:6.1f}s]   line {str(line_id):>4} {tok:<9} "
                  f"trial {t}/{TRIALS}: {'IN ' if got else 'OUT'}"
                  f"{'  (fabricated ' + ','.join(other) + ')' if other and not got else ''}",
                  flush=True)
        n = sum(verdicts)
        print(f"[{time.time() - t0:6.1f}s]   -> line {line_id}: {n}/{TRIALS}\n", flush=True)

    def score(line_id):
        rs = [r for r in rows if r["line"] == line_id]
        return sum(1 for r in rs if r["hit"]), len(rs)

    print()
    for line_id, tok, _ in plan:
        n, k = score(line_id)
        end = digits_end(line_id, per_line) if line_id != "disk" else "-"
        print(f"  line {str(line_id):>4}  {tok:<9} digits end {str(end):>6}   {n}/{k}")

    v["CONTROL_the_positive_needle_is_3_of_3"] = score(3)[0] == TRIALS
    v["CONTROL_the_negative_needle_is_0_of_3"] = score(138)[0] == 0
    v["CONTROL_the_disk_decoy_was_NEVER_retrieved"] = score("disk")[0] == 0
    v["no_tool_was_offered_in_ANY_trial"] = all(r["tools_offered"] == 0 for r in rows)
    v["no_tool_was_used_in_ANY_trial"] = all(not r["tool_uses"] for r in rows)
    v["no_MIXED_cell_anywhere"] = all(
        score(x)[0] in (0, TRIALS) for x, _, _ in plan)

    lo = [digits_end(i, per_line) for i in NEEDLES if score(i)[0] == TRIALS]
    hi = [digits_end(i, per_line) for i in NEEDLES if score(i)[0] == 0]
    bound_lo = max(lo) if lo else None
    bound_hi = min(hi) if hi else None
    print(f"\n  cap >= {bound_lo}   (highest digits-end read in every trial)")
    print(f"  cap <  {bound_hi}   (lowest digits-end read in no trial)")
    print(f"  @pjt222's linux bracket: [24999, 25023)")

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       f"the_cap_on_windows_and_what_a_crlf_line_costs.{label.lower()}.result.json")
    json.dump({"probe": os.path.basename(__file__), "arm": label, "verdicts": v,
               "width": WIDTH, "lines": LINES, "units_per_line": per_line,
               "total_units": len(text), "trials_per_needle": TRIALS,
               "needles": {str(k): {"token": t, "value": val,
                                    "digits_end": digits_end(k, per_line)}
                           for k, (t, val) in NEEDLES.items()},
               "decoy": {"token": DECOY[0], "value": DECOY[1], "on_disk_only": True},
               "scores": {str(x): score(x) for x, _, _ in plan},
               "cap_lower_bound": bound_lo, "cap_upper_bound": bound_hi,
               "trials_detail": rows,
               "claude_version": U.subprocess.run([U.CLAUDE, "--version"], capture_output=True,
                                                  text=True, encoding="utf-8",
                                                  errors="replace").stdout.strip(),
               "platform": sys.platform},
              io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nwrote {out}")
    U.cleanup()
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
