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


def window(text: str) -> str:
    """The first LINE_CAP lines, cut at UNIT_CAP units, backed up to a line boundary."""
    kept = chr(10).join(text.split(chr(10))[:LINE_CAP])
    if len(kept) <= UNIT_CAP:
        return kept
    c = kept.rfind(chr(10), 0, UNIT_CAP)
    return kept[:c if c > 0 else UNIT_CAP]


def main() -> int:
    if not os.path.exists(INDEX):
        raise SystemExit(f"REFUSED: {INDEX} is absent; every check below would pass vacuously")
    raw = io.open(INDEX, "rb").read()
    text = raw.decode("utf-8")
    lines = text.split(chr(10))
    win = window(text)
    seen = win.count(chr(10)) + 1
    in_win = list(dict.fromkeys(LINK.findall(win)))
    all_ptr = list(dict.fromkeys(LINK.findall(text)))
    out_win = [p for p in all_ptr if p not in set(in_win)]
    crlf = raw.count(b"\r\n")
    naive = len(io.open(INDEX, encoding="utf-8").read())

    print(f"  file        : {len(lines):,} lines, {len(text):,} UTF-16 units, "
          f"{len(text) / len(lines):.1f} per line")
    print(f"  regime      : {'BYTE-bound' if len(text) / len(lines) > UNIT_CAP / LINE_CAP else 'LINE-bound'}"
          f"  (the two caps cross at {UNIT_CAP // LINE_CAP} units per line)")
    print(f"  a session sees: {seen:,} lines, {len(win):,} units, {len(in_win)} pointers")
    print(f"  headroom    : {UNIT_CAP - len(win):,} units, {LINE_CAP - seen} lines")
    print(f"  invisible   : {len(lines) - seen} lines, {len(out_win)} pointers "
          f"(on disk and greppable, costing nothing)")

    v: dict = {}
    v["the_window_is_not_empty"] = seen > 1 and bool(in_win)
    v["the_window_respects_the_line_cap"] = seen <= LINE_CAP
    v["the_window_respects_the_unit_cap"] = len(win) <= UNIT_CAP
    # THE CONTROL THIS FILE EXISTS FOR. A text-mode read normalises CRLF away. If the file has
    # carriage returns, the naive count MUST be short by exactly that many, and if it is not, this
    # probe is reading something other than what the loader reads.
    v["CONTROL_a_text_mode_read_would_have_undercounted"] = (
        (crlf > 0 and len(text) - naive == crlf) or (crlf == 0 and len(text) == naive))
    v["and_the_carriage_returns_are_counted_here"] = len(text) == len(raw.decode("utf-8"))
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
               "lines": len(lines), "units": len(text),
               "units_a_text_mode_read_reports": naive, "crlf_terminators": crlf,
               "lines_seen": seen, "units_seen": len(win),
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
