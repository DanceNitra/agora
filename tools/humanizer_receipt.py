"""Bind a humanizer-SKILL pass to the exact bytes it was run on, so a gate can require it.

WHY THIS EXISTS. The owner has now said three times that outbound drafts must go through the
humanizer SKILL, and three times I have substituted something cheaper: first `tools/humanizer_tells.py`
(a pattern scanner, not a rewrite), then the skill's rules applied from memory. Both feel like the
pass and neither is one. His instruction on 2026-08-26 was not "remember to" but "wire it in":

    "a hlavne si zadrotuj ze kazdy komentar pojde cez SKILL HUMANIZER lebo to stale nepouzivas"

A rule you have to recall is a rule you break while thinking about something else, so this is a
receipt a gate can check rather than a habit.

HOW IT WORKS, and the design point is the binding. The receipt is keyed by the SHA-256 of the draft
CONTENT, not by its path. Edit a single character after the pass and the key no longer matches, the
gate finds no receipt, and it fails. That closes the obvious hole, which is running the skill, then
rewriting the sentence it objected to, then shipping.

    python tools/humanizer_receipt.py record <draft.md> --found "a signpost; two negative
        parallelisms; a subjectless fragment" --before 383 --after 360
    python tools/humanizer_receipt.py check <draft.md>          # exit 1 if absent or stale

WHAT IT CANNOT DO is verify the skill actually ran; only that someone recorded it having run, with
findings, against these exact bytes. That is a real limit and it is written here rather than
implied. What it does buy: the receipt cannot be produced by accident, it cannot survive an edit,
and `--found` refuses to be empty, so recording a pass that found nothing takes a deliberate
sentence saying so.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "agora_output", "humanizer_receipts")


def sha(path: str) -> str:
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


# The three skills the owner means by "the gate". `--humanizer-skill-ran` used to be a bare FLAG on
# the send path, which is exactly as strong as remembering: I could pass it without running
# anything, and on 2026-08-26 I did, for all three. So each one is a RECEIPT bound to the draft's
# content, and the send path refuses without them.
SKILLS = ("humanizer", "redteam", "verify")


def receipt_path(digest: str, skill: str = "humanizer") -> str:
    # humanizer keeps the original filename so receipts recorded before this change still resolve.
    tail = ".json" if skill == "humanizer" else "." + skill + ".json"
    return os.path.join(DIR, digest[:32] + tail)


def missing(path: str) -> list:
    """Which of the three skills has no receipt for these exact bytes."""
    if not os.path.exists(path):
        return list(SKILLS)
    d = sha(path)
    return [s for s in SKILLS if not os.path.exists(receipt_path(d, s))]


def check(path: str, quiet: bool = False, skill: str = "humanizer") -> int:
    if not os.path.exists(path):
        if not quiet:
            print(f"  REFUSED: {path} is absent")
        return 1
    d = sha(path)
    p = receipt_path(d, skill)
    if not os.path.exists(p):
        if not quiet:
            print(f"  NO {skill.upper()} RECEIPT for {os.path.basename(path)}")
            print(f"    content sha256 {d[:32]}")
            print(f"    Run the {skill} SKILL on it (not a script I wrote, not the rules from "
                  f"memory), then:")
            print(f"    python tools/humanizer_receipt.py record {path} --skill {skill} "
                  f"--found \"...\"")
        return 1
    r = json.load(io.open(p, encoding="utf-8"))
    if not quiet:
        print(f"  {skill} receipt OK  {os.path.basename(path)}  "
              f"{r.get('before_words')} -> {r.get('after_words')} words, {r.get('iso')}")
        print(f"    found: {r.get('found')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["record", "check", "status"])
    ap.add_argument("draft")
    ap.add_argument("--skill", choices=list(SKILLS), default="humanizer")
    ap.add_argument("--found", default="")
    ap.add_argument("--before", type=int, default=0)
    ap.add_argument("--after", type=int, default=0)
    ap.add_argument("--evidence", default="",
                    help="path to an artifact the skill run produced (its output/transcript "
                         "file). Required for `record`: a receipt must point at something.")
    a = ap.parse_args()

    if a.action == "status":
        m = missing(a.draft)
        for s_ in SKILLS:
            print(f"  {'no ' if s_ in m else 'YES'}  {s_}")
        return 1 if m else 0
    if a.action == "check":
        return check(a.draft, skill=a.skill)

    if not os.path.exists(a.draft):
        raise SystemExit(f"REFUSED: {a.draft} is absent")
    # An empty --found is the whole failure mode in miniature: a pass recorded without a reading.
    if len(a.found.strip()) < 12:
        raise SystemExit("REFUSED: --found must say what the skill actually found. If it found "
                         "nothing, write that as a sentence; a blank is not a pass.")

    # AND A SENTENCE IS NOT A RUN. Measured 2026-08-27: I recorded all three receipts for a draft
    # after running ONE combined agent plus a script of my own, then reported "the gate is clean".
    # The owner caught it. `--found` was satisfied because I can always write a sentence, so the
    # only thing standing between an assertion and a receipt was my own honesty, which is exactly
    # the thing the receipt exists to replace.
    #
    # So a receipt must now POINT AT SOMETHING the run produced. This does not prove the right skill
    # ran; nothing local can. It does make a bare assertion impossible, and it leaves an audit trail
    # that a later reader can open and disagree with.
    ev = (a.evidence or "").strip()
    if not ev:
        raise SystemExit(
            "REFUSED: --evidence is required. Pass the path to the artifact the skill run produced "
            "(the agent's output file, the storm report, the verify transcript).\n"
            "  A receipt that points at nothing is the assertion it was built to replace.")
    if not os.path.exists(ev):
        raise SystemExit("REFUSED: --evidence %s does not exist." % ev)
    ev_bytes = os.path.getsize(ev)
    if ev_bytes < 500:
        raise SystemExit(
            "REFUSED: --evidence %s is %d bytes. A real skill run leaves more than that; if this "
            "is genuinely the whole output, say so in --found and point at the transcript instead."
            % (ev, ev_bytes))
    age_h = (time.time() - os.path.getmtime(ev)) / 3600.0
    if age_h > 12:
        raise SystemExit(
            "REFUSED: --evidence %s was last written %.1f hours ago. A receipt is bound to THIS "
            "draft's bytes; evidence from an older run is evidence about an older draft."
            % (ev, age_h))
    ev_sha = hashlib.sha256(io.open(ev, "rb").read()).hexdigest()
    os.makedirs(DIR, exist_ok=True)
    d = sha(a.draft)
    body = io.open(a.draft, encoding="utf-8").read()
    json.dump({"draft": os.path.relpath(a.draft, ROOT).replace(os.sep, "/"),
               "skill": a.skill,
               "content_sha256": d, "found": a.found.strip(),
               "evidence": {"path": ev.replace(os.sep, "/"), "bytes": ev_bytes,
                            "sha256": ev_sha, "age_hours_at_record": round(age_h, 2)},
               "before_words": a.before or len(body.split()),
               "after_words": a.after or len(body.split()),
               "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "note": f"records that the {a.skill} SKILL was run on these exact bytes; keyed by "
                       f"content, so any later edit invalidates it"},
              io.open(receipt_path(d, a.skill), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"  recorded {a.skill}  {os.path.basename(a.draft)}  sha {d[:32]}  "
          f"{a.before or len(body.split())} -> {a.after or len(body.split())} words  "
          f"evidence {os.path.basename(ev)} ({ev_bytes} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
