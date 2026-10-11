"""Memory files that reach the window in a `file`, `edited_text_file` or `compact_file_reference` record.

Companion of memory_files_delivered_vs_opened_census.py. For each such record that names a memory file
(not the index), it asks whether the agent had already touched that file earlier in the same transcript
through a Read, Edit or Write call. A record with no earlier touch would be a delivery that was not recall.
"""
import glob
import io
import json
import os
import re

BS = chr(92)
P = os.path.join(os.path.expanduser("~"), ".claude", "projects", os.environ.get("CLAUDE_PROJECT_DIR_NAME") or re.sub("[^A-Za-z0-9]", "-", os.getcwd()))
M = os.path.join(P, "memory")
OUT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
prefix = M.replace(BS, "/") + "/"
KINDS = ("file", "edited_text_file", "compact_file_reference")
total = 0
touched_before = 0
not_touched = []
kinds = {}
for f in sorted(glob.glob(os.path.join(P, "*.jsonl"))):
    seen = set()
    for line in io.open(f, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        m = r.get("message")
        if r.get("type") == "assistant" and isinstance(m, dict) and isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    p = ((b.get("input") or {}).get("file_path") or "").replace(BS, "/")
                    if p.startswith(prefix):
                        seen.add(os.path.basename(p))
        a = r.get("attachment")
        if isinstance(a, dict) and a.get("type") in KINDS:
            p = (a.get("filename") or "").replace(BS, "/")
            if p.startswith(prefix) and os.path.basename(p) not in ("MEMORY.md", "MEMORY_ARCHIVE.md"):
                total += 1
                kinds[a["type"]] = kinds.get(a["type"], 0) + 1
                if os.path.basename(p) in seen:
                    touched_before += 1
                else:
                    not_touched.append([os.path.basename(f)[:8], a["type"], os.path.basename(p)])
res = {"records_naming_a_memory_file": total, "by_record_type": kinds,
       "agent_had_touched_the_file_earlier": touched_before, "not_touched_earlier": len(not_touched),
       "not_touched_examples": not_touched[:5]}
io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
