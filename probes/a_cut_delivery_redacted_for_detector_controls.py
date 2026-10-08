"""A real truncated MEMORY.md delivery, redacted, for anyone who needs a detector to go red once.

WHY. On anthropics/claude-code#82056 a truncation detector reported 0 files in 0 sessions after a fix,
and @tonydzi pointed out that a check which has never been red is an untested instrument: the zero
holds only if the detector is shown red on a broken input first. He suggested synthesising one.
This machine has real ones, so this file takes one of those instead of inventing it.

WHAT IT DOES. Reads every transcript in one Claude Code project directory, finds the first
`instructions` attachment whose MEMORY.md content ends in the loader's own `> WARNING:` line, and
writes it as a fixture with the text redacted: every character becomes `x` repeated by its UTF-16
width, newlines stay, and the warning line stays except for the index line it quotes, which is
private text and is redacted the same way. The record keeps its shape.

WHAT IT GUARANTEES, checked before the fixture is written:
  * the redacted content has the same UTF-16 unit count and the same line count as the original,
  * the warning line survives and is the last non-empty line, with only the index line it quotes
    redacted (that quote is text from the private index),
  * no original character other than newlines and the warning line is left in the content.

    python -X utf8 probes/a_cut_delivery_redacted_for_detector_controls.py [project_dir]
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

DEFAULT = os.path.join(os.path.expanduser("~"), ".claude", "projects", "C--Users-Danculus-agora")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "cut_delivery_redacted.json")
WARNING = "> WARNING:"


def units(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


QUOTE = re.compile(r'\("([^"]*)"\)')


def xs(text: str) -> str:
    return "".join("x" * units(ch) for ch in text)


def redact_warning(line: str) -> str:
    """The loader's warning quotes the first cut index line; that quote is private text."""
    return QUOTE.sub(lambda m: '("' + xs(m.group(1)) + '")', line)


def redact(content: str) -> str:
    out = []
    for line in content.split("\n"):
        out.append(redact_warning(line) if line.startswith(WARNING) else xs(line))
    return "\n".join(out)


def first_cut(project_dir: str):
    for path in sorted(glob.glob(os.path.join(project_dir, "*.jsonl"))):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                att = rec.get("attachment") or {}
                if rec.get("type") != "attachment" or att.get("type") != "instructions":
                    continue
                for f in att.get("files") or []:
                    body = str(f.get("content", ""))
                    if str(f.get("path", "")).endswith("MEMORY.md") and WARNING in body:
                        return rec, f, body
    return None


def main() -> int:
    found = first_cut(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
    if not found:
        print("no truncated delivery found: nothing to write")
        return 1
    rec, f, body = found
    red = redact(body)
    warn = [ln for ln in body.split("\n") if ln.startswith(WARNING)]
    checks = {
        "same_utf16_units": units(red) == units(body),
        "same_line_count": red.count("\n") == body.count("\n"),
        "warning_line_kept_and_last": bool(warn) and
            [ln for ln in red.split("\n") if ln.strip()][-1] == redact_warning(warn[-1]),
        "quoted_index_line_redacted": bool(QUOTE.findall(red)) and all(set(q) <= {"x"} for q in QUOTE.findall(red)),
        "no_original_text_left": set("".join(ln for ln in red.split("\n") if not ln.startswith(WARNING))) <= {"x"},
    }
    for k, v in checks.items():
        print("%-34s %s" % (k, "YES" if v else "no"))
    if not all(checks.values()):
        print("REFUSED: fixture not written")
        return 1
    fixture = {
        "type": "attachment",
        "version": rec.get("version"),
        "timestamp": rec.get("timestamp"),
        "attachment": {k: v for k, v in (rec.get("attachment") or {}).items() if k != "files"} | {
            "files": [{"path": "~/.claude/projects/<project>/memory/MEMORY.md", "type": f.get("type"),
                       "content": red}]},
        "_note": "real delivery, text redacted to x per UTF-16 unit; the loader's warning line is kept, "
                 "except the index line it quotes",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fixture, fh, ensure_ascii=False, indent=1)
    print("build %s  lines %d  utf16_units %d" % (rec.get("version"), body.count("\n"), units(body)))
    print("wrote", os.path.relpath(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
