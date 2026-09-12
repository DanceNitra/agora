"""Every subagent brief carries its boundary, or the call does not happen.

THE RULE, from the owner, for this session and stated verbatim: *"Ked spustas subagenta, kazde
zadanie konci vetou: 'Do not post, comment, commit, push, or contact anyone. Report back only.'"*

WHY IT IS A HOOK AND NOT A HABIT. A subagent of ours once sent two unapproved comments and accepted
a role on the owner's behalf. The brief had no boundary and nothing checked for one. Everything that
has to be REMEMBERED here gets forgotten while attention is on the task: the humanizer skill, the
gate, the exit code after a pipe. The existing PreToolUse matcher is
`Bash|Write|Edit|MultiEdit|NotebookEdit`, so a subagent brief has never passed a single check.

IT FAILS CLOSED. A guard that exits 0 when its own parse breaks is the failure this repository keeps
paying for: a check that cannot see its target reporting SAFE. So an internal error blocks too, and
says loudly that the hook is the thing that broke, not the brief.

WHAT IT DOES NOT DO. It does not read the brief for intent, judge the task, or care what the agent is
for. One string, present or absent. A guard that fires on everything is wallpaper; this one is silent
on every brief that carries its sentence.
"""
from __future__ import annotations

import json
import sys

# The sentence itself. Whitespace is normalised on both sides, so a line break inside the brief is
# fine; the words and their order are what must be there.
REQUIRED = "Do not post, comment, commit, push, or contact anyone. Report back only."

# THE SECOND RULE, and it exists because of a measurement. When a subagent finishes, the harness
# leaves its transcript at ZERO bytes: 40 of 40 subagent output files on this machine, against
# 1 of 20 for background shell jobs. So a gate receipt pointing at that transcript records
# nothing, and the only surviving account of what the agent found is the --found text, which the
# main session writes. The evidence for "an adversarial pass ran" was my own prose about it.
#
# A brief must therefore tell the agent to write its own report to a file. Then the receipt can
# point at the agent's words instead of mine. This cannot prove authorship, and does not claim
# to; it removes the case where no independent artefact exists at all.
REPORT_PHRASE = "Write your full report to"
REPORT_SUFFIX = ".report.md"

# The tool names a subagent launch can arrive under. Matching on the payload as well as the settings
# matcher means a rename in one place cannot silently disable the check.
SUBAGENT_TOOLS = ("Task", "Agent")


def _norm(s: str) -> str:
    return " ".join((s or "").split())


def block(msg: str) -> "None":
    sys.stderr.write(msg + "\n")
    raise SystemExit(2)


def main() -> int:
    try:
        raw = sys.stdin.read()
        d = json.loads(raw) if raw.strip() else {}
    except Exception as e:                       # noqa: BLE001 - the hook names its own failure
        block("subagent_boundary: could not read the hook payload (%r). Blocking rather than "
              "passing, because a guard that fails open is the defect it exists to prevent." % e)

    if (d.get("tool_name") or d.get("tool") or "") not in SUBAGENT_TOOLS:
        return 0

    ti = d.get("tool_input") or {}
    prompt = ti.get("prompt") or ti.get("description") or ""
    flat = _norm(prompt)
    if not flat:
        block("subagent_boundary: the brief is empty, so it cannot carry its boundary sentence.")

    if _norm(REQUIRED) not in flat:
        block(
            "subagent_boundary: BLOCKED. This brief does not carry its boundary sentence.\n"
            "  Append, verbatim, as the last line of the prompt:\n"
            "    " + REQUIRED + "\n"
            "  The owner's rule for this session. A subagent of ours has already sent two\n"
            "  unapproved comments from a brief that lacked it."
        )

    if _norm(REPORT_PHRASE).lower() not in flat.lower() or REPORT_SUFFIX not in flat:
        block(
            "subagent_boundary: BLOCKED. This brief does not tell the agent where to write its "
            "report.\n"
            "  The harness leaves subagent transcripts EMPTY (40 of 40 measured here), so without\n"
            "  this the only surviving account of what the agent found is prose the main session\n"
            "  writes. Name a file under the session tasks directory, for example:\n"
            "    " + REPORT_PHRASE + " <tasks-dir>/<name>" + REPORT_SUFFIX + " before you reply."
        )

    # Advisory only: the rule says the brief ENDS with the sentence, but a trailing clarification
    # such as "Do not edit any file." is not a violation worth blocking a session over.
    if _norm(REQUIRED) not in _norm(prompt[-400:]):
        sys.stderr.write("subagent_boundary: the sentence is present but not near the end of the "
                         "brief; the rule says the brief ends with it.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
