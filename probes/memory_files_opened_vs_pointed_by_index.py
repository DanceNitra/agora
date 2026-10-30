"""Of the memory files the agent opened, how many does the live MEMORY.md point at?

Companion of memory_files_delivered_vs_opened_census.py. Reads the same transcripts and the live index.
A file counts as pointed at when its file name appears as a markdown link target in MEMORY.md.
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

idx = io.open(os.path.join(M, "MEMORY.md"), encoding="utf-8").read()
pointed = set(os.path.basename(x) for x in re.findall(r"\(([^)\s]+[.]md)\)", idx))
on_disk = set(f for f in os.listdir(M) if f.endswith(".md") and f not in ("MEMORY.md", "MEMORY_ARCHIVE.md"))
prefix = M.replace(BS, "/") + "/"
opened = set()
for f in glob.glob(os.path.join(P, "*.jsonl")):
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
                        opened.add(os.path.basename(p))
opened &= on_disk
res = {
    "memory_files_on_disk": len(on_disk),
    "files_pointed_at_by_the_live_index": len(pointed & on_disk),
    "files_not_pointed_at": len(on_disk - pointed),
    "opened_by_agent": len(opened),
    "opened_and_pointed_at": len(opened & pointed),
    "opened_and_not_pointed_at": len(opened - pointed),
}
io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
