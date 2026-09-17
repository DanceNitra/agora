"""Does the session transcript record the auto-memory index as the loader delivered it?

CLAIM UNDER TEST (Linxiushen, anthropics/claude-code#82056, 2026-09-17): transcripts carry an
`attachment.type == "instructions"` record with `files[{path, type, content}]`, so whether MEMORY.md
loaded whole, truncated or not at all is decidable after the fact from the transcript alone.

WHAT THIS READS. Every `*.jsonl` in one project directory under `~/.claude/projects`. For each
transcript: the build (`version`), whether an `instructions` attachment exists, and, when it names
MEMORY.md, the delivered content's line count, its size in UTF-16 code units (the unit the loader
caps on, measured on this thread) and whether the loader's own truncation warning line is appended.

WHAT IT CANNOT SHOW. That the model attended to the text. That a session on a build without the
attachment loaded anything at all; for those the verdict is `unknown`, which is the honest answer.

CONTROLS. (1) A transcript with the attachment MUST name MEMORY.md, else the reader found the record
and not the file. (2) The delivered size of a truncated index MUST be at or under the 25,000-unit cap
after the warning line is removed, else the cap this thread measured is wrong. (3) The warning line
MUST appear only where the delivered content is at the cap; a warning on an under-cap index means the
reader matched something else.

Receipt: <this file>.result.json beside it. Nothing here writes to the Claude home it reads.
"""
from __future__ import annotations

import glob
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


def read_one(path: str) -> dict:
    row = {"transcript": os.path.basename(path)[:8], "version": None, "first_ts": None,
           "instructions": 0, "memory_md": None}
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
            row["instructions"] += 1
            if row["memory_md"] is not None:
                continue
            for f in att.get("files", []) or []:
                if str(f.get("path", "")).endswith("MEMORY.md"):
                    content = f.get("content") or ""
                    lines = content.split("\n")
                    warned = any(WARN in ln for ln in lines)
                    body = "\n".join(ln for ln in lines if WARN not in ln) if warned else content
                    row["memory_md"] = {
                        "lines_delivered": len(lines),
                        "units_delivered": u16(content),
                        "units_without_warning": u16(body),
                        "lines_without_warning": len(body.split("\n")),
                        "warning_line_present": warned,
                        "warning_text": next((ln.strip()[:140] for ln in lines if WARN in ln), None),
                    }
                    break
    return row


def main() -> int:
    paths = sorted(glob.glob(os.path.join(PROJECT_DIR, "*.jsonl")), key=os.path.getmtime)
    rows = [read_one(p) for p in paths]
    rows.sort(key=lambda r: (r["first_ts"] or "", r["transcript"]))
    with_att = [r for r in rows if r["instructions"]]
    without = [r for r in rows if not r["instructions"]]

    def vkey(v):
        return tuple(int(x) for x in re.findall(r"\d+", v or "0"))

    v = {}
    # Control 1: every transcript with the attachment names MEMORY.md.
    v["every_instructions_attachment_names_memory_md"] = all(r["memory_md"] for r in with_att) and bool(with_att)
    # Control 2 and 3: the warning appears only at the cap, and the capped body sits under the cap.
    truncated = [r for r in with_att if r["memory_md"]["warning_line_present"]]
    whole = [r for r in with_att if not r["memory_md"]["warning_line_present"]]
    v["warning_only_where_the_body_reaches_a_cap"] = all(
        r["memory_md"]["lines_without_warning"] >= CAP_LINES or r["memory_md"]["units_without_warning"] >= CAP_UNITS - 300
        for r in truncated) and all(
        r["memory_md"]["lines_delivered"] < CAP_LINES + 1 and r["memory_md"]["units_delivered"] <= CAP_UNITS
        for r in whole)
    v["capped_body_never_exceeds_the_unit_cap"] = all(
        r["memory_md"]["units_without_warning"] <= CAP_UNITS for r in truncated)
    # The version edge: the newest build without the attachment and the oldest with it.
    newest_without = max((r["version"] for r in without), key=vkey, default=None)
    oldest_with = min((r["version"] for r in with_att), key=vkey, default=None)
    v["attachment_absent_before_and_present_from_a_single_build_edge"] = (
        newest_without is not None and oldest_with is not None and vkey(newest_without) < vkey(oldest_with))

    print("transcripts: %d | with instructions attachment: %d | without: %d" % (len(rows), len(with_att), len(without)))
    print("newest build WITHOUT: %s | oldest build WITH: %s" % (newest_without, oldest_with))
    for r in with_att:
        m = r["memory_md"] or {}
        print("  %s %s lines=%s units=%s warning=%s" % (r["transcript"], r["version"], m.get("lines_delivered"),
                                                        m.get("units_delivered"), m.get("warning_line_present")))
    print()
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    out = {"probe": os.path.basename(__file__), "project_dir": os.path.basename(PROJECT_DIR),
           "cap_lines": CAP_LINES, "cap_units": CAP_UNITS, "transcripts": rows,
           "newest_build_without_attachment": newest_without, "oldest_build_with_attachment": oldest_with,
           "verdicts": v}
    with open(os.path.splitext(os.path.abspath(__file__))[0] + ".result.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
