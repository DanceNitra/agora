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

WHAT IT CHECKS NOW, in the order the conditions have to hold:

  1. the harness recorded `show` printing THIS hash;
  2. a record the harness marked `origin.kind == "human"` arrived after that;
  3. no other draft's hash was displayed in between, so the reply is attributable;
  4. every sentence of the CURRENT bytes appeared in a message to him before that reply;
  5. the new material could physically have been read in the time available.

WHAT IT STILL CANNOT DO, and this is the honest boundary rather than a caveat. It cannot know he
read it, or that his message means yes. Nothing in a transcript carries either. Condition 5 is a
NECESSARY condition, not evidence of comprehension: it fires when 1,000 words a minute would have
been required, which is a rate nobody achieves, and stays silent on everything slower. Measured on
the two comments actually sent on 2026-09-01: 188 new words over 344 s (33 wpm) and 121 over 60 s
(122 wpm), so both real approvals sit 8x and 30x under the bar.

The guard's claim is therefore: he was shown this exact text, he answered afterwards, and he had
time to read what was new. Not that he agreed, and not that he read it.
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


def _norm(s: str) -> str:
    return " ".join((s or "").split())


def _tight(s: str) -> str:
    """Whitespace removed entirely, for comparing text against the same text re-wrapped.

    Collapsing runs of whitespace is not enough. A chat client wrapped a CJK string mid-run and the
    normaliser turned that break into a SPACE, so the file's 8条标签完全一致，但每条都在同一个方向上
    and the displayed 同一个 方向上 compared unequal. Between CJK characters a line break is not a
    space, and at 45 characters or more two different sentences do not collide once spacing is gone.
    """
    return "".join((s or "").split())


def _samples(body: str, floor: int = 45) -> list[str]:
    """Every substantial SENTENCE of the draft, whitespace-normalised.

    Two earlier grains were both wrong, and each was wrong in a way only a measurement showed.

    Contiguous windows of the assembled body failed a comment that had genuinely been shown: the
    full draft went out at 18:45 and a rewritten paragraph at 19:12, both before the reply, so every
    word was displayed and no single window matched, because the final text never existed
    contiguously in one message. A second round shows what changed, not the whole piece again.

    FILE LINES then failed on wrapping. A draft is hard-wrapped at about 100 characters and the same
    text pasted into chat breaks in different places, so three of 51 lines read as never shown when
    all three were on screen. That is the instrument disagreeing with itself, not a finding.

    Sentences survive both, because a sentence is the same string wherever it is wrapped.
    """
    b = _norm(body)
    out, seen = [], set()
    for s in re.split(r"(?<=[.!?:])\s+", b):
        s = s.strip()
        if len(s) >= floor and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def assistant_texts(path: str) -> list:
    out = []
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"assistant"' not in line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            m = r.get("message") or {}
            if m.get("role") != "assistant":
                continue
            t = _ts(r.get("timestamp"))
            txt = _norm(_text_of(m))
            if t and txt:
                out.append((t, txt))
    return out


def check(sha: str, project_dir: str | None = None, draft: str | None = None) -> tuple[bool, str]:
    """(ok, why). True only when the harness recorded a human speaking after this hash was shown.

    With `draft`, it also requires the TEXT to have been put in front of him. A hash is not a draft:
    `show` prints the digest to a tool result nobody reads aloud, so the first version of this proved
    only that a number had been computed. Measured against the two comments actually sent on
    2026-09-01: for both, the body appears in an assistant message before the reply, once 25 seconds
    after the show and once 27 minutes before it. So the rule is "pasted before the reply", not
    "pasted after the show" -- the order I assumed, and the measurement corrected.

    The samples come from the CURRENT bytes, so a paste of an older revision does not satisfy it.
    That is the property worth having: what he saw and what gets sent are the same text.
    """
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

        # WAS THE TEXT ITSELF PUT IN FRONT OF HIM, not just its digest?
        if draft:
            try:
                body = io.open(draft, encoding="utf-8").read()
            except Exception as e:
                return False, "could not read the draft to check it was shown: %r" % e
            want = _samples(body)
            if not want:
                # No sentence clears the length floor. A short draft is still a draft, so fall back
                # to the whole body rather than reporting "nothing to check", which reads as a pass
                # and is how a guard quietly stops guarding the smallest cases.
                whole = _norm(body)
                if not whole:
                    return False, "the draft file is empty, so there is nothing that could be shown"
                want = [whole]
            # THE QUALIFYING REPLY IS THE ONE THAT POSTDATES THE TEXT, not the first one after the
            # hash. Measured on a real send: the hash went up at 07:42:30, the owner said "ano
            # schvalujem" at 07:43:35, the letter itself was written out at 07:44:34, and "ok posli"
            # came at 07:50:20. Reading `after[0]` failed a send whose text HAD been displayed
            # before the approval that counts.
            #
            # This is stricter, not looser. An answer given before seeing the text is not an
            # approval of that text, so it does not qualify; only a message that comes after every
            # line has been shown does, and if none exists the send is still refused.
            asst = assistant_texts(p)
            first_shown, missing = {}, []
            for s in want:
                hits = [t for t, txt in asst if _tight(s) in _tight(txt)]
                if hits:
                    first_shown[s] = min(hits)
                else:
                    missing.append(s[:40])
            if missing:
                return False, ("%d of %d lines of THIS draft have never been put in front of him, "
                               "so no message of his can be an answer about the text. First "
                               "missing: %r" % (len(missing), len(want), missing[0]))
            complete = max(first_shown.values())
            qualifying = [(t, x) for t, x in after if t > complete]
            if not qualifying:
                return False, ("the whole draft was on screen at %s and he has not spoken since. "
                               "His last message, %s, came before the text was complete."
                               % (complete.isoformat(), after[-1][0].isoformat()))
            # EVERY qualifying message, not just the first. Taking `qualifying[0]` locked the
            # owner out by construction: once an instant "posli" landed, no later message could
            # ever be considered, however long he then spent reading. Measured 2026-09-06 on a
            # real send, where he replied in 8.4 s, was told to wait, and his next two messages
            # were still judged against the first one's timestamp. A guard that cannot be
            # satisfied after a fast first reply is not strict, it is broken.
            #
            # Nothing is loosened. Each candidate is still required to come after the whole draft
            # was on screen, and is still charged the full reading rate from the last NEW content
            # it follows. A later message simply gets its own honest measurement.
            carriers = {t for t in first_shown.values()}
            reply_at = reply_txt = None
            _why = None

            # COULD HE HAVE READ IT? Not whether he did, which no transcript can say.
            #
            # Only content that is NEW to him counts. Measured on the two comments sent 2026-09-01:
            # 188 new words over 344 s (33 wpm) and 121 over 60 s (122 wpm). A second round shows a
            # changed paragraph, so charging the reply for the whole draft would fail both.
            #
            # The ceiling is deliberately absurd rather than merely fast. Skim rates for technical
            # prose are argued about; nobody argues about 1,000 words a minute. Both real approvals
            # sit 8x and 30x under it, so this fires on an instant "ok" after a large new block and
            # on nothing else. A necessary condition, and the docstring says so.
            shown_at = {}
            for _s in want:
                hits = [t for t, txt in assistant_texts(p) if _tight(_s) in _tight(txt)]
                if hits:
                    shown_at[_s] = min(hits)
            for cand_at, cand_txt in qualifying:
                prev_msgs = [t for t, _ in humans if t < cand_at]
                since = max(prev_msgs) if prev_msgs else None
                fresh = [x for x, t in shown_at.items() if since is None or t > since]
                if fresh:
                    last_new = max(shown_at[x] for x in fresh)
                    secs = (cand_at - last_new).total_seconds()
                    words = sum(len(x.split()) for x in fresh)
                    wpm = words / (secs / 60.0) if secs > 0 else float("inf")
                    if wpm > 1000:
                        _why = ("%d new words were put in front of him and the reply came %.1f s "
                                "later, which is %.0f words a minute. Nobody reads at that rate, "
                                "so this is an acknowledgement rather than an answer about the "
                                "text." % (words, secs, wpm))
                        continue
                    rate = "%.0f wpm over %d new word(s)" % (wpm, words)
                else:
                    rate = "no content new since his previous message"
                reply_at, reply_txt = cand_at, cand_txt
                break
            if reply_at is None:
                return False, _why or "no qualifying message cleared the reading-rate check"
            after = [(reply_at, reply_txt)]
            return True, ("shown %s, all %d lines displayed across %d message(s), %s, human "
                          "replied %s: %r" % (anchor.isoformat(), len(want), len(carriers),
                                              rate, reply_at.isoformat(), after[0][1][:50]))

        return True, ("shown %s, human replied %s: %r  (TEXT NOT CHECKED: no draft path given)"
                      % (anchor.isoformat(), after[0][0].isoformat(), after[0][1][:60]))

    return False, ("no transcript records `show` printing this hash, so nobody can have been asked "
                   "about it. Run `show` on this exact file first.")
