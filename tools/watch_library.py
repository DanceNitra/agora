"""Keep what a watched video taught us, and delete what it cost on disk.

The /watch skill leaves a work directory per video under %TEMP%\\watch-*: the downloaded video
(tens of MB), every extracted frame, and a rolling-caption transcript that repeats each line
twice. The owner's rule (2026-09-17): after a study run, the temp is deleted and the transcript
is kept deduplicated and compressed, small enough to grep and to hand to a later session.

    python tools/watch_library.py ingest <transcript.txt or watch report> [--id ID] [--note "..."]
    python tools/watch_library.py ingest-dir <dir with *.txt reports>
    python tools/watch_library.py clean          # delete %TEMP%\\watch-* directories
    python tools/watch_library.py list

Library: agora_output/study/videos.jsonl.gz (one JSON object per video: id, title, url, duration,
words, text) and agora_output/study/videos.md (id, title, note) for humans.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "agora_output", "study")
JSONL = os.path.join(LIB, "videos.jsonl.gz")
INDEX = os.path.join(LIB, "videos.md")


def dedupe(raw: str) -> tuple[str, int]:
    """Collapse the rolling captions: each cue repeats the tail of the previous one."""
    seg = re.findall(r"^\[(\d\d:\d\d(?::\d\d)?)\] (.*)$", raw, re.M)
    out: list[str] = []
    for _, line in seg:
        line = line.strip()
        if not line:
            continue
        if out and line.startswith(out[-1][-40:]):
            continue
        # drop the repeated head: captions print "A B | B C", keep the new half
        if out:
            prev = out[-1]
            for k in range(min(len(prev), len(line)), 10, -1):
                if line.startswith(prev[-k:]):
                    line = line[k:].strip()
                    break
        if line:
            out.append(line)
    text = " ".join(out)
    text = re.sub(r"\s+", " ", text)
    return text, len(seg)


def meta(raw: str) -> dict:
    m = {}
    for key, pat in (("title", r"\*\*Title:\*\* (.*)"), ("url", r"\*\*Source:\*\* (.*)"),
                     ("duration", r"\*\*Duration:\*\* (\S+)"), ("uploader", r"\*\*Uploader:\*\* (.*)")):
        f = re.search(pat, raw)
        if f:
            m[key] = f.group(1).strip()
    return m


def load() -> list[dict]:
    if not os.path.exists(JSONL):
        return []
    with gzip.open(JSONL, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def save(rows: list[dict]) -> None:
    os.makedirs(LIB, exist_ok=True)
    with gzip.open(JSONL, "wt", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(INDEX, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Watched videos\n\nDeduplicated transcripts live in `videos.jsonl.gz` beside this file.\n\n")
        fh.write("| id | title | duration | words | note |\n|---|---|---:|---:|---|\n")
        for r in rows:
            fh.write("| %s | %s | %s | %d | %s |\n" % (r["id"], r.get("title", ""), r.get("duration", ""),
                                                      r["words"], r.get("note", "")))


def ingest(path: str, vid: str | None, note: str) -> dict:
    raw = open(path, encoding="utf-8", errors="replace").read()
    text, cues = dedupe(raw)
    m = meta(raw)
    vid = vid or (re.search(r"[?&]v=([\w-]{11})", m.get("url", "")) or [None, os.path.splitext(os.path.basename(path))[0]])[1]
    row = {"id": vid, **m, "cues": cues, "words": len(text.split()), "note": note, "text": text}
    rows = [r for r in load() if r["id"] != vid] + [row]
    save(rows)
    return row


def clean() -> int:
    n = 0
    for d in glob.glob(os.path.join(tempfile.gettempdir(), "watch-*")):
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ingest"); a.add_argument("path"); a.add_argument("--id"); a.add_argument("--note", default="")
    b = sub.add_parser("ingest-dir"); b.add_argument("dir")
    sub.add_parser("clean"); sub.add_parser("list")
    args = ap.parse_args()
    if args.cmd == "ingest":
        r = ingest(args.path, args.id, args.note)
        print("ingested %s: %d cues -> %d words" % (r["id"], r["cues"], r["words"]))
    elif args.cmd == "ingest-dir":
        for p in sorted(glob.glob(os.path.join(args.dir, "*.txt"))):
            r = ingest(p, None, "")
            print("ingested %s: %d cues -> %d words" % (r["id"], r["cues"], r["words"]))
    elif args.cmd == "clean":
        print("removed %d watch-* directories" % clean())
    elif args.cmd == "list":
        for r in load():
            print("%s  %-70s %6d words  %s" % (r["id"], r.get("title", "")[:70], r["words"], r.get("note", "")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
