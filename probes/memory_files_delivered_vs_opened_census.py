"""Census of memory files: delivered into the window on their own, or opened by the agent.

WHY. @JhouCode asked @DanceNitra on anthropics/claude-code#82056 (comment 5910419239) for our numbers
on the delivery of individual memory files. His own count over 190 sessions: 0 injected on their own.

WHAT IT READS. Only the transcripts of ONE project folder (the main checkout) under ~/.claude/projects,
and the memory directory of that project. Nothing is written except the result file beside this script.

THREE COUNTS.
  delivered_on_their_own : memory files (not the index) named in an `instructions` attachment record.
  opened_by_agent        : memory files named in a Read, Edit or Write tool call of the agent.
  index_deliveries       : `instructions` records that name MEMORY.md. This is the POSITIVE CONTROL: it is
                           known to be non-zero (the index arrives at every session start), so a zero for
                           the other file is a measurement only if this one is above zero.

WHAT IT DOES NOT SHOW. It reads the transcript record, not the model's context, so it measures what the
channel recorded, not what the model saw. One operator, one installation.
"""
import glob
import io
import json
import os
import re
import sys

HOME = os.path.expanduser("~")
PROJECT = os.path.join(HOME, ".claude", "projects", os.environ.get("CLAUDE_PROJECT_DIR_NAME") or re.sub("[^A-Za-z0-9]", "-", os.getcwd()))
MEMDIR = os.path.join(PROJECT, "memory")
OUT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
INDEX_NAMES = {"MEMORY.md", "MEMORY_ARCHIVE.md"}


def norm(p):
    return os.path.normcase(os.path.normpath(p)) if p else ""


def in_memdir(p):
    return norm(p).startswith(norm(MEMDIR) + os.sep)


def main():
    on_disk = sorted(f for f in os.listdir(MEMDIR) if f.endswith(".md") and f not in INDEX_NAMES)
    files = sorted(glob.glob(os.path.join(PROJECT, "*.jsonl")))
    delivered, opened = set(), set()
    index_deliveries = 0
    instr_records = 0
    types_seen = {}
    sessions_with_index = 0
    first_ts, last_ts = None, None
    for f in files:
        had_index = False
        for line in io.open(f, encoding="utf-8", errors="replace"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            ts = r.get("timestamp")
            if ts:
                first_ts = ts if first_ts is None or ts < first_ts else first_ts
                last_ts = ts if last_ts is None or ts > last_ts else last_ts
            a = r.get("attachment")
            if isinstance(a, dict) and a.get("type") == "instructions":
                instr_records += 1
                for fi in a.get("files") or []:
                    p = fi.get("path") or ""
                    t = fi.get("type")
                    types_seen[t] = types_seen.get(t, 0) + 1
                    if os.path.basename(p) == "MEMORY.md" and in_memdir(p):
                        index_deliveries += 1
                        had_index = True
                    elif in_memdir(p) and os.path.basename(p) not in INDEX_NAMES:
                        delivered.add(os.path.basename(p))
            m = r.get("message")
            if r.get("type") == "assistant" and isinstance(m, dict) and isinstance(m.get("content"), list):
                for b in m["content"]:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        inp = b.get("input") or {}
                        p = inp.get("file_path") or ""
                        if p and in_memdir(p) and os.path.basename(p) not in INDEX_NAMES:
                            opened.add(os.path.basename(p))
        if had_index:
            sessions_with_index += 1
    res = {
        "transcripts_read": len(files),
        "first_record": first_ts,
        "last_record": last_ts,
        "memory_files_on_disk": len(on_disk),
        "instructions_records": instr_records,
        "attachment_file_types_seen": types_seen,
        "index_deliveries_POSITIVE_CONTROL": index_deliveries,
        "transcripts_with_an_index_delivery": sessions_with_index,
        "delivered_on_their_own": len(delivered & set(on_disk)),
        "opened_by_agent": len(opened & set(on_disk)),
        "opened_share": round(len(opened & set(on_disk)) / max(1, len(on_disk)), 3),
        "control_passed": index_deliveries > 0,
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res, indent=1, ensure_ascii=False))
    if not res["control_passed"]:
        print("CONTROL FAILED: the index was never seen being delivered, so the zero below is void.")
        sys.exit(2)


if __name__ == "__main__":
    main()
