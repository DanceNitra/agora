"""Did the owner actually speak after we showed him this hash?

WHY. `send_approved.py` binds the bytes to a digest, which closed "approved one thing, sent another".
It does not close the layer under it: I compute the digest, print it, and pass it back. Every
artefact in that chain is mine, so "the owner approved this" was my own assertion wearing a hash.

WHAT THIS ESTABLISHES, and it is narrower than it sounds. It cannot know that a message means yes,
and a keyword list for that would be brittle and gameable. It establishes one fact I cannot author:
between the moment the harness recorded this hash being displayed and now, a message whose ORIGIN
the harness marked `human` arrived in that same session.

THE FIRST VERSION FAILED OPEN, AND AN ADVERSARIAL PASS MEASURED IT. Two defects, both fatal:

  * It excluded machine messages by matching text PREFIXES. Measured across 20 transcripts and
    24,679 `role: user` records: 229 machine-authored records passed that filter, recall 80.6%. The
    largest group, 94 of them, reads `Base directory for this skill: ...` and is injected whenever
    the assistant calls the Skill tool. **One Skill call satisfied the guard.** Also leaking:
    compaction summaries, skill re-invocations, and a `/loop` prompt whose text says "owner asleep".
    The harness marks every record's `origin`: 1,571 `human`, 931 `task-notification`, one
    `auto-continuation`. Keyed on that field the same corpus admits all 1,571 humans and rejects all
    229 leaks. Read the field the harness writes, not the words it happens to contain.

  * The anchor was a JSON file this session writes. Backdating one line made every human message
    already on disk satisfy the check, for any hash, unconditionally. The anchor is now the
    harness's own record of `show` printing `sha256 : <hash>` to stdout: 77 such records exist here.
    That is an event this session can CAUSE but cannot RE-TIME, which is the whole difference.

STILL TRUE AND WORTH SAYING: an active session produces a human message every few minutes, so this
proves the owner was present and speaking, not that he read the draft. It is a floor, not a proof.
"""
from __future__ import annotations

import datetime as _dt
import glob
import io
import json
import os
import re

SHOW_LINE = re.compile(r"sha256 : ([0-9a-f]{64})")


def _transcripts(project_dir: str | None = None) -> list[str]:
    d = project_dir or os.path.expanduser(
        os.path.join("~", ".claude", "projects", "C--Users-Danculus-agora"))
    return sorted(glob.glob(os.path.join(d, "*.jsonl")), key=os.path.getmtime)


def _ts(s):
    """Parse a transcript timestamp, or None. Comparing ISO strings with `>` looks right and is not:
    a local-offset stamp an hour BEFORE the anchor sorts after it as text."""
    if not isinstance(s, str) or not s:
        return None
    try:
        return _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(_dt.timezone.utc)
    except Exception:
        return None


def _text_of(msg: dict) -> str:
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _origin_kind(rec: dict):
    o = rec.get("origin")
    if isinstance(o, dict):
        return o.get("kind")
    return o if isinstance(o, str) else None


def scan(path: str):
    """(shows, humans) for one transcript. shows: [(time, sha)]. humans: [(time, text)]."""
    shows, humans = [], []
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"role"' not in line and "sha256 : " not in line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            t = _ts(r.get("timestamp"))
            if t is None:
                continue
            tur = r.get("toolUseResult")
            out = tur.get("stdout") if isinstance(tur, dict) else (tur if isinstance(tur, str) else "")
            m = SHOW_LINE.search(out or "")
            if m:
                shows.append((t, m.group(1)))
            msg = r.get("message") or {}
            if msg.get("role") == "user" and _origin_kind(r) == "human":
                txt = " ".join(_text_of(msg).split())
                if txt:
                    humans.append((t, txt))
    return shows, humans


def check(sha: str, project_dir: str | None = None) -> tuple[bool, str]:
    """(ok, why). True only when the harness recorded a human speaking after this hash was shown."""
    paths = _transcripts(project_dir)
    if not paths:
        return False, "no session transcript found, so no owner message can be established"

    # Only the transcript that actually contains the show matters: a human message in ANOTHER
    # session is not an answer to a hash displayed in this one.
    for p in reversed(paths):
        shows, humans = scan(p)
        mine = [t for t, h in shows if h == sha.lower()]
        if not mine:
            continue
        anchor = max(mine)
        after = [(t, x) for t, x in humans if t > anchor]
        if not after:
            last = max([t for t, _ in humans], default=None)
            return False, ("the hash was shown at %s and the harness has recorded no human message "
                           "since. Last human message: %s"
                           % (anchor.isoformat(), last.isoformat() if last else "none in this session"))
        # TWO DRAFTS IN FLIGHT. If another hash was displayed between this anchor and the answer,
        # one "ok" would unlock both and there is no way to tell which one it meant.
        between = sorted({h for t, h in shows if anchor < t < after[0][0] and h != sha.lower()})
        if between:
            return False, ("another draft's hash (%s) was shown between this one and the reply, so "
                           "the reply cannot be attributed to this draft. Show this draft again and "
                           "get a fresh answer." % between[0][:16])
        return True, ("shown %s, human replied %s: %r"
                      % (anchor.isoformat(), after[0][0].isoformat(), after[0][1][:60]))

    return False, ("no transcript records `show` printing this hash, so nobody can have been asked "
                   "about it. Run `show` on this exact file first.")
