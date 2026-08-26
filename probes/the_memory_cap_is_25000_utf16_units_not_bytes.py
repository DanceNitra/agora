"""The auto-memory cap is 25,000 UTF-16 units. Every surface that shows it calls those units bytes.

WHY THIS EXISTS. @JhouCode closed a long comment on anthropics/claude-code#82056 with three asks,
and the first one is the whole of this file:

    "State the constant precisely, in the unit it is actually counted in."

and, on what it cost to get even an approximation:

    "The precise boundary currently stands at [24999, 25023), and it took four people roughly a
     week of fixtures, retractions, adversarial review and wire captures to get there."

ONE half had never been measured, and it is the constant. The bracket is 24 units wide because of
WHERE it was read, not how carefully: read the cap through a line and it quantizes to a line's
width, and that is the floor four people spent a week hitting. Part One gets under it.

THE OTHER HALF, the unit, we measured in August and published in another repo, and Part Two is a
replication rather than a discovery -- said here at the top because the first draft of this file did
not say it anywhere. What Part Two adds is the SURFACE: August was behavioural, and behavioural arms
in this thread keep getting retracted, ours included.

Five arms below, on one Windows box, zero model calls. The instrument -- point `ANTHROPIC_BASE_URL`
at a local recorder and read the request body -- is @pjt222's, published in comment 5412833938 and
offered for other platforms. Reading bytes that were SENT is what makes all of this immune to the
reconstruction ruler he raised against the behavioural arms, including ours.


PART ONE -- WHERE THE BRACKET COMES FROM, AND HOW TO GET UNDER IT

  ARM 1, MULTI-LINE (150 x 199 chars, CRLF). The wire carries lines 1..124 and stops. Line 125 does
  not appear even in part, though a raw cut at 25,000 would have carried 78 more characters of it.
  Truncation keeps whole lines. @pjt222 flagged this as an assumption his own brackets leaned on and
  downgraded it; this is the observation, and it explains the week: whole-line truncation reads the
  cap THROUGH a line, so every such fixture quantizes the answer to one line's width. Arm 1 alone
  admits any cap in [24,922, 25,125). No instrument that respects line boundaries does better.

  ARM 2, A SINGLE LINE of unique markers, far over the cap. Whole-line has nothing to keep: line 1
  alone exceeds the budget, so it falls back to a raw cut, and a raw cut does not quantize.

      4-char markers 0001..8000 (32,001 units) -> 6,250 whole markers + 0 characters = 25,000
      7-char markers 0000001..  (35,001 units) -> 3,571 whole markers + 3 characters = 25,000

  Two widths, one number, and the second cuts INSIDE marker 3572. A boundary landing on a marker
  edge in both runs would be the fixture's geometry talking; one that lands mid-marker is not.

  This is the arm @pjt222 named and deliberately did not run -- "a needle whose digits end at
  25,000... it was deliberately not run, because it is confounded". Asked of a model it is
  confounded. Read off the wire nothing is asked of a model, so it is not.

  THE HEADER CONTROL. Both arm-2 captures used the same store path, and the harness prepends a
  header naming that path. Identical headers cannot separate "25,000 units of CONTENT" from "25,000
  units of header PLUS content". A third capture of the same fixture, taken from a project whose
  store path flattens 6 characters shorter, carries the same 25,000: header 246 units vs 240, content
  starting at offset 541 vs 535, and 25,000 units of it either way. Were the header on the budget the
  shorter one would have carried 25,006. Six units is a thin wedge and a wider one would be better,
  but the direction is unambiguous and the arithmetic has no slack in it. (This number was written as
  45 in the first draft of this file, from the length of the PROJECT directory; the store lives under
  ~/.claude/projects/<flattened-path>/, and the flattening is what the header names.)


PART TWO -- THE UNIT. THIS IS A REPLICATION OF OUR OWN RESULT, NOT A NEW FINDING.

  Say that first, because the file nearly did not. We measured this on 2026-08-21 on v2.1.238
  (`probes/is_the_cap_counted_in_bytes_or_utf16_units.py`, 10/10 verdicts, including
  `warning_reports_units_over_1024_not_kb`) and published it in pjt222/agent-almanac#407, comment
  5366900247. It is five days old and it is already outward. Re-deriving it today and presenting it
  as new would have been the third time this week that a "finding" turned out to be ours already.

  That earlier run is STRONGER than this one on the axis that matters most: it carried an EMOJI arm,
  and emoji are the only fixture that separates code points from UTF-16 units, because they are one
  code point and two units. 200x125 emoji has the same 25,200 code points as the ASCII arm but
  43,400 units, and it cut at line 115 instead of 198. CJK alone cannot see that distinction. Do not
  cite the arms below as evidence about code points; they are not.

  WHAT IS ACTUALLY ADDED HERE is the surface, and given this thread's history it is worth the run.
  The August arms were BEHAVIOURAL -- they asked the model which canary was last. Behavioural arms
  in #82056 have not survived: our own 115, our 168 and the ceiling derived from them were all
  retracted, and @pjt222's reconstruction ruler is why. The arms below ask nothing of any model.
  They read the request body. A behavioural result confirmed on the wire is worth more than the same
  result asserted twice.

  Three fixtures. CJK ideographs are 3 bytes in UTF-8 and exactly 1 UTF-16 unit, and that gap is the
  entire experiment.

      ARM A  20,000 ASCII chars =  20,000 bytes  -> arrives whole, no notice     [CONTROL]
      ARM B  10,500 CJK chars   =  31,500 bytes  -> arrives whole, no notice
      ARM C  35,000 CJK chars   = 105,000 bytes  -> cut at 25,000 CHARS (75,000 bytes)

  ARM B is the decision. It is over 25,000 bytes by a quarter and under 25,000 units by more than
  half, and it is not touched. The cap is not counted in bytes. ARM C confirms it from the other
  side: a byte cut would have landed at 8,333 characters.

  ARM A is the control that lets B mean anything. An instrument that never reports truncation would
  produce B's result on any input. A does the same thing to the notice: no notice appears when
  nothing is cut, so the notice's absence in B is evidence rather than silence.

  AND THE DISPLAYS ARE WRONG WHEREVER THE INDEX IS NOT ASCII -- also ours, also August, also already
  outward: the August receipt's verdict is named `warning_reports_units_over_1024_not_kb` and its
  ASCII arm recorded "24.6KB" over a 61,600-byte CJK file. Arm C's file is 105,001 bytes, 102.5 KB
  on disk. The runtime's own warning says:

      WARNING: MEMORY.md is 34.2KB (limit: 24.4KB)

  34.2 = 35,001/1024 and 24.4 = 25,000/1024. Both figures count UTF-16 units and print the letters
  KB. The documented "25KB" is the same mistake at the same place. On ASCII this is invisible, which
  is why nobody has caught it. On a Chinese, Japanese, Korean or emoji-heavy index it is off by the
  UTF-8 expansion factor -- 3x here -- in BOTH numbers at once, so a user is told their 102.5 KB file
  is 34.2KB and that their limit is 24.4KB when they may in fact spend 73 KB of disk.

  The practical consequence is not "the docs have a typo". It is that a CJK index gets roughly three
  times the budget the documentation promises, and the runtime will never tell its owner so.


WHAT IS NOT SETTLED, listed because two of these were raised against an earlier version of this file:

  * whether the TRIGGER equals the CUT. 25,000 units arriving proves the cut takes 25,000. A loader
    testing "> 25000" while cutting at 25,000 is not separated by anything here. Arm B narrows it --
    10,500 units did not trigger -- but does not pin it.
  * one machine, win32, ASCII and CJK fixtures. The captures were taken on 2.1.245.1ab and 2.1.246;
    this thread has watched the CLI update itself mid-session, so the constant is a reading, not a
    promise.
  * the 200-LINE cap, untouched by all of this, and the one that binds first on an ordinary index.

CORRECTION CARRIED FORWARD. An earlier version of this file claimed truncation is "not whole-line"
and cited arm 2 as the refutation. That was wrong, and our own capture from the day before refutes
it: arm 1 shows the whole-line path directly. The single-line cut is the fallback -- which is
precisely why it can read the constant exactly.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED = 25_000
CJK = "〇一二三四五六七八九"

SLICE_CAPS = {4: os.path.join(HERE, "_wire_capture_exact_cap_4char.json"),
              7: os.path.join(HERE, "_wire_capture_exact_cap_7char.json")}
SHORTPATH = os.path.join(HERE, "_wire_capture_exact_cap_shortpath.json")
MULTILINE = os.path.join(HERE, "_wire_capture_windows_crlf.json")
UNIT_ARMS = {"A": (os.path.join(HERE, "_wire_capture_unit_armA.json"), False, 20_000),
             "B": (os.path.join(HERE, "_wire_capture_unit_armB.json"), True, 10_500),
             "C": (os.path.join(HERE, "_wire_capture_unit_armC.json"), True, 35_000)}
ML_WIDTH, ML_LINES = 199, 150          # 199 chars + CRLF = 201 units per line


def body_of(path: str) -> dict:
    if not os.path.exists(path):
        raise SystemExit(f"REFUSED: {path} is absent; every check below would pass vacuously")
    return json.loads(json.load(io.open(path, encoding="utf-8"))[0]["body"])


def prompt_of(path: str) -> str:
    return body_of(path)["messages"][0]["content"][0]["text"]


def marker_run(path: str, width: int) -> tuple:
    text = prompt_of(path)
    i = text.find("1".rjust(width, "0") + "2".rjust(width, "0"))
    if i < 0:
        raise SystemExit(f"REFUSED: the {width}-char fixture is not in {os.path.basename(path)}")
    run = re.match(r"\d+", text[i:]).group(0)
    return len(run), len(run) // width, len(run) % width


def header_units(path: str) -> int:
    m = re.search(r"Contents of [^\n]*auto-memory[^\n]*\n\n", prompt_of(path))
    return len(m.group(0)) if m else -1


def notice(path: str):
    return re.search(r"WARNING: MEMORY\.md is ([\d.]+)KB \(limit: ([\d.]+)KB\)", prompt_of(path))


def main() -> int:
    v: dict = {}

    # ---- PART ONE, ARM 1: the whole-line path, which is the one that quantizes -----------------
    ml = body_of(MULTILINE)
    mltext = ml["messages"][0]["content"][0]["text"]
    ids = [int(x) for x in re.findall(r"CANARY-L(\d{4})", mltext)]
    last, per = (max(ids) if ids else 0), ML_WIDTH + 2
    kept = last * per - 2
    would_carry = EXPECTED - kept
    partial_next = f"CANARY-L{last + 1:04d}" in mltext

    print(f"  ARM 1  multi-line {ML_LINES}x{ML_WIDTH} CRLF -> lines 1..{last} = {kept:,} units, "
          f"then stops")
    print(f"         a raw cut would have carried {would_carry} more chars of line {last + 1}: "
          f"{'PRESENT' if partial_next else 'ABSENT'}")
    v["ARM1_the_multiline_wire_stops_on_a_line_boundary"] = not partial_next
    v["ARM1_and_a_raw_cut_would_have_had_room_to_continue"] = would_carry > 0
    v["ARM1_alone_only_brackets_the_cap"] = kept < EXPECTED < (last + 1) * per

    # ---- PART ONE, ARM 2: the fallback cut, which does not --------------------------------------
    rows = []
    for width, path in SLICE_CAPS.items():
        units, whole, leftover = marker_run(path, width)
        rows.append({"marker_width": width, "units_on_wire": units, "whole_markers": whole,
                     "leftover_chars": leftover})
        print(f"  ARM 2  {width}-char markers: {units:,} units "
              f"({whole:,} whole markers + {leftover} characters)")

    v["ARM2_both_widths_cut_at_the_same_unit"] = len({r["units_on_wire"] for r in rows}) == 1
    v["ARM2_that_unit_is_exactly_25000"] = all(r["units_on_wire"] == EXPECTED for r in rows)
    # If every run stopped on a marker edge the boundary would be the fixture, not the constant.
    v["CONTROL_at_least_one_run_cuts_INSIDE_a_marker"] = any(r["leftover_chars"] for r in rows)
    v["CONTROL_the_two_fixtures_have_different_geometry"] = len(rows) == 2 and len(
        {r["marker_width"] for r in rows}) == 2
    v["CONTROL_both_fixtures_exceeded_the_cap"] = all(
        r["whole_markers"] * r["marker_width"] >= EXPECTED - r["marker_width"] for r in rows)

    sp_units, _, _ = marker_run(SHORTPATH, 4)
    long_h, short_h = header_units(SLICE_CAPS[4]), header_units(SHORTPATH)
    print(f"  CTRL   same fixture, store path {long_h - short_h} units shorter -> {sp_units:,} units")
    v["CONTROL_the_two_headers_really_differ_in_length"] = long_h > 0 and short_h > 0 and long_h != short_h
    v["CONTROL_a_shorter_header_carries_the_SAME_content"] = sp_units == EXPECTED

    # ---- PART TWO: the unit ---------------------------------------------------------------------
    print()
    unit_rows = {}
    for arm, (path, is_cjk, total) in UNIT_ARMS.items():
        text = prompt_of(path)
        cls = "[" + CJK + "]" if is_cjk else r"\d"
        m = re.search(cls + "{100,}", text)
        run = m.group(0) if m else ""
        n = notice(path)
        unit_rows[arm] = {"fixture_chars": total, "fixture_bytes": total * (3 if is_cjk else 1),
                          "chars_on_wire": len(run), "bytes_on_wire": len(run.encode("utf-8")),
                          "truncated": len(run) < total,
                          "notice": bool(n),
                          "notice_size_kb": float(n.group(1)) if n else None,
                          "notice_limit_kb": float(n.group(2)) if n else None}
        r = unit_rows[arm]
        print(f"  ARM {arm}  {total:,} chars = {r['fixture_bytes']:,} bytes -> "
              f"{r['chars_on_wire']:,} chars on the wire, truncated={r['truncated']}, "
              f"notice={'yes' if n else 'no'}")

    A, B, C = unit_rows["A"], unit_rows["B"], unit_rows["C"]
    # THE CONTROL: an instrument that never reports truncation would produce B's result on anything.
    v["CONTROL_ARM_A_under_both_caps_is_NOT_truncated"] = not A["truncated"] and not A["notice"]
    v["CONTROL_ARM_A_proves_the_notice_can_be_absent_meaningfully"] = not A["notice"]
    v["CONTROL_ARM_B_really_is_over_25000_BYTES"] = B["fixture_bytes"] > EXPECTED
    v["CONTROL_ARM_B_really_is_under_25000_UNITS"] = B["fixture_chars"] < EXPECTED
    v["ARM_B_over_25000_bytes_is_NOT_truncated"] = not B["truncated"] and not B["notice"]
    v["ARM_C_cuts_at_25000_CHARACTERS"] = C["chars_on_wire"] == EXPECTED
    v["ARM_C_does_NOT_cut_at_25000_bytes"] = C["bytes_on_wire"] != EXPECTED
    v["so_the_cap_is_counted_in_UTF16_units_not_bytes"] = (
        not B["truncated"] and C["chars_on_wire"] == EXPECTED)

    # The displayed sizes count units and print KB.
    disk_kb = (C["fixture_bytes"] + 1) / 1024
    units_kb = (C["fixture_chars"] + 1) / 1024
    v["the_notice_size_matches_UNITS_over_1024"] = abs(C["notice_size_kb"] - units_kb) < 0.05
    v["the_notice_size_does_NOT_match_the_file_on_disk"] = abs(C["notice_size_kb"] - disk_kb) > 1.0
    v["the_stated_limit_is_25000_over_1024"] = abs(C["notice_limit_kb"] - EXPECTED / 1024) < 0.05

    print(f"\n  arm C notice : {C['notice_size_kb']}KB (limit: {C['notice_limit_kb']}KB)")
    print(f"  units/1024   : {units_kb:.2f}   <- what it printed")
    print(f"  actually on disk: {disk_kb:.1f} KB   <- off by {disk_kb / units_kb:.1f}x")

    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    print(f"\n  documented   : 25KB          -- units labelled bytes, and 25,000 is not 25*1024")
    print(f"  runtime shows: 24.4KB / 34.2KB -- the same units, labelled KB")
    print(f"  thread's best: [24999, 25023) -- 24 units wide, four people, about a week")
    print(f"  measured here: {EXPECTED:,} UTF-16 units, exactly, and NOT bytes")

    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "cap_units": EXPECTED, "unit": "UTF-16 code units",
               "slice_arm": rows, "unit_arms": unit_rows,
               "multiline_arm": {"last_kept_line": last, "units": kept,
                                 "partial_next_line_on_wire": partial_next,
                                 "bracket_from_this_arm_alone": [kept, (last + 1) * per]},
               "header_control": {"long": long_h, "short": short_h, "content_units": sp_units},
               "display_defect": {"notice_kb": C["notice_size_kb"], "units_kb": round(units_kb, 2),
                                  "real_kb_on_disk": round(disk_kb, 1),
                                  "factor": round(disk_kb / units_kb, 2),
                                  "what": "size and limit are both UTF-16 unit counts divided by "
                                          "1024 and printed as KB; invisible on ASCII, 3x off on "
                                          "CJK, in both numbers at once"},
               "truncation": "whole-line while a line boundary is available; a raw 25,000-unit cut "
                             "when line 1 alone exceeds the budget",
               "not_settled": ["whether the trigger threshold equals the cut length",
                               "any platform but win32; builds 2.1.245.1ab and 2.1.246",
                               "the 200-line cap, which binds first on ordinary indexes"],
               "instrument_credit": "wire-capture method from @pjt222, anthropics/claude-code#82056 "
                                    "comment 5412833938",
               "corrects": "an earlier version claimed truncation is NOT whole-line, citing the "
                           "single-line arm. Arm 1, our own capture from the day before, shows the "
                           "whole-line path directly. The single-line cut is the fallback.",
               "platform": sys.platform},
              io.open(os.path.join(HERE, "the_memory_cap_is_25000_utf16_units_not_bytes.result.json"),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
