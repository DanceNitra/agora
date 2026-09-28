"""PostToolUse hook for Bash and PowerShell: warn when a shell command grows MEMORY.md near the cap.

WHY. Claude Code checks the index size only after Edit and Write (measured 2026-09-26: all 8
compaction reminders in 1,367 transcripts came from PostToolUse:Edit). About 86 % of our writes
to the index go through Bash, so the index can pass the load cap without any warning, and the
lines past the cap are then not loaded at the next session start. @vshulcz reported the same
gap on anthropics/claude-code#91188.

WHAT IT DOES (v2, 2026-09-28). The first version matched the command text for "MEMORY.md" or
"memory". @vshulcz showed why that misses the normal case: a trim ran as
`python3 compact_memory.py --write`, and only 3 of 8 runs of that script named the index at all.
So this version does not read the command. After EVERY shell command it stats the index (one
syscall) and compares size and mtime with the last stat. Unchanged: exit silently. Changed: measure
the index the way the loader does (UTF-16 units and lines, binary read), append the change to
CHANGES_LOG, and add one line of context when the index is above WARN_UNITS or WARN_LINES.
It always exits 0.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

HOME = os.path.join(os.path.expanduser("~"), ".claude")
INDEX = os.environ.get("MEMORY_INDEX_GUARD_INDEX") or os.path.join(
    HOME, "projects", "C--Users-Danculus-agora", "memory", "MEMORY.md")
STATE = os.environ.get("MEMORY_INDEX_GUARD_STATE") or os.path.join(HOME, "memory_index_guard.state.json")
CHANGES_LOG = os.environ.get("MEMORY_INDEX_GUARD_LOG") or os.path.join(HOME, "memory_index_guard.changes.jsonl")
LINE_CAP, UNIT_CAP = 200, 25_000
WARN_UNITS, WARN_LINES = 21_000, 180


def measure(path: str):
    with open(path, "rb") as fh:
        text = fh.read().decode("utf-8", errors="replace")
    return len(text.encode("utf-16-le")) // 2, text.count("\n") + (0 if text.endswith("\n") else 1)


def main() -> int:
    try:
        event = json.load(sys.stdin)
        st = os.stat(INDEX)
        sig = [st.st_size, st.st_mtime_ns]
        try:
            prev = json.load(open(STATE, encoding="utf-8"))
        except (OSError, ValueError):
            prev = {}
        if prev.get("sig") == sig:
            return 0
        units, lines = measure(INDEX)
        json.dump({"sig": sig, "units": units, "lines": lines}, open(STATE, "w", encoding="utf-8"))
        if prev:  # the first stat only sets the baseline
            cmd = str((event.get("tool_input") or {}).get("command", ""))
            with open(CHANGES_LOG, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                     "session": event.get("session_id"), "tool": event.get("tool_name"),
                                     "units_before": prev.get("units"), "units_after": units,
                                     "lines_before": prev.get("lines"), "lines_after": lines,
                                     "command_names_index": "MEMORY.md" in cmd,
                                     "command_head": cmd[:120]}) + "\n")
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
