"""Has this draft already gone out? Ask the DESTINATION, never the drafts folder.

WHY THIS EXISTS. On 2026-08-18 I told the owner that a retraction was "an unsent draft" because the
file sat in `agora_output/drafts/`. It had been public on deepseek-ai/DeepSeek-V3#1466 for two days
(comment 5309136671, posted 16 August). I described the state of an outward artifact from a local
file and never asked the thread. The whole briefing that followed was built on that.

A file in `drafts/` is not evidence that its contents were not sent. Nothing removes a draft when it
is posted, so the folder is a record of what was WRITTEN, never of what was SENT.

    python tools/draft_sent_check.py agora_output/drafts/<file>.md

It resolves the destination from the filename or the draft body (e.g. `deepseek1466_...` ->
deepseek-ai/DeepSeek-V3#1466), pulls every comment we authored on that thread, and compares
normalised text. Exit 1 if a match is found, so it can gate a command.

CONTROL: `--self-test` runs it against a draft KNOWN to have been posted and fails loudly if the
matcher cannot find it. A checker that answers "not sent" for everything is the same defect one level
up, and that is exactly the mistake it exists to stop.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

OUR_LOGIN = "DanceNitra"

# filename or body slug -> (owner/repo, issue number)
KNOWN = {
    "deepseek1466": ("deepseek-ai/DeepSeek-V3", 1466),
    "deepseek1121": ("deepseek-ai/DeepSeek-V3", 1121),
    "deepseek1462": ("deepseek-ai/DeepSeek-V3", 1462),
    "cml289": ("safal207/Causal-Memory-Layer", 289),
    "popoto588": ("tomcounsell/popoto", 588),
}


def normalise(s: str) -> str:
    s = re.sub(r"https?://\S+", " ", s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())


def resolve_target(path: pathlib.Path, body: str):
    name = path.name.lower()
    for slug, target in KNOWN.items():
        if slug in name:
            return target
    m = re.search(r"([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)#(\d+)", body)
    if m:
        return m.group(1), int(m.group(2))
    m = re.search(r"github\.com/([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)/issues/(\d+)", body)
    if m:
        return m.group(1), int(m.group(2))
    return None, None


def our_comments(repo: str, number: int):
    out = subprocess.run(
        ["gh", "issue", "view", str(number), "--repo", repo, "--json", "comments"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:200] or "gh failed")
    data = json.loads(out.stdout)
    return [c for c in data.get("comments", [])
            if (c.get("author") or {}).get("login") == OUR_LOGIN]


WINDOW = 12


def best_match(body: str, comments):
    """Match on ANCHORS SAMPLED ACROSS the draft, not on its opening.

    The first version compared leading words and its own self-test caught the flaw: a draft that has
    since gained a header -- the "DO NOT SEND" banner this repository puts on withdrawn drafts is
    exactly that -- no longer starts like the comment it became, so a leading-run matcher reports
    "not sent" for a draft that is demonstrably public. Anchors taken from throughout the body
    survive a prepended header, an edited opening, and a trailing signature.
    """
    d = normalise(body).split()
    if len(d) < WINDOW:
        return 0, None
    step = max(1, len(d) // 12)
    anchors = [" ".join(d[i:i + WINDOW]) for i in range(0, len(d) - WINDOW, step)]
    best = (0, None)
    for c in comments:
        hay = " ".join(normalise(c.get("body", "")).split())
        hits = sum(1 for a in anchors if a in hay)
        if hits > best[0]:
            best = (hits, c)
    return best


def check(path: pathlib.Path, quiet: bool = False) -> int:
    body = path.read_text(encoding="utf-8")
    repo, number = resolve_target(path, body)
    if not repo:
        if not quiet:
            print("target unresolved for %s -- add its slug to KNOWN or name the thread in the body"
                  % path.name)
        return 2
    try:
        comments = our_comments(repo, number)
    except Exception as exc:
        if not quiet:
            print("could not reach %s#%d: %s" % (repo, number, exc))
        return 2
    score, hit = best_match(body, comments)
    if not quiet:
        print("draft   : %s" % path.name)
        print("thread  : %s#%d   our comments there: %d" % (repo, number, len(comments)))
    if score >= 3 and hit is not None:
        if not quiet:
            print("MATCH   : %d anchors of %d words found in that comment" % (score, WINDOW))
            print("SENT    : %s  (%s)" % (hit.get("url"), (hit.get("createdAt") or "")[:10]))
            print()
            print("This draft -- or a version of it -- IS ALREADY PUBLIC. Do not describe it as unsent.")
        return 1
    if not quiet:
        print("no comment of ours on that thread matches this text (best: %d anchors)" % score)
        print("NOT FOUND -- which is not the same as 'never sent'; it may have gone by another route.")
    return 0


def self_test() -> int:
    """BOTH directions. A checker that only ever says "sent" is as useless as one that only says
    "not sent", and my first negative control was fake -- it re-used the same posted draft, so it
    could not have failed."""
    known_sent = pathlib.Path("agora_output/drafts/deepseek1466_withdrawing_the_units_objection.md")
    if not known_sent.exists():
        print("SELF-TEST INCONCLUSIVE: control draft missing at %s" % known_sent)
        return 2

    pos = check(known_sent, quiet=True)
    ok_pos = pos == 1
    print("  [%s] POSITIVE: a draft that really was posted is found (rc=%d)"
          % ("PASS" if ok_pos else "FAIL", pos))

    # NEGATIVE: same thread, same length, text that was never posted anywhere.
    body = known_sent.read_text(encoding="utf-8")
    scrambled = " ".join("zz%s" % w for w in normalise(body).split())
    tmp = known_sent.with_name("_selftest_never_sent_deepseek1466.md")
    try:
        tmp.write_text(scrambled, encoding="utf-8")
        neg = check(tmp, quiet=True)
    finally:
        if tmp.exists():
            tmp.unlink()
    ok_neg = neg == 0
    print("  [%s] NEGATIVE: text that was never posted is NOT reported as sent (rc=%d)"
          % ("PASS" if ok_neg else "FAIL", neg))

    if ok_pos and ok_neg:
        print("SELF-TEST PASS: the matcher can say both yes and no.")
        return 0
    print("SELF-TEST FAIL: a one-sided checker is the defect it exists to prevent.")
    return 1


def main(argv) -> int:
    if "--self-test" in argv:
        return self_test()
    if len(argv) < 2:
        print(__doc__)
        return 2
    return check(pathlib.Path(argv[1]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
