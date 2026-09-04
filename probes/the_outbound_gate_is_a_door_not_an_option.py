"""Can a comment reach someone else's repository without passing the approved sender?

WHY. `tools/send_approved.py` refuses `--body`, binds a digest to the text actually sent, and checks
the verify, redteam and humanizer receipts. There is also an inspeximus hook that blocks outbound
posts. Both were escapable. The inspeximus hook names its own escape: prefix
`AGORA_OUTREACH_APPROVED=1` once the owner has approved. That flag records that a HUMAN said yes; it
checks nothing about the SHAPE of the command it then lets through, and the sender is a tool a
session has to choose to invoke.

CORRECTED 2026-09-04. This used to read "It happened three times on anthropics/claude-code#91188",
with those three comment ids attributed to us. Comments 5493443058, 5522927403 and 5538716005 were
posted by `pm25coder`, resolved from the live GitHub API; our `gh` holds one token, `DanceNitra`.
See `probes/who_actually_posted_it_resolved_from_the_live_api.py`. The failure mode is real and
belongs to the tool: `--body` takes text and only `--body-file` reads a file, so `--body @path.md`
posts the literal path, and a later edit repairs the page while the notification emails keep the
original. What is corrected is who hit it. The checks below are unchanged.

WHAT THIS CHECKS, by running the hook the way the harness runs it, on stdin, reading its exit code:
  1. EVERY WRITING FORM IS BLOCKED, including under `AGORA_OUTREACH_APPROVED=1`, because owner
     approval is not a claim about the command's shape.
  2. THE EXACT COMMAND SHAPE THAT CAUSED IT is blocked, verbatim.
  3. `gh api` with a writing method or field flag against a human-facing path is blocked. It is the
     back door: the same POST with none of the subcommand's shape.
  4. A WRAPPER IS UNWRAPPED: `bash -c "gh issue comment ..."` is blocked.
  5. READS ARE UNTOUCHED, and so is a MENTION. A command whose Python source merely quotes the
     string is not an invocation. The first version of this hook blocked exactly that, including
     this probe, and an over-broad gate gets switched off. A switched-off gate is the state being
     left behind, so this check is not politeness: it is the failure mode.
  6. THE SENDER PASSES, otherwise the gate has no door.
  7. IT FAILS CLOSED on a broken payload.
  8. THE HOOK IS WIRED into settings.json for Bash. A correct hook nobody registered is the same as
     no hook, which is how send_approved.py came to be bypassable in the first place.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HOOK = os.path.join(ROOT, ".claude", "hooks", "outbound_gate.py")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")
OUT = os.path.join(HERE, "the_outbound_gate_is_a_door_not_an_option.result.json")

GH = "gh"           # assembled, so this file's own source is not the thing under test
COMMENT = GH + " issue comment"
INCIDENT = COMMENT + ' 91188 -R anthropics/claude-code --body "@tmp/r112_91188_tonydzi_reply.md"'

MUST_BLOCK = [
    INCIDENT,
    COMMENT + " 12 -R o/r --body-file d.md",
    "AGORA_OUTREACH_APPROVED=1 " + INCIDENT,
    "AGORA_OUTREACH_APPROVED=1 " + COMMENT + " 12 -R o/r --body-file d.md",
    GH + " pr comment 5 -R o/r --body-file d.md",
    GH + " pr review 5 -R o/r --approve --body-file d.md",
    GH + " issue create -R o/r --title x --body-file d.md",
    GH + " pr create -R o/r --title x --body-file d.md",
    GH + " api repos/o/r/issues/1/comments -X POST -f body=@d.md",
    GH + " api -X PATCH repos/o/r/issues/comments/123 -f body=hello",
    GH + " api repos/o/r/pulls/1/reviews --input review.json",
    "cd /tmp && " + COMMENT + " 1 -R o/r --body-file d.md",
    'bash -c "' + COMMENT + ' 1 -R o/r --body-file d.md"',
]

MUST_ALLOW = [
    GH + " api repos/anthropics/claude-code/issues/91188/comments --paginate",
    GH + " issue view 91188 -R anthropics/claude-code",
    GH + " issue list -R o/r --limit 5",
    GH + " pr diff 5 -R o/r",
    GH + " search issues --author pm25coder --limit 5",
    'git commit -m "a local commit is not outbound"',
    # A MENTION, not an invocation. This is the shape the first version of the hook blocked.
    'python -c "cases = [\'' + COMMENT + ' 1 -R o/r\']; print(len(cases))"',
    "grep -rn '" + COMMENT + "' tools/",
    "python tools/send_approved.py drafts/d.md --sha abc -- "
    + COMMENT + " 91188 -R anthropics/claude-code --body-file drafts/d.md",
]


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def run(cmd):
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stderr or "").strip()


def main():
    if not os.path.isfile(HOOK):
        refuse("no hook at %s, so this check would pass by testing nothing" % HOOK)

    print("  MUST BLOCK (%d):" % len(MUST_BLOCK))
    for c in MUST_BLOCK:
        code, err = run(c)
        print("     %-11s %s" % ("blocked" if code == 2 else "LET THROUGH", c[:72]))
        if code != 2:
            refuse("NOT blocked, so the gate is still optional: %s" % c)
        if "send_approved" not in err:
            refuse("the block message does not name the sender, so it tells nobody what to do "
                   "instead: %s" % c)

    print()
    print("  MUST ALLOW (%d):" % len(MUST_ALLOW))
    for c in MUST_ALLOW:
        code, err = run(c)
        print("     %-11s %s" % ("allowed" if code == 0 else "BLOCKED", c[:72]))
        if code != 0:
            refuse("a read, a mention or an approved send was blocked. An over-broad gate gets "
                   "switched off, and a switched-off gate is the state being left behind: %s" % c)

    print()
    r = subprocess.run([sys.executable, HOOK], input="{not json",
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 2:
        refuse("a broken payload exited %d; the hook must fail closed, otherwise anything that "
               "confuses it is silently permitted" % r.returncode)
    print("  FAIL-CLOSED: a malformed payload blocks (exit 2) and names the hook as the cause")

    s = json.load(io.open(SETTINGS, encoding="utf-8"))
    wired = any("outbound_gate.py" in (h.get("command") or "")
                for e in (s.get("hooks", {}).get("PreToolUse") or [])
                if "Bash" in (e.get("matcher") or "")
                for h in e.get("hooks", []))
    print("  WIRED into settings.json PreToolUse for Bash: %s" % wired)
    if not wired:
        refuse("the hook exists but is not registered for Bash in .claude/settings.json. A correct "
               "hook nobody registered is the same as no hook, which is exactly how "
               "send_approved.py came to be bypassable")

    print()
    print("  VERDICT: the sender is the only door; reads, mentions and grep still pass.")
    json.dump({"script": os.path.basename(__file__),
               "blocked": len(MUST_BLOCK), "allowed": len(MUST_ALLOW),
               "fails_closed": True, "wired_for_bash": wired,
               "approval_env_var_does_not_bypass": True,
               "wrapper_unwrapped": True, "mention_is_not_an_invocation": True,
               "verbatim_incident_command_blocked": INCIDENT},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
