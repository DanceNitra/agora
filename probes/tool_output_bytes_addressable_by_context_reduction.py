"""How many bytes of tool output entered our sessions, and how much of it a context-mode style layer could keep out?

context-mode (mksglu/context-mode, read 2026-10-19) shrinks context only for output that passes through its own MCP
tools: stdout over 5 KB with an intent is indexed and replaced by section titles, over 100 KB by a pointer. A hook
cannot shrink a native tool's result in Claude Code (hooks/posttooluse.mjs has no output-replacing field). So the
ceiling for inspeximus is: tool results over 5 KB, by tool, in our real transcripts.

Run: python -X utf8 probes/tool_output_bytes_addressable_by_context_reduction.py
Writes the .result.json beside it. No model call, no network.
"""
import collections
import glob
import json
import os
import sys
import time

ROOT = os.path.expanduser("~/.claude/projects")
OUT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
SMALL, LARGE = 5_000, 102_400


def text_len(content):
    if isinstance(content, str):
        return len(content.encode("utf-8"))
    n = 0
    for x in content or []:
        if isinstance(x, dict) and x.get("type") == "text":
            n += len((x.get("text") or "").encode("utf-8"))
    return n


def bucket(name):
    if not name:
        return "?"
    if name.startswith("mcp__"):
        return "mcp:" + name.split("__")[1][:24]
    return name


def main():
    t0 = time.time()
    files = sorted(glob.glob(os.path.join(ROOT, "*", "*.jsonl")))
    by_tool = collections.defaultdict(lambda: [0, 0, 0, 0])   # calls, bytes, bytes_over_5k, calls_over_5k
    total = over = over_large = 0
    for n, path in enumerate(files, 1):
        uses = {}
        try:
            fh = open(path, encoding="utf-8")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"tool_' not in line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                c = (r.get("message") or {}).get("content")
                if not isinstance(c, list):
                    continue
                for x in c:
                    if not isinstance(x, dict):
                        continue
                    if x.get("type") == "tool_use":
                        uses[x.get("id")] = x.get("name")
                    elif x.get("type") == "tool_result":
                        b = text_len(x.get("content"))
                        row = by_tool[bucket(uses.get(x.get("tool_use_id")))]
                        row[0] += 1
                        row[1] += b
                        total += b
                        if b > SMALL:
                            row[2] += b
                            row[3] += 1
                            over += b
                        if b > LARGE:
                            over_large += b
        if n % 100 == 0:
            print(f"[{n}/{len(files)}] {total / 1e6:.1f} MB, {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    rows = sorted(by_tool.items(), key=lambda kv: -kv[1][2])
    result = {
        "measured": time.strftime("%Y-%m-%d %H:%M"),
        "transcripts": len(files),
        "tool_result_bytes_total": total,
        "bytes_in_results_over_5KB": over,
        "share_over_5KB": round(over / total, 3) if total else None,
        "bytes_in_results_over_100KB": over_large,
        "by_tool_top": [{"tool": k, "calls": v[0], "bytes": v[1], "bytes_over_5KB": v[2], "calls_over_5KB": v[3]}
                        for k, v in rows[:20]],
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
