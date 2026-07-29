"""Which advertised guarantees does the surface-conformance suite actually cover?

The suite holds 13 tests and I chose them by reading the docs by hand. That is exactly how route() came
to have "five" write sites when it had nine. So: enumerate the claims mechanically, then READ each one --
the extraction proposes, it does not decide.

A claim counts as COVERED only if the suite exercises it through the MCP server or the CLI. "The library
can do it" is not the claim the documentation makes to a user, and it was the gap that let two erasure
defects ship.

Read-only. Prints a census; changes nothing.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = r"C:\Users\Danculus\inspeximus-repo"

DOCS = [("README.md", os.path.join(REPO, "README.md")),
        ("docs/AI_ACT.md", os.path.join(REPO, "docs", "AI_ACT.md"))]

#: A guarantee reads like a promise about behaviour, not like prose. These are the shapes the two
#: documents actually use for them.
PATTERNS = [
    (r"^\s*[-*]\s+\*\*(Art\.[^*]+|GDPR[^*]+)\*\*", "article bullet"),
    (r"^\s*[-*]\s+\*\*([A-Z][^*]{8,90})\.\*\*", "bolded promise"),
    (r"^\|\s*`([a-z_]+\([^`]*\))`\s*\|", "operations table row"),
]


def claims():
    seen = []
    for label, path in DOCS:
        if not os.path.exists(path):
            print(f"   MISSING: {path}")
            continue
        for i, line in enumerate(open(path, encoding="utf-8", errors="replace").read().splitlines(), 1):
            for pat, kind in PATTERNS:
                m = re.search(pat, line)
                if m:
                    seen.append((label, i, kind, m.group(1).strip()))
                    break
    return seen


def suite_text():
    p = os.path.join(REPO, "tests", "test_surface_conformance.py")
    return open(p, encoding="utf-8", errors="replace").read()


TESTS = suite_text()

#: Hand-mapped, because a keyword match would claim coverage it cannot verify. Each entry names the test
#: that exercises the guarantee THROUGH a surface, or states plainly that nothing does.
COVERED = {
    "Art. 12 & 19": "test_art12_write_receipts_verify_once_ENABLED + tampered_record_is_caught",
    "Art. 15": "test_art15_correction_sticks_through_MCP / _through_CLI + echo_cannot_resurrect",
    "GDPR Art. 17": "test_art17_erasure_through_MCP / _through_CLI + correction + ghost + certificate",
}

print("=== candidate guarantees extracted from the two documents ===\n")
rows = claims()
for label, ln, kind, text in rows:
    key = next((k for k in COVERED if text.startswith(k)), None)
    mark = "COVERED  " if key else "unmapped "
    print(f"   [{mark}] {label}:{ln:<4} ({kind}) {text[:82]}")

print(f"\n   {len(rows)} candidates, {sum(1 for r in rows if any(r[3].startswith(k) for k in COVERED))} "
      f"mapped to a surface test\n")

print("=== the operations the README promises, and whether the suite reaches them ===")
ops = [t for _, _, kind, t in rows if kind == "operations table row"]
for op in ops:
    name = op.split("(")[0]
    reached = f"mcp.{name}(" in TESTS or f'"{name}"' in TESTS or f"'{name}'" in TESTS
    print(f"   {name:22s} {'reached by the suite' if reached else 'NOT reached through any surface'}")

print("\n-> Every 'unmapped' line above is a POINTER, not a verdict. The last scan of mine that skipped")
print("   the reading step reported nine CLI defects and one was real.")
