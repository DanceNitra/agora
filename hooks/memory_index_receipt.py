"""SessionStart hook: tell the session which memory-index pointers the loader dropped.

THE PROBLEM IT ANSWERS. Claude Code loads the first 200 lines or 25,000 UTF-16 units of
MEMORY.md, whichever comes first, cut at a line boundary. Over the cap it warns that the file
was partly loaded. It never says WHICH pointers went, so an entry the session was supposed to
honour can be missing and the session cannot know that it does not know. Measured on our own
index on 2026-09-13: one added line pushed four pointers out, and the warning said only "over
the cap".

WHAT THIS DOES. Runs at session start, applies the same cut rule to the index, and prints the
pointers that fell outside the window, by name, into the session's context. That is the whole
receipt: the loader's silence replaced by a list. Nothing else is injected, so the cost inside
the window is one short block, and only when something was cut. When nothing was cut it prints
nothing.

WHAT IT DOES NOT DO. It does not load the dropped entries, so the index budget is unchanged, and
it does not say whether a pointer's record is fresh; an unread record stays unknown. It reports
the loader's omission, which is the one failure the loader cannot report about itself.

INSTALL. Copy this file anywhere and add it as a SessionStart hook in .claude/settings.json:

    "SessionStart": [{"hooks": [{"type": "command",
                                 "command": "python /path/to/memory_index_receipt.py"}]}]

The index path is derived from the working directory the way Claude Code derives it (the
project path with every non-alphanumeric character replaced by "-"), or set
CLAUDE_MEMORY_INDEX to point at it. Exit status is always 0: a receipt that can block a session
would be worse than the silence it replaces.
"""
from __future__ import annotations

import io
import os
import re
import sys

LINE_CAP, UNIT_CAP = 200, 25_000
LINK = re.compile(r"\]\(([^)]+\.md)\)")


def u16(text: str) -> int:
    """UTF-16 code units: what the loader compares against the cap. len() counts code points."""
    return len(text.encode("utf-16-le")) // 2


def split_lines(text: str) -> list:
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


def index_path() -> str:
    explicit = os.environ.get("CLAUDE_MEMORY_INDEX")
    if explicit:
        return explicit
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(project))
    return os.path.join(os.path.expanduser("~"), ".claude", "projects", slug, "memory", "MEMORY.md")


def receipt(text: str) -> str:
    """The lines to hand the session. Empty when nothing was cut."""
    lines = split_lines(text)
    win = window(text)
    seen = win.count(chr(10)) + 1 if win else 0
    in_win = set(LINK.findall(win))
    outside = [p for p in dict.fromkeys(LINK.findall(text)) if p not in in_win]
    if not outside and seen >= len(lines):
        return ""
    head = ("[memory-index receipt] the loader kept %d of %d lines (%s of %s units); "
            "%d pointer(s) are on disk but NOT in this session's context:"
            % (seen, len(lines), format(u16(win), ","), format(u16(text), ","), len(outside)))
    body = "".join("\n  - " + p for p in outside)
    tail = ("\n  They are readable by path; a pointer you cannot see is not a pointer that does "
            "not exist. To stop losing them, move entries below the cut into an archive file.")
    return head + body + tail


def main() -> int:
    path = index_path()
    if not os.path.isfile(path):
        return 0
    try:
        text = io.open(path, "rb").read().decode("utf-8")   # bytes, so CR is counted as the loader counts it
    except Exception:                                       # noqa: BLE001 - never block a session
        return 0
    out = receipt(text)
    if out:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
