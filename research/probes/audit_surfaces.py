"""AUDIT, aimed at the class the owner named: a function whose whole purpose is to REFUSE,
returning a clean verdict about input it never structurally examined.

Six were already found this way — verify_claim, verify_attribution, DeletionManifest.verify,
compliance_check, scan_residue, MCP verify_audit_bundle. His instruction for the seventh: look where
README.md and docs/AI_ACT.md point at the moat.

So this does not hunt code at random. It enumerates every VERIFICATION SURFACE those two documents
advertise, resolves each to its implementation, and reports what it actually reads. A surface that
returns a verdict without touching the artefact it judges is the next defect by construction.
"""
import ast
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Danculus\inspeximus-repo"

DOCS = ["README.md", os.path.join("docs", "AI_ACT.md")]
#: things that make a claim a GUARANTEE rather than a feature
VERBS = re.compile(r"\b(verif\w*|check\w*|prove\w*|proof|refus\w*|detect\w*|audit\w*|attest\w*|"
                   r"guarantee\w*|tamper|certif\w*)\b", re.I)
#: an identifier that looks like a callable surface
CALL = re.compile(r"`([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)\(?\)?`")

claimed = {}
for rel in DOCS:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    for i, line in enumerate(open(p, encoding="utf-8").read().splitlines(), 1):
        if not VERBS.search(line):
            continue
        for name in CALL.findall(line):
            base = name.split(".")[-1]
            if len(base) < 4 or base in ("true", "false", "none", "json", "dict", "list"):
                continue
            claimed.setdefault(base, []).append((rel, i))

print(f"verification surfaces advertised in README/AI_ACT: {len(claimed)}\n")

# resolve each to a def in the package
defs = {}
for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "inspeximus")):
    dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "build")]
    for f in filenames:
        if not f.endswith(".py"):
            continue
        fp = os.path.join(dirpath, f)
        try:
            tree = ast.parse(open(fp, encoding="utf-8").read())
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs.setdefault(node.name, []).append((os.path.relpath(fp, ROOT), node.lineno, node))

found, missing = [], []
for name, where in sorted(claimed.items()):
    if name in defs:
        found.append(name)
    else:
        missing.append((name, where[0]))

print(f"resolved to a function in the package: {len(found)}")
for n in found:
    locs = ", ".join(f"{f}:{ln}" for f, ln, _ in defs[n][:2])
    doc_at = ", ".join(f"{r}:{i}" for r, i in claimed[n][:2])
    print(f"   {n:34s} {locs:52s}  claimed at {doc_at}")

print(f"\nadvertised but NOT a function here ({len(missing)}) — prose, a CLI verb, or another package:")
for n, w in missing:
    print(f"   {n:34s} claimed at {w[0]}:{w[1]}")
