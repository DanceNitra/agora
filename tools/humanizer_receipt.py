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


def receipt_path(digest: str) -> str:
    return os.path.join(DIR, digest[:32] + ".json")


def check(path: str, quiet: bool = False) -> int:
    if not os.path.exists(path):
        if not quiet:
            print(f"  REFUSED: {path} is absent")
        return 1
    d = sha(path)
    p = receipt_path(d)
    if not os.path.exists(p):
        if not quiet:
            print(f"  NO HUMANIZER RECEIPT for {os.path.basename(path)}")
            print(f"    content sha256 {d[:32]}")
            print("    Run the humanizer SKILL on it (not the tells script, not the rules from "
                  "memory), then:")
            print(f"    python tools/humanizer_receipt.py record {path} --found \"...\" "
                  f"--before N --after M")
        return 1
    r = json.load(io.open(p, encoding="utf-8"))
    if not quiet:
        print(f"  humanizer receipt OK  {os.path.basename(path)}  "
              f"{r.get('before_words')} -> {r.get('after_words')} words, {r.get('iso')}")
        print(f"    found: {r.get('found')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["record", "check"])
    ap.add_argument("draft")
    ap.add_argument("--found", default="")
    ap.add_argument("--before", type=int, default=0)
    ap.add_argument("--after", type=int, default=0)
    a = ap.parse_args()

    if a.action == "check":
        return check(a.draft)

    if not os.path.exists(a.draft):
        raise SystemExit(f"REFUSED: {a.draft} is absent")
    # An empty --found is the whole failure mode in miniature: a pass recorded without a reading.
    if len(a.found.strip()) < 12:
        raise SystemExit("REFUSED: --found must say what the skill actually found. If it found "
                         "nothing, write that as a sentence; a blank is not a pass.")
    os.makedirs(DIR, exist_ok=True)
    d = sha(a.draft)
    body = io.open(a.draft, encoding="utf-8").read()
    json.dump({"draft": os.path.relpath(a.draft, ROOT).replace(os.sep, "/"),
               "content_sha256": d, "found": a.found.strip(),
               "before_words": a.before or len(body.split()),
               "after_words": a.after or len(body.split()),
               "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "note": "records that the humanizer SKILL was run on these exact bytes; keyed by "
                       "content, so any later edit invalidates it"},
              io.open(receipt_path(d), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  recorded  {os.path.basename(a.draft)}  sha {d[:32]}  "
          f"{a.before or len(body.split())} -> {a.after or len(body.split())} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
