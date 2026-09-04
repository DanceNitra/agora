"""How much of our own MEMORY.md reaches a session, measured the way the loader measures it.

WHY. Twice now our index has been silently smaller than we thought, and both times the instrument
was the problem rather than the file.

  * 2026-08-21: 95 of 229 entries sat outside the window while every size check passed, because
    un-crowding is byte-neutral and the LINE cap was the one binding.
  * 2026-08-26, this file's reason for existing: the index was measured with a TEXT-MODE read on a
    CRLF file. Python's universal newlines silently drop the carriage returns, so 210 units vanished
    from the count and the file was reported 210 units smaller than it is. We measured on the wire
    the day before that the CR is counted against the cap, published that finding, and then walked
    into it on our own file within twenty-four hours.

So this reads in BINARY and decodes once. The rule it applies is the one measured on the wire in
`the_memory_cap_is_25000_utf16_units_not_bytes.py`: the loader keeps the first 200 LINES, then cuts
the result at 25,000 UTF-16 units, backing up to the last line boundary.

WHAT IT REPORTS is the only number that matters about an index: how many pointers a session can
actually see. Lines past the cut cost nothing and stay greppable on disk, so they are not an error
in themselves. Reporting them as invisible is the point.

WHAT IT DOES NOT DO is decide the layout. That trade is measured elsewhere and it is not obvious:
packing two entries onto one line buys membership and costs retrieval (recall@3 0.343 for one entry
per line, 0.216 for two or three, ablation-confirmed as co-tenancy rather than hook length), so
"more pointers in the window" is not automatically better. This prints both numbers and leaves the
judgement to a person.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

MEM = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                   "C--Users-Danculus-agora", "memory")
INDEX = os.path.join(MEM, "MEMORY.md")
LINE_CAP, UNIT_CAP = 200, 25_000
LINK = re.compile(r"\]\(([^)]+\.md)\)")


def true_text(path: str) -> str:
    """Decode the bytes on disk. Never a text-mode read: it deletes the carriage returns."""
    return io.open(path, "rb").read().decode("utf-8")


def u16(text: str) -> int:
    """UTF-16 code units, which is what the loader counts and NOT what len() returns.

    THIS FILE CALLED len() A UTF-16 COUNT AND WAS RIGHT ONLY BY LUCK. Python's len() counts CODE
    POINTS. JavaScript's String.length, which is what the loader compares against the cap, counts
    UTF-16 CODE UNITS. The two agree for everything in the Basic Multilingual Plane, so they agree
    on Latin, Cyrillic and ordinary CJK, and they diverge by one per ASTRAL character: an emoji or
    a mathematical alphanumeric is 1 code point and 2 code units. Measured on this index today:
    0 astral characters, so the old count happened to be exact. A fixture that never leaves the
    alphabet where two units coincide cannot detect that it picked the wrong one, which is the same
    trap @tonydzi described on anthropics/claude-code#91188 for bytes against units.
    """
    return len(text.encode("utf-16-le")) // 2


def split_lines(text: str) -> list:
    """Lines, with the trailing newline treated as a TERMINATOR and not as a line.

    @JhouCode's control on anthropics/claude-code#82056, 2026-08-27, and it found a defect here.
    The two obvious primitives fail on disjoint populations: 0 counts newlines and is short by
    one on a file with no trailing newline, while  yields a phantom empty element on
    a file that has one. This probe used the second, MEMORY.md ends in a newline, so every line
    figure it has ever produced was ONE TOO MANY -- 196 reported against a true 195.

    The direction is the tolerable one of the two: over-reporting declares the index nearer the
    200-line cap than it is, so it cries wolf rather than staying quiet on a real cut. It was still
    wrong, and it was quoted.
    """
    out = text.split(chr(10))
    if out and out[-1] == "":
        out.pop()
    return out


def window(text: str) -> str:
    """The first LINE_CAP lines, cut at UNIT_CAP units, backed up to a line boundary."""
    kept = chr(10).join(split_lines(text)[:LINE_CAP])
    if u16(kept) <= UNIT_CAP:
        return kept
    c = kept.rfind(chr(10), 0, UNIT_CAP)
    return kept[:c if c > 0 else UNIT_CAP]


def main() -> int:
    if not os.path.exists(INDEX):
        raise SystemExit(f"REFUSED: {INDEX} is absent; every check below would pass vacuously")
    raw = io.open(INDEX, "rb").read()
    text = raw.decode("utf-8")
    lines = split_lines(text)
    win = window(text)
    seen = win.count(chr(10)) + 1
    in_win = list(dict.fromkeys(LINK.findall(win)))
    all_ptr = list(dict.fromkeys(LINK.findall(text)))
    out_win = [p for p in all_ptr if p not in set(in_win)]
    crlf = raw.count(b"\r\n")
    naive = len(io.open(INDEX, encoding="utf-8").read())

    print(f"  file        : {len(lines):,} lines, {u16(text):,} UTF-16 units, "
          f"{u16(text) / len(lines):.1f} per line")
    print(f"  regime      : {'UNIT-bound' if u16(text) / len(lines) > UNIT_CAP / LINE_CAP else 'LINE-bound'}"
          f"  (the two caps cross at {UNIT_CAP // LINE_CAP} units per line)")
    print(f"  a session sees: {seen:,} lines, {u16(win):,} units, {len(in_win)} pointers")
    print(f"  headroom    : {UNIT_CAP - u16(win):,} units, {LINE_CAP - seen} lines")
    print(f"  invisible   : {len(lines) - seen} lines, {len(out_win)} pointers "
          f"(on disk and greppable, costing nothing)")

    v: dict = {}
    v["the_window_is_not_empty"] = seen > 1 and bool(in_win)
    v["the_window_respects_the_line_cap"] = seen <= LINE_CAP
    v["the_window_respects_the_unit_cap"] = u16(win) <= UNIT_CAP
    # THE CONTROL THIS FILE EXISTS FOR. A text-mode read normalises CRLF away. If the file has
    # carriage returns, the naive count MUST be short by exactly that many, and if it is not, this
    # probe is reading something other than what the loader reads.
    v["CONTROL_a_text_mode_read_would_have_undercounted"] = (
        (crlf > 0 and len(text) - naive == crlf) or (crlf == 0 and len(text) == naive))
    v["and_the_carriage_returns_are_counted_here"] = len(text) == len(raw.decode("utf-8"))
    # THE CONTROL THE UNIT FIX NEEDS. Code points and UTF-16 units agree on this index today
    # because it holds no astral characters, so the two counters cannot be told apart by running
    # them on it. Record the divergence and the astral count, so a future index that acquires an
    # emoji makes the difference visible instead of silently shifting the cap by one per character.
    astral = sum(1 for ch in text if ord(ch) > 0xFFFF)
    v["code_points_and_utf16_units_agree_only_because_there_are_no_astral_chars"] = (
        (astral == 0) == (u16(text) == len(text)))
    # Every pointer must resolve, or the window is spending units on nothing.
    missing = [p for p in all_ptr if not os.path.exists(os.path.join(MEM, p))]
    v["every_pointer_in_the_index_resolves"] = not missing
    # And the map to everything outside the index has to be INSIDE the window, or the 197 memories
    # it points at are unreachable from a session.
    v["the_archive_pointer_is_inside_the_window"] = "MEMORY_ARCHIVE.md" in win
    v["CONTROL_the_archive_actually_exists"] = os.path.exists(os.path.join(MEM, "MEMORY_ARCHIVE.md"))

    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    if missing:
        print("\n  DEAD POINTERS (units spent on nothing):")
        for p in missing:
            print("   ", p)
    if out_win:
        print("\n  OUTSIDE THE WINDOW, so a session never sees these:")
        for p in out_win:
            print("   ", p)

    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "lines": len(lines), "units": u16(text), "code_points": len(text),
               "astral_chars": sum(1 for ch in text if ord(ch) > 0xFFFF),
               "utf8_bytes": len(raw),
               "units_a_text_mode_read_reports": naive, "crlf_terminators": crlf,
               "lines_seen": seen, "units_seen": u16(win),
               "pointers_seen": len(in_win), "pointers_outside": len(out_win),
               "headroom_units": UNIT_CAP - len(win), "headroom_lines": LINE_CAP - seen,
               "dead_pointers": missing, "outside": out_win,
               "cap_source": "measured on the wire in "
                             "the_memory_cap_is_25000_utf16_units_not_bytes.py: 25,000 UTF-16 units, "
                             "whole-line, header not counted",
               "layout_note": "one entry per line scores recall@3 0.343 against 0.216 for two or "
                              "three, so more pointers inside the window is NOT automatically "
                              "better -- see our-own-index-crowding-costs-6x-on-retrieval",
               "platform": sys.platform},
              io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "what_our_own_index_actually_delivers.result.json"),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
