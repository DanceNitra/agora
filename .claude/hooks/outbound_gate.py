"""Nothing reaches another person's repository except through the approved sender.

WHY THIS IS A HOOK. `tools/send_approved.py` already refuses `--body` and demands `--body-file`,
so the digest can bind the text that is actually sent. It refuses without the three skill receipts.
It requires the owner to have spoken after the draft was on screen. All of that is correct, and all
of it is OPT-IN: a session that calls `gh issue comment` directly meets none of it, and nothing
stops that.

It happened three times on anthropics/claude-code#91188. Comments 5493443058, 5522927403 and
5538716005 were posted with a body of `@tmp/<file>.md`, the literal string, because `--body` takes
text and only `--body-file` reads a file. Each was edited to the real content afterwards, one of
them 15 hours later, so the web page reads correctly and the defect is invisible there. The
notification emails are not editable: every subscriber to an Anthropic issue received a comment
from us whose entire body was a path on this machine.

So the class is not "the wrong flag". The class is that our outbound gate is a tool we have to
remember to use, on a machine where forgetting is the documented failure mode. This makes the gate
the only door.

WHAT IT BLOCKS. A Bash command that posts, edits or opens anything on a repository: `gh issue
comment`, `gh pr comment`, `gh pr review`, `gh issue create`, `gh pr create`, `gh release create`,
and any `gh api` with a writing method against a comments, issues, pulls or reviews path.

WHAT IT ALLOWS. Reads of every kind, and the same actions when they run through
`tools/send_approved.py`, which is where the receipts and the owner's approval are enforced.

IT MATCHES AN INVOCATION, NOT A MENTION. The first version searched the whole command string, and
blocked a probe whose Python source merely quoted the command it was testing. An over-broad gate
gets switched off, and a switched-off gate is the state being left behind, so the match now runs
per shell segment and only where `gh` is the command being run. A wrapper is unwrapped: `bash -c
"..."` and `sh -c "..."` are re-examined inside.

RESIDUAL GAP, stated rather than hidden: a command assembled at runtime, or run from a script file,
is invisible here. This hook narrows the door, it does not seal the building. What it does cover is
every form that has actually been used.

IT FAILS CLOSED, for the same reason the sibling hook does: a guard that exits 0 when its own parse
breaks is the failure this repository keeps paying for. An internal error blocks and says the hook
is what broke.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

SENDER = "send_approved.py"

# (subcommand, action) pairs that put text in front of a human on someone else's repository.
WRITING_SUBCOMMANDS = {
    ("issue", "comment"), ("issue", "create"), ("issue", "edit"),
    ("pr", "comment"), ("pr", "create"), ("pr", "edit"), ("pr", "review"),
    ("release", "create"), ("gist", "create"),
}

# `gh api` is the back door: the same POST with none of the subcommand's shape.
API_WRITE_METHOD = re.compile(r"^(?:-X|--method)$", re.I)
API_WRITE_VERB = re.compile(r"^(POST|PATCH|PUT|DELETE)$", re.I)
API_FIELD_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input"}
API_HUMAN_PATH = re.compile(r"(?:issues|pulls|comments|reviews|discussions|releases)\b")

# Shell separators that begin a new command. `gh` after one of these is an invocation; `gh` inside
# a quoted Python string is not, which is the distinction the first version of this hook missed.
SEPARATORS = re.compile(r"(?:\|\||&&|[;|&\n(){}]|\$\()")
ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
WRAPPERS = {"bash", "sh", "zsh", "pwsh", "powershell"}


def _tokens(segment):
    try:
        return shlex.split(segment, posix=True)
    except ValueError:                           # unbalanced quotes: fall back to whitespace
        return segment.split()


def _gh_invocations(cmd, depth=0):
    """Every `gh ...` argv in `cmd` where gh is the command being RUN, wrappers unwrapped."""
    out = []
    if depth > 3:
        return out
    for seg in SEPARATORS.split(cmd):
        toks = _tokens(seg)
        while toks and (ENV_ASSIGN.match(toks[0]) or toks[0] in ("env", "exec", "sudo", "time",
                                                                 "nohup", "command")):
            toks = toks[1:]
        if not toks:
            continue
        head = toks[0].replace("\\", "/").rsplit("/", 1)[-1]
        if head in ("gh", "gh.exe"):
            out.append(toks)
        elif head in WRAPPERS:
            for i, t in enumerate(toks[1:], 1):          # bash -c "<command>"
                if t == "-c" and i + 1 < len(toks):
                    out.extend(_gh_invocations(toks[i + 1], depth + 1))
    return out


def block(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    raise SystemExit(2)


def main() -> int:
    try:
        raw = sys.stdin.read()
        d = json.loads(raw) if raw.strip() else {}
    except Exception as e:                       # noqa: BLE001 - the hook names its own failure
        block("outbound_gate: could not read the hook payload (%r). Blocking rather than guessing; "
              "the hook is what broke, not the command." % (e,))
        return 2

    if (d.get("tool_name") or "") != "Bash":
        return 0
    cmd = ((d.get("tool_input") or {}).get("command") or "")
    if not cmd.strip():
        return 0

    # The sender is the door. Anything running through it has already met the receipts, the digest
    # and the owner's approval, so it passes here without further inspection.
    if SENDER in cmd:
        return 0

    hit = None
    for argv in _gh_invocations(cmd):
        words = [a for a in argv[1:] if not a.startswith("-")]
        if len(words) >= 2 and (words[0], words[1]) in WRITING_SUBCOMMANDS:
            hit = "gh %s %s" % (words[0], words[1])
            break
        if words[:1] == ["api"]:
            path = " ".join(words[1:])
            writes = any(a in API_FIELD_FLAGS for a in argv) or any(
                API_WRITE_METHOD.match(a) and i + 1 < len(argv)
                and API_WRITE_VERB.match(argv[i + 1]) for i, a in enumerate(argv))
            if writes and API_HUMAN_PATH.search(path):
                hit = "gh api (writing method or field against a human-facing path)"
                break
    if not hit:
        return 0

    block(
        "outbound_gate: BLOCKED. This command posts to a repository without going through the "
        "approved sender.\n"
        "  matched: %s\n"
        "  command: %s\n\n"
        "Use:  python tools/send_approved.py <draft.md> --sha <digest> -- "
        "gh issue comment N -R owner/repo --body-file <draft.md>\n\n"
        "Why this is enforced rather than advised: on anthropics/claude-code#91188 three of our "
        "comments went out with a body of '@tmp/<file>.md', the literal string, because --body "
        "takes text and only --body-file reads a file. Each was edited afterwards, one of them 15 "
        "hours later, so the page reads correctly. The notification emails are not editable: every "
        "subscriber received a comment from us whose entire body was a local path.\n"
        "The sender refuses --body, binds the digest to the text actually sent, and checks the "
        "verify, redteam and humanizer receipts. Reads are untouched by this hook."
        % (hit, cmd.strip()[:400]))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
