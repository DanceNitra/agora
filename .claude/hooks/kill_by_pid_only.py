"""PreToolUse hook: a process is stopped by its PID, never by its image name.

WHY. On a shared machine several sessions run the same interpreter. `taskkill /IM python.exe`
stops all of them, including long jobs that belong to someone else. Measured on our own machine
on 2026-09-18: one such command stopped three running research jobs. A rule in CLAUDE.md did not
prevent the repeat; a hook does.

WHAT IT BLOCKS (Bash and PowerShell commands):
  taskkill /IM ..., taskkill /FI "IMAGENAME ...", pkill, killall,
  Stop-Process -Name / -ProcessName, kill -s by name via `pgrep | xargs kill`,
  Get-Process <name> | Stop-Process, wmic process where name=... delete.
WHAT IT ALLOWS: Stop-Process -Id <number>, taskkill /PID <number>, kill <number>.
A PID of 0 or 4 is blocked too: an empty lookup turned into PID 0 once and hit System.

It fails closed: an unreadable payload blocks the call and names the hook as the cause.
"""
from __future__ import annotations

import json
import re
import sys

TOOLS = ("Bash", "PowerShell")

BY_NAME = [
    (re.compile(r"\btaskkill\b[^\n|;&]*?/(IM|FI)\b", re.I), "taskkill by image name or filter"),
    (re.compile(r"(^|[\s;&|(])pkill\b", re.I), "pkill matches by name"),
    (re.compile(r"(^|[\s;&|(])killall\b", re.I), "killall matches by name"),
    (re.compile(r"\bStop-Process\b[^\n|;]*?-(Name|ProcessName)\b", re.I), "Stop-Process -Name"),
    (re.compile(r"\bGet-Process\b[^\n|;]*\|\s*Stop-Process\b", re.I), "Get-Process | Stop-Process"),
    (re.compile(r"\bpgrep\b[^\n;]*\|\s*xargs\s+kill\b", re.I), "pgrep | xargs kill"),
    (re.compile(r"\bwmic\b[^\n]*\bprocess\b[^\n]*\bname\s*=[^\n]*\bdelete\b", re.I), "wmic by name"),
]
SYSTEM_PID = re.compile(
    r"(\bStop-Process\b[^\n|;]*-Id\s+|\btaskkill\b[^\n|;]*/PID\s+|(^|[\s;&|(])kill\s+(-\d+\s+|-9\s+)?)"
    r"(0|4)\b", re.I)
# Stop-Process -Id with a variable is allowed only when the variable cannot be empty; we cannot
# know that, so a bare $var is passed through and the PID-0 check above catches the literal case.


SHELLS = re.compile(r"(^|[\s;&|(])(bash|sh|zsh|pwsh|powershell)(\.exe)?\b[^\n]*<<", re.I)
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(?P<tag>[A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n(?P<body>.*?)\n\s*(?P=tag)\s*(\n|$)",
                     re.S)


def strip_heredocs(command: str) -> str:
    """Drop heredoc bodies that are data (a commit message, a script being written). A heredoc
    fed to a shell keeps its body, because the shell runs it."""
    out, pos = [], 0
    for m in HEREDOC.finditer(command):
        line_start = command.rfind("\n", 0, m.start()) + 1
        if SHELLS.search(command[line_start:m.start() + 2]):
            continue
        out.append(command[pos:m.start("body")])
        pos = m.end("body")
    out.append(command[pos:])
    return "".join(out)


def block(msg: str) -> None:
    sys.stderr.write("kill_by_pid_only: BLOCKED. " + msg + "\n")
    raise SystemExit(2)


SEARCH_QUOTED = re.compile(r"(\b(grep|egrep|rg|findstr|Select-String)\b[^\"'\n;|&]*)(\"[^\"]*\"|'[^']*')", re.I)


def check(command: str) -> str | None:
    command = strip_heredocs(command)
    # A search pattern that mentions taskkill is text being searched for, not a command.
    prev = None
    while prev != command:
        prev, command = command, SEARCH_QUOTED.sub(r'\1""', command)
    for pat, why in BY_NAME:
        if pat.search(command):
            return why
    if SYSTEM_PID.search(command):
        return "PID 0 or 4 is the system; an empty PID lookup must stop the kill, not reach it"
    return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        d = json.loads(raw) if raw.strip() else {}
    except Exception as e:  # noqa: BLE001
        block("could not read the hook payload (%r); blocking rather than guessing." % (e,))
    if d.get("tool_name") not in TOOLS:
        return 0
    why = check(str((d.get("tool_input") or {}).get("command") or ""))
    if why:
        block(why + ". Stop only processes this session started, by PID: "
              "Stop-Process -Id <pid> or taskkill /PID <pid>.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
