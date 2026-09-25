"""The author receipt: the model that wrote an outbound text is responsible for its content.

Owner decision, 2026-09-25. It replaces the three skill receipts (verify, redteam, humanizer)
that a separate `claude -p` gate call used to record. That call cost 0.39 USD for a five-sentence
reply that had nothing to check, so the owner removed the paid gate: "za content bude zodpovedat
OPUS 5.5". He removed the humanizer from the pipeline the same day.

What stays deterministic and free: `outbound.py check` (dashes, signature, ASCII, disclosure),
the seal's recompute of every figure from its source files, and the owner's "posli <hash>" on the
render. The author receipt binds the draft's sha256 to the model that answers for it, so an edit
after recording invalidates it the way the skill receipts did.

    python tools/author_receipt.py record DRAFT [--author MODEL]
    python tools/author_receipt.py check  DRAFT
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import sys

AUTHOR = "claude-opus-5-5"


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _path(draft):
    return os.path.join(os.path.dirname(os.path.abspath(draft)), "author.json")


def record(draft, author=AUTHOR):
    rec = {"draft": os.path.basename(draft), "draft_sha256": _sha(draft), "author": author,
           "responsible_for": "every fact, figure and word in this draft",
           "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    with io.open(_path(draft), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    return rec


def check(draft):
    """None when a receipt binds these exact bytes, else the reason it does not."""
    p = _path(draft)
    if not os.path.isfile(p):
        return "no author receipt beside %s; run: python tools/outbound.py gate SLUG" % draft
    rec = json.load(io.open(p, encoding="utf-8"))
    if rec.get("draft_sha256") != _sha(draft):
        return ("the draft changed after the author receipt was recorded (receipt %s, draft %s); "
                "re-run the gate" % (rec.get("draft_sha256", "")[:12], _sha(draft)[:12]))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["record", "check"])
    ap.add_argument("draft")
    ap.add_argument("--author", default=AUTHOR)
    a = ap.parse_args()
    if a.action == "record":
        rec = record(a.draft, a.author)
        print("author receipt: %s answers for %s (sha %s)" % (rec["author"], a.draft, rec["draft_sha256"][:16]))
        return 0
    why = check(a.draft)
    print("OK" if not why else "MISSING: " + why)
    return 1 if why else 0


if __name__ == "__main__":
    sys.exit(main())
