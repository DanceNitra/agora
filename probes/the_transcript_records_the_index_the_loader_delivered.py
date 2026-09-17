"""Does the session transcript record the auto-memory index as the loader delivered it?

CLAIM UNDER TEST (Linxiushen, anthropics/claude-code#82056, 2026-09-17): transcripts carry an
`attachment.type == "instructions"` record with `files[{path, type, content}]`, so whether MEMORY.md
loaded whole, truncated or not at all is decidable after the fact from the transcript alone.

WHAT THIS READS. Every `*.jsonl` in one project directory under `~/.claude/projects`. For each
transcript: the build (`version`) and EVERY `instructions` attachment, not the first one. The first
version of this probe read one record per session and reported "two sessions were cut"; the red
team found 11 records in one transcript with six distinct deliveries, because every compaction
re-reads the file and writes a new record tagged `changed: true, reason: "compaction"`, and every
resume writes an untagged record that repeats the previous delivery byte for byte. So the unit of
the record is a prompt build, not a session, and a per-session verdict has to be a per-record one.
For each record: the tags, the delivered MEMORY.md line count, its size in UTF-16 code units (the
unit the loader caps on, measured on this thread), whether the loader's own truncation warning line
is appended, and a content hash so repeats are visible.

WHAT IT CANNOT SHOW. That the model attended to the text. That a session on a build without the
attachment loaded anything at all; for those the verdict is `unknown`, which is the honest answer.
And whether an untagged resume record that repeats the session-start delivery after the file changed
on disk is a faithful record of a stale delivery or a replay of the earlier record: only a capture of
the request body can say, and none was run on these builds.

CONTROLS. (1) Every record with the attachment MUST name MEMORY.md, else the reader found the record
and not the file. (2) The delivered body of a truncated index MUST be at or under the 25,000-unit cap
with the warning line removed, else the cap this thread measured is wrong; the warning line is matched
as a line that starts with `> WARNING:`, so a memory entry quoting the phrase cannot be stripped.
(3) The warning line MUST appear only where the delivered body is at a cap; a warning on an under-cap
body means the reader matched something else. (4) Every record tagged `changed` MUST differ from the
record before it, and every untagged record after the first MUST repeat the one before it, else the
tags do not mean what this docstring says.

Receipt: <this file>.result.json beside it. Nothing here writes to the Claude home it reads.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys

CAP_LINES = 200
CAP_UNITS = 25000
WARN = "Only part of it was loaded"
PROJECT_DIR = os.path.join(os.path.expanduser("~"), ".claude", "projects", "C--Users-Danculus-agora")


def u16(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def _memory_record(att: dict) -> dict | None:
    for f in att.get("files", []) or []:
        if str(f.get("path", "")).endswith("MEMORY.md"):
            content = f.get("content") or ""
            lines = content.split("\n")
            warn_idx = [i for i, ln in enumerate(lines) if ln.startswith("> WARNING:") and WARN in ln]
            warned = bool(warn_idx)
            body_lines = [ln for i, ln in enumerate(lines) if i not in warn_idx]
            # The loader appends "\n\n> WARNING: ..." so a cut body ends in a blank element.
            while warned and body_lines and body_lines[-1] == "":
                body_lines.pop()
            body = "\n".join(body_lines)
            return {
                "lines_delivered": len(lines),
                "units_delivered": u16(content),
                "body_lines": len(body_lines),
                "body_units": u16(body),
                "warning_line_present": warned,
                "warning_text": lines[warn_idx[0]].strip()[:140] if warned else None,
                "sha1": hashlib.sha1(content.encode("utf-8")).hexdigest()[:10],
            }
    return None


def read_one(path: str) -> dict:
    row = {"transcript": os.path.basename(path)[:8], "version": None, "first_ts": None, "records": []}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if row["version"] is None and '"version"' in line:
                try:
                    row["version"] = json.loads(line).get("version")
                except Exception:  # noqa: BLE001
                    pass
            if row["first_ts"] is None and '"timestamp"' in line:
                try:
                    row["first_ts"] = json.loads(line).get("timestamp")
                except Exception:  # noqa: BLE001
                    pass
            if '"instructions"' not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            att = rec.get("attachment") or {}
            if att.get("type") != "instructions":
                continue
            row["records"].append({"ts": (rec.get("timestamp") or "")[:19], "changed": att.get("changed"),
                                   "reason": att.get("reason"), "memory_md": _memory_record(att)})
    return row


def main() -> int:
    paths = sorted(glob.glob(os.path.join(PROJECT_DIR, "*.jsonl")), key=os.path.getmtime)
    rows = [read_one(p) for p in paths]
    rows.sort(key=lambda r: (r["first_ts"] or "", r["transcript"]))
    with_att = [r for r in rows if r["records"]]
    without = [r for r in rows if not r["records"]]
    records = [(r, x) for r in with_att for x in r["records"]]
    mems = [x["memory_md"] for _, x in records]

    def vkey(v):
        return tuple(int(x) for x in re.findall(r"\d+", v or "0"))

    v = {}
    v["every_instructions_record_names_memory_md"] = bool(mems) and all(m is not None for m in mems)
    cut = [m for m in mems if m and m["warning_line_present"]]
    whole = [m for m in mems if m and not m["warning_line_present"]]
    v["warning_only_where_the_body_reaches_a_cap"] = all(
        m["body_lines"] >= CAP_LINES - 1 or m["body_units"] >= CAP_UNITS - 300 for m in cut) and all(
        m["lines_delivered"] <= CAP_LINES and m["units_delivered"] <= CAP_UNITS for m in whole)
    v["capped_body_never_exceeds_the_unit_cap"] = all(m["body_units"] <= CAP_UNITS for m in cut)
    tag_ok = True
    for r in with_att:
        prev = None
        for x in r["records"]:
            h = x["memory_md"]["sha1"] if x["memory_md"] else None
            if prev is not None:
                if x["changed"] and h == prev:
                    tag_ok = False
                if not x["changed"] and h != prev:
                    tag_ok = False
            prev = h
    v["changed_records_differ_and_untagged_records_repeat_the_previous_delivery"] = tag_ok
    newest_without = max((r["version"] for r in without), key=vkey, default=None)
    oldest_with = min((r["version"] for r in with_att), key=vkey, default=None)
    v["attachment_absent_before_and_present_from_a_single_build_edge"] = (
        newest_without is not None and oldest_with is not None and vkey(newest_without) < vkey(oldest_with))

    distinct = len({m["sha1"] for m in mems if m})
    print("transcripts: %d | with instructions records: %d | without: %d | records: %d | distinct deliveries: %d"
          % (len(rows), len(with_att), len(without), len(records), distinct))
    print("newest build WITHOUT: %s | oldest build WITH: %s" % (newest_without, oldest_with))
    for r in with_att:
        print("  %s %s" % (r["transcript"], r["version"]))
        for x in r["records"]:
            m = x["memory_md"] or {}
            tag = ("changed:" + str(x["reason"])) if x["changed"] else "untagged"
            print("     %s %-19s body_lines=%3s body_units=%5s warning=%-5s sha=%s" % (
                x["ts"], tag, m.get("body_lines"), m.get("body_units"), m.get("warning_line_present"), m.get("sha1")))
    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    out = {"probe": os.path.basename(__file__), "project_dir": os.path.basename(PROJECT_DIR),
           "cap_lines": CAP_LINES, "cap_units": CAP_UNITS, "transcripts": rows,
           "records": len(records), "distinct_deliveries": distinct,
           "newest_build_without_attachment": newest_without, "oldest_build_with_attachment": oldest_with,
           "verdicts": v}
    with open(os.path.splitext(os.path.abspath(__file__))[0] + ".result.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
