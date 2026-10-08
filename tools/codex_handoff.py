# -*- coding: utf-8 -*-
"""codex_handoff.py - build a handoff note from a Codex thread file, without any model call.

Reads ~/.codex/sessions/.../rollout-*.jsonl (the thread on disk) and writes a Markdown digest:
every message Danchi wrote (dated), the last assistant answers in full, the files the thread
touched, and the goals it tracked. Used when a provider runs out mid-thread, so no context is lost.

    python tools/codex_handoff.py <rollout.jsonl> --title "SHORT CREATOR" --out "<dir>"
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path


def text_of(content):
    if isinstance(content, str):
        return content
    out = []
    for c in content or []:
        if isinstance(c, dict):
            out.append(c.get("text") or c.get("input_text") or c.get("output_text") or "")
    return "\n".join(x for x in out if x)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("rollout")
    ap.add_argument("--title", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--last-answers", type=int, default=25)
    a = ap.parse_args()

    owner, answers, files, commands = [], [], collections.Counter(), collections.Counter()
    first = last = None
    turns = 0
    for line in open(a.rollout, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        ts = d.get("timestamp")
        first = first or ts
        last = ts or last
        p = d.get("payload") or {}
        if d.get("type") == "turn_context":
            turns += 1
        if d.get("type") == "response_item" and p.get("type") == "message":
            t = text_of(p.get("content")).strip()
            if not t:
                continue
            if p.get("role") == "user":
                if t.startswith(("<environment_context", "<user_instructions", "# AGENTS.md", "<permissions", "<turn_aborted")):
                    continue
                owner.append((ts, t))
            elif p.get("role") == "assistant":
                answers.append((ts, t))
        if d.get("type") == "response_item" and p.get("type") == "function_call":
            args = p.get("arguments") or ""
            for m in re.findall(r"\*\*\* (?:Add|Update|Delete) File: ([^\n\"\\]+)", args):
                files[m.strip()] += 1
            for m in re.findall(r"(C:[\\/]{1,2}Users[\\/]{1,2}Danculus[\\/]{1,2}[^\s\"'`<>|]+\.(?:md|py|json|jsonl|toml|yaml|txt|ps1|html))", args):
                files[m.replace("\\\\", "\\")] += 1
            cmd = re.search(r'"command"\s*:\s*\[?"([^"]{0,80})', args)
            if cmd:
                commands[cmd.group(1).split()[0] if cmd.group(1).split() else ""] += 1

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    day = (last or "")[:10]
    path = out_dir / f"HANDOFF {a.title} {day}.md"
    L = ["---", f'title: "HANDOFF {a.title} {day}"', "status: handoff", "domain: CrewOS",
         "tags: [crew-os, handoff, codex]", f"created: {day}", f"sources: [{Path(a.rollout).name}]", "---", "",
         f"# HANDOFF: {a.title}", "",
         f"- Thread file: `{a.rollout}`",
         f"- Span: {first} to {last}, {turns} turns, {len(owner)} messages from Danchi",
         "- Written by tools/codex_handoff.py from the file on disk, with no model call.", "",
         "## Where the thread stopped (last assistant answers, newest last)", ""]
    for ts, t in answers[-a.last_answers:]:
        L += [f"### {ts}", "", t.strip()[:4000], ""]
    L += ["## Every message from Danchi (oldest first)", ""]
    for ts, t in owner:
        short = t if len(t) <= 1500 else t[:1500] + f"\n\n[... {len(t) - 1500} more characters]"
        L += [f"**{ts}**", "", short, ""]
    L += ["## Files the thread touched (most often first)", ""]
    for f, n in files.most_common(150):
        L.append(f"- `{f}` ({n}x)")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{path}\nturns {turns}, owner messages {len(owner)}, assistant answers {len(answers)}, files {len(files)}, "
          f"{path.stat().st_size // 1024} kB")


if __name__ == "__main__":
    main()
