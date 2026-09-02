"""Did the owner actually say something after we showed him the hash?

WHY. `send_approved.py` binds the bytes to a digest, which closed the "approved one thing, sent
another" hole. It does not close the one underneath: the digest is computed by me, printed by me,
and passed back by me. Every artefact in that chain is mine. "The owner approved this" has been an
assertion of mine wearing a hash.

WHAT THIS ADDS, and it is narrower than it sounds. It cannot know that a message means yes, and any
keyword list for that would be brittle and gameable. It establishes one fact I cannot author: after
the moment the hash was displayed, a REAL message from the owner arrived in the session transcript,
which the harness writes and I do not.

THE TRAP THAT SHAPES THE FILTER. Task notifications, hook output and system reminders are all
recorded with `role: user`. A run that counted those would treat a background job finishing as
consent, which is worse than no check: the standing session rule says the opposite, in those words.
So every message whose text begins with one of the machine markers is excluded, and the module
refuses rather than passes when it cannot tell.

FAILS CLOSED. No transcript, no readable record, no qualifying message: refuse. A guard that waves
the send through when it cannot see is the failure this repository keeps paying for.
"""
from __future__ import annotations

import glob
import io
import json
import os
import time

# Recorded by `show`, read by `post`. It holds only WHEN a hash was displayed, never whether anyone
# agreed with it, so forging it buys nothing on its own: the message still has to exist.
STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "agora_output", "gate", "shown_hashes.json")

# A `role: user` entry starting with any of these was written by the machine, not by a person.
MACHINE_PREFIXES = (
    "<task-notification>", "<system-reminder>", "<local-command-stdout>",
    "[inspeximus]", "caveat: the messages below", "<command-name>", "<command-message>",
    "<user-prompt-submit-hook>", "preToolUse", "PostToolUse", "tool_use_error",
)


def _transcripts(project_dir: str | None = None) -> list[str]:
    d = project_dir or os.path.expanduser(
        os.path.join("~", ".claude", "projects", "C--Users-Danculus-agora"))
    return sorted(glob.glob(os.path.join(d, "*.jsonl")), key=os.path.getmtime)


def _text_of(msg: dict) -> str:
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


def owner_messages(path: str) -> list[tuple[str, str]]:
    """(timestamp, text) for every message a PERSON sent, machine entries excluded."""
    out = []
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"role"' not in line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            m = r.get("message") or {}
            if m.get("role") != "user":
                continue
            t = " ".join(_text_of(m).split())
            if not t:
                continue
            low = t.lower()
            if any(low.startswith(p.lower()) for p in MACHINE_PREFIXES):
                continue
            ts = r.get("timestamp")
            if ts:
                out.append((ts, t))
    return out


def record_shown(sha: str) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    try:
        d = json.load(io.open(STATE, encoding="utf-8"))
    except Exception:
        d = {}
    d[sha] = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    # Keep the file small; only recent hashes can be in play.
    if len(d) > 200:
        d = dict(sorted(d.items(), key=lambda kv: kv[1])[-200:])
    json.dump(d, io.open(STATE, "w", encoding="utf-8"), indent=1)


def check(sha: str, project_dir: str | None = None, state: str | None = None) -> tuple[bool, str]:
    """(ok, why). ok is True only when a person spoke after this hash was displayed."""
    st = state or STATE
    try:
        shown = json.load(io.open(st, encoding="utf-8"))
    except Exception as e:
        return False, ("no record that this hash was ever shown (%s: %r). Run `show` first, paste "
                       "the draft to the owner with the hash, and post only after he answers." % (st, e))
    when = shown.get(sha)
    if not when:
        return False, ("this hash was never displayed by `show`, so nobody can have approved it. "
                       "%d other hashes are on record." % len(shown))
    paths = _transcripts(project_dir)
    if not paths:
        return False, "no session transcript found, so no owner message can be established"
    msgs = [m for p in paths for m in owner_messages(p)]
    if not msgs:
        return False, ("the transcript holds no messages from a person at all, only machine "
                       "entries. Refusing rather than treating a notification as consent.")
    after = [m for m in msgs if m[0] > when]
    if not after:
        return False, ("the hash was shown at %s and no message from a person has arrived since. "
                       "The last one was at %s: %r" % (when, msgs[-1][0], msgs[-1][1][:60]))
    return True, ("owner spoke %d time(s) after the hash was shown at %s; first was %s: %r"
                  % (len(after), when, after[0][0], after[0][1][:60]))
