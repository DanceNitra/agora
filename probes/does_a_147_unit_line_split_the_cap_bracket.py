"""The one width that narrows the cap bracket, which @JhouCode asked for and cannot run himself.

The bracket from our four published arms is [24955, 25074) UTF-16 units, and @pjt222's point is
that collecting more widths does not converge: every width whose line boundaries fall OUTSIDE that
interval leaves it exactly as wide as it was. Three of our widths (126, 61, 217) did nothing to it
for that reason. A width helps only if one of its line boundaries lands INSIDE the interval.

  line cost = width + 1, because the newline counts. Measured, not assumed: the published
  ascii_200x125 arm is 200 lines of 125 characters and reports 25,200 units, which is 200 x 126.

At 147 characters a line costs 148 units, and the cumulative totals are

  line 168 ends at 24,864   <- below the bracket
  line 169 ends at 25,012   <- INSIDE [24955, 25074)
  line 170 ends at 25,160   <- above the bracket

so a single arm splits it, whichever way it falls:

  last kept 168  ->  cap is in [24955, 25012)
  last kept 169  ->  cap is in [25012, 25074)

180 lines, so the file totals 26,640 units and a size cut is guaranteed, while staying under the
200-line cap that would otherwise pre-empt the size rule and make the arm answer nothing. ASCII, so
bytes, code points and UTF-16 units all coincide and the arm says nothing about WHICH unit is
counted; that question is already settled by the published emoji arm and is not what this is for.

@JhouCode identified this width and stated plainly that his CLI is not authenticated for `-p`, so
he has no behavioural arms at all. This is his experiment, run on our machine.

COST, stated before running because that is the rule here: one arm, 1 init + 3 trials = 4 `claude
-p` sessions. Tools are allowlisted to zero and asserted empty at init, because a probe with tools
can answer by reading MEMORY.md off disk instead of reporting its own context (@pjt222,
pjt222/agent-almanac#407).
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import is_the_cap_counted_in_bytes_or_utf16_units as U  # noqa: E402

WIDTH = 147                  # characters per line; the line costs WIDTH + 1 units
LINES = 180                  # over the cap, under the 200-line rule
TRIALS = 3
BRACKET = (24955, 25074)     # from the four published arms, recomputed in verdicts below
_t0 = time.time()


def cumulative(n: int) -> int:
    """UTF-16 units consumed through the end of line n, newline included."""
    return n * (WIDTH + 1)


def main() -> int:
    lo, hi = BRACKET
    boundary_line = next(n for n in range(1, LINES + 1) if lo <= cumulative(n) < hi)
    split_at = cumulative(boundary_line)
    print(f"  width {WIDTH} -> {WIDTH + 1} units/line; line {boundary_line} ends at {split_at}, "
          f"inside [{lo}, {hi})")
    print(f"  last kept {boundary_line - 1} => cap in [{lo}, {split_at});  "
          f"last kept {boundary_line} => cap in [{split_at}, {hi})")
    print(f"  file is {LINES} lines = {cumulative(LINES)} units, so a size cut is guaranteed\n")

    U.CLAUDE = U.claude_bin()
    root = tempfile.mkdtemp(prefix="split147_")
    cwd = os.path.join(root, "arm")
    os.makedirs(cwd, exist_ok=True)
    store, _, offered, _ = U.run(cwd, "Reply with only: INIT")
    if offered:
        raise SystemExit(f"REFUSED: {len(offered)} tools offered; a disk read could answer this")
    if not store:
        raise SystemExit("REFUSED: store not resolved, so nothing here would be evidence")
    os.makedirs(store, exist_ok=True)
    text = U.make(LINES, WIDTH, "x")
    with open(os.path.join(store, "MEMORY.md"), "wb") as f:
        f.write(text.encode("utf-8"))
    U.CREATED.append(store)

    units = len(text.encode("utf-16-le")) // 2
    answers, warned, rows = [], None, []
    for t in range(1, TRIALS + 1):
        _, ans, off2, used = U.run(cwd, U.ASK)
        head = (ans or "").split("WARNING")[0]
        m = re.search(r"CANARY-L(\d{4})", head)
        answers.append(int(m.group(1)) if m else None)
        if warned is None:
            warned = "NO-INDICATOR" not in (ans or "")
        rows.append({"trial": t, "last": answers[-1], "tools_offered": len(off2),
                     "tool_uses": used, "answer": (ans or "")[:220]})
        print(f"[{time.time() - _t0:6.1f}s]   trial {t}/{TRIALS} last={answers[-1]}", flush=True)

    last = answers[0] if answers and len(set(answers)) == 1 else None
    v = {
        "file_size_matches_the_arithmetic": units == cumulative(LINES),
        "no_tools_were_offered": all(r["tools_offered"] == 0 for r in rows),
        "no_tool_was_called": all(not r["tool_uses"] for r in rows),
        "every_trial_agrees": last is not None,
        "the_answer_is_one_of_the_two_the_design_allows": last in (boundary_line - 1, boundary_line),
        "a_cut_actually_happened": last is not None and last < LINES,
    }
    narrowed = None
    if v["the_answer_is_one_of_the_two_the_design_allows"]:
        narrowed = ([lo, split_at] if last == boundary_line - 1 else [split_at, hi])
        v["the_bracket_is_strictly_narrower_than_before"] = (
            narrowed[1] - narrowed[0] < hi - lo)

    removed, left = U.cleanup()
    v["every_fixture_store_was_removed"] = not left

    print("\n=== VERDICTS ===")
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    if narrowed:
        print(f"\n  cap bracket [{lo}, {hi}) -> [{narrowed[0]}, {narrowed[1]}), "
              f"width {hi - lo} -> {narrowed[1] - narrowed[0]} units")
    print(f"  fixture stores removed: {removed}   still present: {len(left)}")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "does_a_147_unit_line_split_the_cap_bracket.result.json")
    json.dump({"probe": os.path.basename(__file__),
               "claude_version": U.subprocess.run([U.CLAUDE, "--version"], capture_output=True,
                                                  text=True).stdout.strip(),
               "width_chars": WIDTH, "units_per_line": WIDTH + 1, "lines": LINES,
               "file_units": units, "boundary_line": boundary_line, "split_at": split_at,
               "bracket_before": list(BRACKET), "bracket_after": narrowed,
               "last_line_loaded": last, "warned": warned, "verdicts": v, "rows": rows},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nwrote {out}")
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
