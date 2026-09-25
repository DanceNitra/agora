"""What does an agent remove from its memory index when the harness tells it to compact?

anthropics/claude-code#91188 asks whether a trim triggered by the MEMORY.md compaction reminder
removes load-bearing content. @vshulcz proposed reading the answer out of the transcripts: every
Edit carries `old_string` and `new_string`, so the removed lines of every edit to a memory file can
be recovered and classified, whatever anyone kept as a backup. His own index never crossed the
threshold, so his scan could not separate reminder-triggered edits from ordinary ones. Ours has.

What this does, per transcript (main sessions and their subagents, never the throwaway probe
projects under AppData/Local/Temp, which are synthetic):

  1. A REMINDER is the harness's own record: a line of type "attachment" whose content says
     "The memory index at MEMORY.md is N, approaching the ... read limit". Text that merely quotes
     the reminder (a tool result, a prompt, an issue body) is not one. A control below requires that.
  2. An edit is AFTER A REMINDER when it touches MEMORY.md later in the same transcript than a
     reminder, and before the session's next user prompt. Everything else is ordinary.
  3. Removed lines: for Edit and MultiEdit, the lines of old_string that new_string no longer has
     (as a multiset). A Write carries only the new file, so its removals are not recoverable here;
     it is counted, never classified.
  4. The scan cannot see a trim made by a script (python, sed) through Bash, because no old_string
     is recorded. Those are counted separately as Bash commands naming MEMORY.md after a reminder.

Classes, first match wins: rule (never/always/must/only as a word), dated (a 2026 date or MM-DD),
link (a markdown link), bullet (starts with "- "), prose (anything else non-blank).

    python -X utf8 probes/what_a_reminder_triggered_trim_removes.py [--self-test]
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.expanduser("~/.claude/projects")
REMINDER = re.compile(r"The memory index at MEMORY\.md is [\d.]+ ?(KB|lines), approaching the")
IS_INDEX = re.compile(r"(^|[\\/])MEMORY\.md$")
RULE = re.compile(r"\b(never|always|must|only)\b", re.I)
DATED = re.compile(r"\b20\d\d-\d\d-\d\d\b|\b\d\d-\d\d\b")
LINK = re.compile(r"\[[^\]]+\]\([^)]+\)")


def classify(line: str) -> str:
    if RULE.search(line):
        return "rule"
    if DATED.search(line):
        return "dated"
    if LINK.search(line):
        return "link"
    if line.lstrip().startswith("- "):
        return "bullet"
    return "prose"


def removed_lines(old: str, new: str) -> list:
    left = collections.Counter(new.split("\n"))
    out = []
    for line in old.split("\n"):
        if left[line] > 0:
            left[line] -= 1
        elif line.strip():
            out.append(line)
    return out


def is_reminder(rec: dict) -> bool:
    if rec.get("type") != "attachment":
        return False
    return bool(REMINDER.search(json.dumps(rec.get("attachment", {}), ensure_ascii=False)))


def is_prompt(rec: dict) -> bool:
    """A human turn: a user message whose content is text, not a tool result."""
    if rec.get("type") != "user" or rec.get("isMeta"):
        return False
    c = (rec.get("message") or {}).get("content")
    if isinstance(c, str):
        return True
    return isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "text" for b in c)


def tool_uses(rec: dict):
    if rec.get("type") != "assistant":
        return
    for b in (rec.get("message") or {}).get("content") or []:
        if isinstance(b, dict) and b.get("type") == "tool_use":
            yield b.get("name"), b.get("input") or {}


def scan_records(records, tally: dict) -> None:
    armed = False
    for rec in records:
        if is_reminder(rec):
            armed = True
            tally["reminders"] += 1
            continue
        if is_prompt(rec):
            armed = False
            continue
        for name, inp in tool_uses(rec):
            group = "after_reminder" if armed else "ordinary"
            if name == "Bash" and "MEMORY.md" in str(inp.get("command", "")):
                tally[group + "_bash"] += 1
                continue
            path = str(inp.get("file_path", ""))
            if not IS_INDEX.search(path):
                continue
            if name == "Write":
                tally[group + "_write"] += 1
                continue
            edits = inp.get("edits") if name == "MultiEdit" else [inp] if name == "Edit" else []
            for e in edits or []:
                tally[group + "_edits"] += 1
                gone = removed_lines(str(e.get("old_string", "")), str(e.get("new_string", "")))
                if gone:
                    tally[group + "_shrinking_edits"] += 1
                for line in gone:
                    tally[group + "_removed:" + classify(line)] += 1


def transcripts() -> list:
    out = []
    for d in glob.glob(os.path.join(ROOT, "*")):
        if "AppData-Local-Temp" in os.path.basename(d):
            continue
        out += glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True)
    return sorted(out)


def load(path: str):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def self_test() -> None:
    """Controls. Each would pass for the wrong reason if the scan could not tell the cases apart."""
    rem = {"type": "attachment", "attachment": {"content": [
        "The memory index at MEMORY.md is 22.1KB, approaching the 24.4KB read limit."]}}
    quoted = {"type": "user", "message": {"content": [{"type": "tool_result", "content":
              "The memory index at MEMORY.md is 22.1KB, approaching the 24.4KB read limit."}]}}
    edit = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {
        "file_path": "/x/memory/MEMORY.md", "old_string": "- never do X\nkeep\n", "new_string": "keep\n"}}]}}
    prompt = {"type": "user", "message": {"content": "next task"}}

    t = collections.Counter(); scan_records([rem, edit], t)
    assert t["after_reminder_removed:rule"] == 1 and t["ordinary_edits"] == 0, t
    t = collections.Counter(); scan_records([quoted, edit], t)
    assert t["reminders"] == 0 and t["ordinary_removed:rule"] == 1, "a quoted reminder is not one"
    t = collections.Counter(); scan_records([rem, prompt, edit], t)
    assert t["ordinary_edits"] == 1, "a new prompt ends the reminder's reach"
    topic = json.loads(json.dumps(edit)); topic["message"]["content"][0]["input"]["file_path"] = "/x/memory/a.md"
    t = collections.Counter(); scan_records([rem, topic], t)
    assert t["after_reminder_edits"] == 0, "only MEMORY.md is the index"
    print("self-test: 4 of 4 controls hold")


def main() -> int:
    self_test()
    if "--self-test" in sys.argv:
        return 0
    files = transcripts()
    t = collections.Counter()
    for i, f in enumerate(files, 1):
        scan_records(load(f), t)
        if i % 200 == 0:
            print("  %d/%d transcripts" % (i, len(files)), file=sys.stderr)
    print("transcripts scanned: %d" % len(files))
    for k in sorted(t):
        print("%-40s %d" % (k, t[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
