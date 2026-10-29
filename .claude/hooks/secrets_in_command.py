"""PreToolUse hook: a literal secret never goes on a command line.

WHY. A command line is logged in the transcript, shell history and sometimes the process list.
A key typed into it is leaked the moment the command runs, whatever the command does. The safe
pattern is to read the secret inside the program from a gitignored .env file or the environment.

WHAT IT BLOCKS: a Bash or PowerShell command that contains a value shaped like a known secret
(Anthropic, OpenAI, GitHub, Slack, AWS, Google API keys, Telegram bot tokens, private-key blocks,
JWTs) or a literal value after Authorization: Bearer, password=, token=, api_key=.
A reference to a variable ($TOKEN, ${env:KEY}, %KEY%) is allowed, because it carries no value.

The matched value is never echoed back; the message names only the kind of secret.
It fails closed: an unreadable payload blocks the call.
"""
from __future__ import annotations

import json
import re
import sys

TOOLS = ("Bash", "PowerShell")

SHAPES = [
    ("Anthropic API key", r"sk-ant-[A-Za-z0-9_-]{20,}"),
    ("OpenAI API key", r"sk-(proj-)?[A-Za-z0-9_-]{32,}"),
    ("GitHub token", r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}"),
    ("Slack token", r"xox[abprs]-[A-Za-z0-9-]{10,}"),
    ("AWS access key", r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"),
    ("Google API key", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    # No \b before the digits: in a URL the token follows "bot" directly (bot123...:AA...).
    ("Telegram bot token", r"(?<![0-9])\d{8,10}:[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])"),
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
]
SHAPES = [(n, re.compile(p)) for n, p in SHAPES]
# A literal value after a credential-looking name. A value that starts with $ or % or { is a
# reference, not a secret, and passes.
ASSIGN = re.compile(
    r"(Authorization:\s*Bearer\s+|(password|passwd|pwd|token|api[_-]?key|secret)\s*[=:]\s*)"
    r"(?P<v>[\"']?(?![$%{<])[^\s\"';&|]{12,})", re.I)


def check(command: str) -> str | None:
    for name, rx in SHAPES:
        if rx.search(command):
            return name
    m = ASSIGN.search(command)
    if m:
        return "literal credential value"
    return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        d = json.loads(raw) if raw.strip() else {}
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("secrets_in_command: could not read the hook payload (%r); blocking.\n" % (e,))
        return 2
    if d.get("tool_name") not in TOOLS:
        return 0
    kind = check(str((d.get("tool_input") or {}).get("command") or ""))
    if kind:
        sys.stderr.write("secrets_in_command: BLOCKED. The command contains a %s. Read the secret "
                         "inside the program from a gitignored .env file or an environment "
                         "variable instead.\n" % kind)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
