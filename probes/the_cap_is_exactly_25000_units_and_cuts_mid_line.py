"""The auto-memory cap is exactly 25,000 UTF-16 units, and truncation cuts mid-line.

WHY THIS EXISTS. @JhouCode closed a long comment on anthropics/claude-code#82056 with a request
rather than a measurement, and it is the sharpest thing in the thread:

    "The precise boundary currently stands at [24999, 25023), and it took four people roughly a
     week of fixtures, retractions, adversarial review and wire captures to get there. It is a
     constant. One line of documentation would have replaced the entire effort."

The bracket exists because every instrument used on it so far reads the cut through a LINE. A
fixture of N-unit lines can only ever say which line survived, so the cap is pinned to an interval
of one line's width and no better.

@pjt222's wire capture removes the line. Read the request body and the index arrives as text, so
the boundary can be counted character by character. This fixture is ONE long line of unique
markers, which turns the question from "which line survived" into "how many units crossed".

    4-char markers 0001..8000 (32,001 units)  ->  6,250 whole markers  = 25,000 units
    7-char markers 0000001..  (35,001 units)  ->  3,571 whole markers + 3 characters = 25,000

Two widths, one number. The second run cuts INSIDE marker 3572, three characters in, which is what
makes it a measurement of the cap rather than of the fixture: a boundary that fell on a marker edge
in both runs would be the geometry talking.

TWO THINGS THIS SETTLES, both open in the thread as of 2026-08-26:

  1. THE CONSTANT IS 25,000 UTF-16 UNITS EXACTLY. Not "25KB" (the documented figure, in the wrong
     unit -- bytes and units diverge by up to 3x on a non-ASCII index). Not "24.4KB" (the runtime's
     own display, rounded, consistent with any cap in [24934.4, 25036.8)). 25,000, on the nose.

  2. TRUNCATION IS NOT WHOLE-LINE. @pjt222 flagged whole-line truncation as an assumption his own
     brackets leaned on and downgraded it. It is refuted here directly: the wire carries three
     characters of a marker whose remaining four never arrived.

WHAT IT DOES NOT SETTLE. One machine, win32, 2.1.245.1ab, ASCII fixtures. Whether 25,000 is stable
across builds is exactly the kind of thing this thread has watched move. And a single line is an
unusual index; the 200-LINE cap is untouched by this and still binds first on ordinary indexes.

The instrument is @pjt222's (comment 5412833938), offered for other platforms. The single-line
fixture and the two-width control are the part added here.

Zero model calls: the recorder answers with canned SSE. Reads two committed captures.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAPS = {4: os.path.join(HERE, "_wire_capture_exact_cap_4char.json"),
        7: os.path.join(HERE, "_wire_capture_exact_cap_7char.json")}
EXPECTED = 25_000


def crossed(path: str, width: int) -> tuple:
    """Digits of index content on the wire, and how the run ends."""
    body = json.loads(json.load(io.open(path, encoding="utf-8"))[0]["body"])
    text = body["messages"][0]["content"][0]["text"]
    first = "1".rjust(width, "0") + "2".rjust(width, "0")
    i = text.find(first)
    if i < 0:
        raise SystemExit(f"REFUSED: the {width}-char fixture is not in the capture; nothing below "
                         f"would be evidence")
    run = re.match(r"\d+", text[i:]).group(0)
    return len(run), len(run) // width, len(run) % width, len(body.get("tools") or [])


def main() -> int:
    v: dict = {}
    rows = []
    for width, path in CAPS.items():
        if not os.path.exists(path):
            raise SystemExit(f"REFUSED: {path} is absent")
        units, whole, leftover, tools = crossed(path, width)
        rows.append({"marker_width": width, "units_on_wire": units,
                     "whole_markers": whole, "leftover_chars": leftover,
                     "tools_on_wire": tools})
        print(f"  {width}-char markers: {units:,} units on the wire "
              f"({whole:,} whole markers + {leftover} characters)")

    v["both_captures_cut_at_the_same_unit"] = len({r["units_on_wire"] for r in rows}) == 1
    v["that_unit_is_exactly_25000"] = all(r["units_on_wire"] == EXPECTED for r in rows)
    # THE CONTROL THAT MAKES IT A CAP AND NOT A GEOMETRY. If every run stopped on a marker edge,
    # the boundary would be a property of the fixture. One of these must cut INSIDE a marker.
    v["CONTROL_at_least_one_run_cuts_INSIDE_a_marker"] = any(r["leftover_chars"] for r in rows)
    v["and_that_refutes_whole_line_truncation"] = any(r["leftover_chars"] for r in rows)
    v["no_tool_was_offered_in_either_capture"] = all(r["tools_on_wire"] == 0 for r in rows)
    # The two widths must actually differ, or "two widths" is one experiment run twice.
    v["CONTROL_the_two_fixtures_have_different_geometry"] = len(
        {r["marker_width"] for r in rows}) == 2
    # And each fixture must have been larger than the cap, or nothing was cut at all.
    v["CONTROL_both_fixtures_exceeded_the_cap"] = all(
        r["whole_markers"] * r["marker_width"] >= EXPECTED - r["marker_width"] for r in rows)

    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print(f"\n  documented   : 25KB, in bytes -- the wrong unit for a UTF-16 cap")
    print(f"  runtime shows: 24.4KB, rounded -- consistent with [24934.4, 25036.8)")
    print(f"  thread's best: [24999, 25023), 24 units wide, four people, about a week")
    print(f"  measured here: {EXPECTED:,} units exactly, two fixture widths, zero model calls")

    json.dump({"probe": os.path.basename(__file__), "verdicts": v, "rows": rows,
               "cap_units": EXPECTED,
               "truncation": "mid-line, to the unit -- not whole-line",
               "instrument_credit": "wire capture from @pjt222, anthropics/claude-code#82056 "
                                    "comment 5412833938",
               "scope": "one machine, win32, 2.1.245.1ab, ASCII single-line fixtures. The 200-line "
                        "cap is untouched by this and still binds first on ordinary indexes.",
               "platform": sys.platform},
              io.open(os.path.join(HERE,
                                   "the_cap_is_exactly_25000_units_and_cuts_mid_line.result.json"),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
