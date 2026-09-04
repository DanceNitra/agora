"""Who posted it? Resolve the author from the live API before attributing anything to us.

WHY THIS EXISTS. On 2026-09-04 I spent hours building a public retraction of six comments a
stranger wrote. Three decision records in our own store said `pm25coder` on
anthropics/claude-code#91188 was our account. I wrote those records, never checked, and then
treated them as established fact. `gh auth status` refuted the whole chain in one call.

The class is older than the instance. A gate can check whether a claim is TRUE and never check
WHOSE claim it is, which is `a-check-with-no-subject-passed-two-wrong-attributions`. Here the
missing subject was our own identity.

WHAT THIS CHECKS, for any thread we are about to write into:
  1. The local `gh` identity, from `gh auth status`. That is the only account that can have
     posted as us from this host.
  2. Every comment on the thread, by author, fetched from the live API rather than from a
     memory record, a draft, or a subagent report.
  3. That every comment id a caller claims as ours is in fact authored by the local identity.

CONTROLS, because a check that cannot see its target reports SAFE:
  * POSITIVE CONTROL ON THE READER. The fetch must return a comment we know is ours before any
    "not ours" verdict counts. A thread that returns zero comments is a dead instrument, not an
    absence.
  * NEGATIVE CONTROL. The probe asserts that a known third-party id is reported as NOT ours. If
    everything comes back ours, the comparison is not running.
  * IDENTITY IS READ, NEVER ASSUMED. If `gh auth status` cannot be parsed, the run refuses. An
    unknown identity must not default to "probably us".
  * UNAUTHENTICATED READ PATH. Public issue comments are readable without a token, so an expired
    token degrades the reader for step 1 only and cannot silently change an author.

RUN IT before writing anything that accepts blame, corrects the record, or says "we published".
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "who_actually_posted_it_resolved_from_the_live_api.result.json")

REPO = "anthropics/claude-code"
ISSUE = 91188
# The fixture that made this probe necessary. Both controls are pinned here.
KNOWN_OURS = "5499087276"        # positive control: must resolve to the local identity
KNOWN_THEIRS = "5538716005"      # negative control: must resolve to somebody else
# Every id a session claimed as ours in a commit message or a memory record on 3-4 September.
CLAIMED_AS_OURS = ["5493443058", "5495840695", "5498341230",
                   "5522927403", "5533605446", "5538716005"]


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8", newline="\n"), indent=1)
    raise SystemExit(2)


def local_identity():
    """The only account that can have posted as us from this host."""
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=90)
    except Exception as exc:                                          # noqa: BLE001
        refuse("cannot run `gh auth status` (%s); identity must be read, never assumed" % exc)
    blob = (r.stdout or "") + (r.returncode and (r.stderr or "") or (r.stderr or ""))
    names = re.findall(r"Logged in to \S+ account (\S+)", blob)
    if not names:
        refuse("`gh auth status` names no account, so this host has no resolvable identity")
    return sorted(set(names))


def comments(repo, issue):
    """Every comment on the thread, by author, from the live API. No token required."""
    out, page = {}, 1
    while page <= 10:
        url = ("https://api.github.com/repos/%s/issues/%d/comments?per_page=100&page=%d"
               % (repo, issue, page))
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json", "User-Agent": "agora-attribution-probe"})
        try:
            with urllib.request.urlopen(req, timeout=90) as fh:
                batch = json.loads(fh.read().decode("utf-8"))
        except Exception as exc:                                      # noqa: BLE001
            refuse("live API read failed (%s); an unread thread is a dead instrument, not an "
                   "absence" % exc)
        if not batch:
            break
        for c in batch:
            out[str(c["id"])] = c["user"]["login"]
        page += 1
    return out


def main():
    ids = local_identity()
    by_id = comments(REPO, ISSUE)

    if not by_id:
        refuse("the thread returned zero comments; the reader is blind and every verdict is void")
    if KNOWN_OURS not in by_id:
        refuse("positive control %s is absent from the fetch, so the reader cannot see our own "
               "comments and no 'not ours' verdict counts" % KNOWN_OURS)
    if by_id[KNOWN_OURS] not in ids:
        refuse("positive control %s resolves to %r, which is not a local identity %r; either the "
               "fixture is stale or the identity read is wrong"
               % (KNOWN_OURS, by_id[KNOWN_OURS], ids))
    if by_id.get(KNOWN_THEIRS) in ids:
        refuse("negative control %s resolves to a local identity, so the comparison is not "
               "discriminating and everything would come back ours" % KNOWN_THEIRS)

    ours = sorted(i for i, a in by_id.items() if a in ids)
    verdicts = []
    for cid in CLAIMED_AS_OURS:
        author = by_id.get(cid)
        verdicts.append({"comment": cid, "author": author,
                         "claimed_as_ours": True,
                         "actually_ours": author in ids if author else None})
    wrong = [v for v in verdicts if v["actually_ours"] is not True]

    res = {
        "verdict": "MISATTRIBUTED" if wrong else "OK",
        "repo": REPO, "issue": ISSUE,
        "local_gh_identities": ids,
        "comments_on_thread": len(by_id),
        "authors": sorted(set(by_id.values())),
        "our_comments_on_this_thread": ours,
        "claimed_as_ours_but_are_not": [v["comment"] for v in wrong],
        "per_claim": verdicts,
        "controls": {"positive_control_id": KNOWN_OURS,
                     "positive_control_author": by_id[KNOWN_OURS],
                     "negative_control_id": KNOWN_THEIRS,
                     "negative_control_author": by_id.get(KNOWN_THEIRS)},
    }
    json.dump(res, io.open(OUT, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)

    print("  local gh identity: %s" % ", ".join(ids))
    print("  thread %s#%d: %d comments by %s" % (REPO, ISSUE, len(by_id),
                                                 ", ".join(res["authors"])))
    print("  our comments there: %s" % ", ".join(ours))
    print("  claimed as ours but are not: %s" % ", ".join(res["claimed_as_ours_but_are_not"]))
    print("  verdict: %s" % res["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
