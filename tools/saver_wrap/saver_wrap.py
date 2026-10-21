"""PreToolUse hook for Bash: run the command with its output passed through the inspeximus context saver.

Dogfooding 3.22 (owner, 2026-10-21: "ten kontext saver zapnite okamzite", hook permission given the same day).
The command text stays inline in the rewritten command, so the permission check still reads what runs. The exit
code is the command's own. Output under 5,000 bytes is printed unchanged; a larger output is printed as the
saver's digest, with the path of the full output for a follow-up read.
Off with AGORA_SAVER_WRAP=0. A background command is never wrapped, because its output is read from a file.
"""
import json
import os
import shlex
import sys

TAIL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saver_tail.py").replace("\\", "/")


def main():
    if os.environ.get("AGORA_SAVER_WRAP") == "0":
        return
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return
    ti = ev.get("tool_input") or {}
    cmd = ti.get("command")
    if not cmd or ti.get("run_in_background") or "saver_tail.py" in cmd:
        return
    intent = (ti.get("description") or "").strip()
    wrapped = (
        '__sv_out="$HOME/.claude/saver/out/$(date +%%Y%%m%%d-%%H%%M%%S)-$$.txt"; mkdir -p "$(dirname "$__sv_out")"\n'
        "{\n%s\n} > \"$__sv_out\" 2>&1; __sv_rc=$?\n"
        "python %s \"$__sv_out\" %s\n"
        "(exit $__sv_rc)"
    ) % (cmd, shlex.quote(TAIL), shlex.quote(intent))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "updatedInput": dict(ti, command=wrapped)}}))


if __name__ == "__main__":
    main()
