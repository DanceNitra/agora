"""PostToolUse hook for Bash and PowerShell: warn when a shell command grows MEMORY.md near the cap.

WHY. Claude Code checks the index size only after Edit and Write (measured 2026-09-26: all 8
compaction reminders in 1,367 transcripts came from PostToolUse:Edit). About 86 % of our writes
to the index go through Bash, so the index can pass the load cap without any warning, and the
lines past the cap are then not loaded at the next session start. @vshulcz reported the same
gap on anthropics/claude-code#91188.

WHAT IT DOES. After a shell command that names MEMORY.md or the memory directory, it measures
the index the way the loader does (UTF-16 units and lines, binary read) and adds one line of
context when the index is above WARN_UNITS or WARN_LINES. It prints nothing otherwise, and it
always exits 0.
"""
from __future__ import annotations

import json
import os
import sys

INDEX = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                     "C--Users-Danculus-agora", "memory", "MEMORY.md")
LINE_CAP, UNIT_CAP = 200, 25_000
WARN_UNITS, WARN_LINES = 21_000, 180


def measure(path: str):
    with open(path, "rb") as fh:
        text = fh.read().decode("utf-8", errors="replace")
    return len(text.encode("utf-16-le")) // 2, text.count("\n") + (0 if text.endswith("\n") else 1)


def main() -> int:
    try:
        event = json.load(sys.stdin)
        cmd = str((event.get("tool_input") or {}).get("command", ""))
        if "MEMORY.md" not in cmd and "memory" not in cmd.lower():
            return 0
        units, lines = measure(INDEX)
        if units <= WARN_UNITS and lines <= WARN_LINES:
            return 0
        msg = ("[memory_index_guard] MEMORY.md is %d of %d UTF-16 units and %d of %d lines. "
               "Claude Code does not check the size after a shell write. Compact it now: one line "
               "per entry, move detail to topic files or MEMORY_ARCHIVE.md."
               % (units, UNIT_CAP, lines, LINE_CAP))
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": msg}}))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
