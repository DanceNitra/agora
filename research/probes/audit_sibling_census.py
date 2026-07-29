"""Apply tonight's lesson to tonight's other claims: enumerate the siblings I did not measure.

Recorded an hour ago, after the third instance in a week: I fix the site I measured and write the commit
message as though I fixed the class. The check that would have caught all three is mechanical -- list
EVERY call site of the shape before claiming anything -- so this runs it against the claims I made
tonight, not only the one where the gate caught me.

Claims under test:
  C1  "every erasure path carries residue_in_store"     -- which paths emit a tombstone?
  C2  "remember_decision can attribute a decision"      -- who else calls remember_decision?
  C3  "route declares a parent at every write site"     -- how many self.remember() calls does it make?
  C4  "coverage ships on every erasure path"            -- fixed this morning; still true?

Read-only, on local HEAD. Structural -- it reports call sites, and each one still has to be READ before
it counts as a finding. The last time a scan of mine produced a plausible number by looking at the wrong
node, it claimed nine defects and one was real.
"""
import ast
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Danculus\inspeximus-repo"
CORE = os.path.join(ROOT, "inspeximus", "core.py")
src = open(CORE, encoding="utf-8", newline="").read()
tree = ast.parse(src)

FUNCS = {}
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        FUNCS.setdefault(node.name, []).append(node)


def calls_in(fn_name, attr):
    """Every `self.<attr>(...)` inside every def of this name, with the kwargs it passes."""
    out = []
    for node in FUNCS.get(fn_name, []):
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr == attr):
                out.append((sub.lineno, {k.arg for k in sub.keywords if k.arg}))
    return out


def callers_of(attr):
    """Which functions call `self.<attr>(...)` anywhere in core."""
    hits = {}
    for name, nodes in FUNCS.items():
        for node in nodes:
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == attr):
                    hits.setdefault(name, []).append(sub.lineno)
    return hits


print("=== C3: every self.remember() inside route(), and what it passes ===")
for lineno, kw in sorted(calls_in("route", "remember")):
    has = sorted(k for k in ("source", "derived_from") if k in kw)
    flag = "" if has else "   <-- NO PROVENANCE"
    print(f"   line {lineno}: {sorted(kw)}{flag}")
print("   -> five sites were the count when the echo branch was missed. Any line without provenance")
print("      here needs reading before it is called a defect: a site with no key has nothing to derive")
print("      from, and inferring a subject would be inventing one.\n")

print("=== C1/C4: who emits a tombstone, i.e. which functions are erasure paths? ===")
for name, lines in sorted(callers_of("_emit_tombstone").items()):
    print(f"   {name:24s} lines {lines}")
print("   -> anything here that does not funnel through forget() needs `coverage` and")
print("      `residue_in_store` carried by hand, which is how both were missed before.\n")

print("=== C1: which functions return a dict containing 'erased' or 'forgotten'? ===")
for name, nodes in sorted(FUNCS.items()):
    for node in nodes:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Dict):
                keys = {k.value for k in sub.value.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)}
                if keys & {"erased", "forgotten"}:
                    missing = sorted({"coverage", "residue_in_store"} - keys)
                    mark = f"   <-- missing {missing}" if missing else ""
                    print(f"   {name:24s} line {sub.lineno}{mark}")

print("\n=== C2: who calls remember_decision, and can they pass a source? ===")
for name, lines in sorted(callers_of("remember_decision").items()):
    print(f"   {name:24s} lines {lines}")
for surface, path in (("cli.py", "inspeximus/cli.py"), ("mcp_server.py", "inspeximus/mcp_server.py")):
    text = open(os.path.join(ROOT, path), encoding="utf-8", newline="").read()
    n = text.count("remember_decision")
    has_src = "source=" in text.split("remember_decision", 1)[-1][:400] if n else False
    print(f"   {surface:24s} mentions={n}  passes source nearby={has_src}")

print("\n-> Every line above is a POINTER, not a verdict. Read it before it counts.")
