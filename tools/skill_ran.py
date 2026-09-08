"""Did a skill actually run in this session, on this draft? Ask the transcript, not the session.

WHY THIS EXISTS. `humanizer_receipt.py` accepts two kinds of evidence today: a subagent transcript,
or a `.report.md` the subagent wrote. Both assume the skill ran in a SUBAGENT. A skill invoked
directly, through the Skill tool, writes no file of its own, so the receipt refuses it and the only
way to satisfy the gate is to spend an agent on every outbound message. On 2026-09-08 that meant an
agent panel on a 35-word note saying a merge conflict was resolved.

The transcript is better evidence than either. The harness writes a `tool_use` record for every
Skill invocation, carrying the skill name, the arguments and a timestamp. This session can put words
in a `.report.md`; it cannot put a `tool_use` record into its own transcript without calling the
tool.

A RELATED GUARD WAS DEFEATED BY A SKILL CALL, and the difference matters. `owner_spoke.py`'s first
version tried to recognise HUMAN messages by text prefix, and the `Base directory for this skill:`
block the harness injects on every Skill invocation passed that filter: 94 of 229 leaks in a
20-transcript audit. That was a side effect of a Skill call impersonating something else. This reads
the invocation record itself, which is the very event being claimed, so the same trick has nothing
to impersonate.

WHAT THIS CHECKS, and each one closes a way of passing without running the skill:

  the skill was invoked      a tool_use record with name 'Skill' and this skill name
  on THIS draft              the draft's path appears in the invocation arguments, so a run on
                             yesterday's letter cannot certify today's
  recently                   within RECENT_HOURS, the same bound the receipt already applies to its
                             other evidence, so an older session's run cannot certify this draft
  in THIS session            only the current session's transcript is read

THE FIRST VERSION REQUIRED THE INVOCATION TO BE NEWER THAN THE DRAFT FILE, AND THAT WAS BACKWARDS.
A humanizer pass reads the old text and the rewritten file is its OUTPUT, so the run is always
earlier than the bytes it produced. Tested against three real invocations it rejected all three, two
of which had genuinely run on the named draft, and reported that the pass "ran on different bytes"
when it had not. mtime is the wrong instrument regardless: a checkout, a copy or an editor touch
moves it without changing a character.

Editing the draft after the pass is caught where it already was. `humanizer_receipt.py` binds every
receipt to the content sha256, so one changed character invalidates all three receipts.

WHAT IT CANNOT SHOW. That the skill's advice was applied. This is the same boundary the subagent
path has, since a `.report.md` does not prove its findings were acted on either. What changes is the
cost, not the strength.

Usage:
    python tools/skill_ran.py humanizer drafts/x.md          # exit 0 and print the record, or exit 1
    python tools/skill_ran.py humanizer drafts/x.md --json
"""
import argparse
import io
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECENT_HOURS = 12          # the bound humanizer_receipt.py already applies to its other evidence

# THE RECEIPT'S LABEL IS NOT THE SKILL'S NAME. `humanizer_receipt.py` records three skills as
# humanizer, redteam and verify, while the skills are called humanizer, stress-claim and
# verify-claims. Without this map a real verify-claims run was reported as "the transcript records no
# `verify` skill invocation", which is a true sentence about the wrong name.
ALIASES = {"verify": ("verify-claims", "verify"),
           "redteam": ("stress-claim", "redteam"),
           "humanizer": ("humanizer",)}


def transcript_path():
    """The current session's transcript, from the environment the harness sets."""
    p = os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    if p and os.path.isfile(p):
        return p
    # Fall back to the newest transcript for this project directory. Newest rather than any, because
    # an older session's Skill call is not evidence about this draft.
    slug = "C--" + os.path.abspath(ROOT).replace(":", "").replace("\\", "-").replace("/", "-").lstrip("-")
    d = os.path.join(os.path.expanduser("~/.claude/projects"), slug)
    if not os.path.isdir(d):
        return None
    files = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".jsonl")]
    return max(files, key=os.path.getmtime) if files else None


def find(skill, draft, tp):
    """Every Skill invocation of `skill` whose arguments name `draft`, newest first."""
    want = os.path.basename(draft)
    alt = os.path.relpath(os.path.abspath(draft), ROOT).replace(os.sep, "/")
    out = []
    with io.open(tp, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"Skill"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            for c in ((rec.get("message") or {}).get("content") or []):
                if not isinstance(c, dict) or c.get("type") != "tool_use" or c.get("name") != "Skill":
                    continue
                inp = c.get("input") or {}
                if inp.get("skill") not in ALIASES.get(skill, (skill,)):
                    continue
                args = str(inp.get("args") or "")
                if want not in args and alt not in args:
                    continue
                out.append({"timestamp": rec.get("timestamp"), "skill": skill,
                            "args_head": " ".join(args.split())[:300]})
    return sorted(out, key=lambda r: r["timestamp"] or "", reverse=True)


def epoch(ts):
    """ISO-8601 with a trailing Z to a float. Returns None rather than guessing on a bad value."""
    if not ts:
        return None
    try:
        return time.mktime(time.strptime(ts.split(".")[0], "%Y-%m-%dT%H:%M:%S")) - time.timezone
    except ValueError:
        return None


def check(skill, draft):
    """(record, None) when the skill ran on this draft recently, else (None, reason)."""
    if not os.path.isfile(draft):
        return None, "%s does not exist." % draft
    tp = transcript_path()
    if not tp:
        return None, ("no session transcript found, so nothing can be checked. Set "
                      "CLAUDE_TRANSCRIPT_PATH.")

    hits = find(skill, draft, tp)
    if not hits:
        return None, ("the transcript records no %s skill invocation naming %s. Invoke the skill "
                      "on this draft, then record the receipt."
                      % (" or ".join("`%s`" % a for a in ALIASES.get(skill, (skill,))),
                         os.path.basename(draft)))

    newest = hits[0]
    ran = epoch(newest["timestamp"])
    if ran is None:
        return None, ("the invocation carries no readable timestamp (%r), so it cannot be placed in "
                      "time at all." % newest["timestamp"])
    age_h = (time.time() - ran) / 3600.0
    if age_h > RECENT_HOURS:
        return None, ("the newest `%s` run naming this draft was %.1f hours ago, past the %d-hour "
                      "bound. That is evidence about an older draft; run the skill again."
                      % (skill, age_h, RECENT_HOURS))

    newest["transcript"] = tp.replace(os.sep, "/")
    newest["age_hours"] = round(age_h, 2)
    newest["runs_naming_this_draft"] = len(hits)
    return newest, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("skill")
    ap.add_argument("draft")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rec, why = check(a.skill, a.draft)
    if why:
        print("NO: %s" % why)
        return 1
    if a.json:
        print(json.dumps(rec, indent=1))
    else:
        print("YES: `%s` ran on %s at %s, %.1f h ago (%d run(s) naming this draft)."
              % (a.skill, os.path.basename(a.draft), rec["timestamp"], rec["age_hours"],
                 rec["runs_naming_this_draft"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
