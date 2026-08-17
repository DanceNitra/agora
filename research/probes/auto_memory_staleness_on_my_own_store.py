"""What does Claude Code's auto memory know about whether its own notes are still true?

Measured on a live auto-memory directory rather than argued from the docs. Per
https://code.claude.com/docs/en/memory a note carries at most a `modified` write timestamp -- and
only if the file already had YAML frontmatter, because "Claude Code never adds frontmatter to a file
that has none". Nothing records what a note was derived FROM, and nothing re-checks it.

That is a design choice, not a defect, and for "always use pnpm" it is the right one. The question
this asks is narrower and empirical: on a real store, how many notes make a claim that CAN go stale,
and how many already HAVE?

THE MEASURABLE PROXY, chosen because it needs no judgement: a note that names a repository path.
If the path no longer exists, the note is making a claim about a thing that is gone. That is not the
only way to go stale -- it is the way that can be checked mechanically, so it is a FLOOR.

Run:  python auto_memory_staleness_on_my_own_store.py [--dir <memory dir>]
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--dir", default=None, help="auto-memory directory (default: this project's)")
ap.add_argument("--repo", default=None, help="repo root the paths are relative to")
a = ap.parse_args()

MEM = Path(a.dir) if a.dir else Path(
    os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora/memory"))
REPO = Path(a.repo) if a.repo else Path(__file__).resolve().parents[2]

if not MEM.is_dir():
    raise SystemExit(f"no auto-memory directory at {MEM}")

notes = sorted(p for p in MEM.glob("*.md") if p.name != "MEMORY.md")
assert notes, "COVER: no notes found, so every count below would be a vacuous zero"

# A path-like token: at least one slash, a file extension, no spaces. Deliberately conservative --
# it will miss paths and that is the right direction for a floor.
PATH = re.compile(r"(?<![\w/.])((?:[\w.\-]+/)+[\w.\-]+\.[A-Za-z0-9]{1,5})(?![\w/])")
SKIP = ("http", "example.", "your-", "path/to")

with_fm = 0
with_modified = 0
claims: dict[Path, set] = {}

for n in notes:
    head = n.read_text(encoding="utf-8", errors="replace")[:400]
    if head.startswith("---"):
        with_fm += 1
        if re.search(r"^modified:", head, re.M):
            with_modified += 1
    body = n.read_text(encoding="utf-8", errors="replace")
    hits = {m for m in PATH.findall(body) if not any(s in m for s in SKIP)}
    if hits:
        claims[n] = hits

# Resolve each path against the repo AND against git history: a path that never existed is a
# false positive of the regex, while one that existed and is gone is the finding.
def known_to_git(rel: str) -> bool:
    r = subprocess.run(["git", "log", "--oneline", "-1", "--", rel],
                       capture_output=True, text=True, cwd=REPO)
    return bool(r.stdout.strip())


gone_notes, gone_paths, live_paths, never = 0, 0, 0, 0
examples = []
for n, hits in claims.items():
    dead_here = []
    for h in sorted(hits):
        if (REPO / h).exists():
            live_paths += 1
        elif known_to_git(h):
            gone_paths += 1
            dead_here.append(h)
        else:
            never += 1
    if dead_here:
        gone_notes += 1
        if len(examples) < 6:
            examples.append((n.name, dead_here[0]))

total_paths = live_paths + gone_paths + never
print("=" * 94)
print(f"CLAUDE CODE AUTO MEMORY -- one live store")
print(f"  directory : {MEM}")
print(f"  repo      : {REPO}")
print("=" * 94)
print(f"\n  notes (excluding the MEMORY.md index) : {len(notes)}")
print(f"  notes with YAML frontmatter           : {with_fm}")
print(f"  notes carrying a `modified` timestamp : {with_modified}")
print("      READ THAT WITH ITS CAUSE, which took a version check and a write-path check to find.")
print("      `modified` is added by CLAUDE CODE when IT writes a memory file (v2.1.214+). This store")
print("      is written by an agent calling the Write tool directly, so the field never gets added.")
print("      The zero is a fact about HOW THIS STORE IS WRITTEN, not a defect in the feature, and")
print("      reporting it as one would be an artefact of a setup dressed as a product gap.")
print(f"  notes with no timestamp at all        : {len(notes) - with_modified}"
      f"   ({100 * (len(notes) - with_modified) / len(notes):.0f}%)")

print(f"\n  notes naming at least one repo path   : {len(claims)}")
print(f"  distinct paths named                  : {total_paths}"
      f"  (live {live_paths} · gone {gone_paths} · never-in-git {never})")
print(f"  notes naming a path that EXISTED and is now GONE : {gone_notes}")
for name, p in examples:
    print(f"      {name[:58]:58s} -> {p}")

print(f"""
WHAT THIS DOES AND DOES NOT SHOW.

  It does NOT show that {gone_notes} notes are wrong. A note can name a deleted file and still be
  entirely correct about the lesson it records -- most of ours are exactly that.

  It shows that the format cannot TELL, and neither can the reader without doing what this script
  just did. A `modified` timestamp answers "when was this written"; it does not answer "is what it
  says still there". Those are different questions and only the first one is stored.

  The floor is conservative on both sides: the path regex is deliberately narrow, and a path is only
  counted as gone if git has seen it, so a typo is not a finding.
""")
print("=" * 94)
