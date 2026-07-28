"""Every MCP tool against the function it wraps: which parameters does the wrapper drop?

Today's two MCP defects were the same shape — the wrapper did not expose what the underlying function
needed to perform its own check:

    verify_audit_bundle  had no `store_items`   -> content was never compared, `ok` regardless
    compliance_check     dropped `prior_anchor` -> `not_append_only` could never fire

Both were found by hand. This finds the rest mechanically: for each `@mcp.tool()`, resolve the core
callable it delegates to, and diff the parameter lists. A parameter the core accepts and the tool never
offers is a capability the MCP surface silently cannot reach — sometimes deliberate, sometimes the
defect above. The report ranks by how correctness-relevant the missing name looks.
"""
import ast
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Danculus\inspeximus-repo"
MCP = os.path.join(ROOT, "inspeximus", "mcp_server.py")

#: names whose absence changes what a verdict MEANS, rather than merely what it covers
CRITICAL = re.compile(
    r"store_items|store_path|prior_anchor|expected_pubkey|witness|threshold|strict|"
    r"require|verify|exact|allow_ambiguous|authorization|authorized_by|basis|request_id|"
    r"trusted_only|include_superseded|reaffirm|dry_run", re.I)

tree = ast.parse(open(MCP, encoding="utf-8").read())
tools = []
for node in tree.body:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    if not any(isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "tool"
               for d in node.decorator_list):
        continue
    params = [a.arg for a in node.args.args if a.arg != "self"]
    # EVERY call in the body, not the first. The first Call is usually a helper or a str/dict build,
    # so "first non-builtin" resolved nothing at all and the audit reported a clean sheet over 56
    # tools — a scan that finds zero because it looked at the wrong node is the failure this whole
    # audit is about, produced by the audit itself.
    called = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if nm and nm not in ("dict", "list", "str", "int", "float", "len", "get", "json",
                                 "sorted", "sum", "min", "max", "bool", "range", "enumerate"):
                called.append(nm)
    tools.append((node.name, params, called))

# index every def in the package
defs = {}
for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "inspeximus")):
    dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "build")]
    for f in filenames:
        if not f.endswith(".py") or f == "mcp_server.py":
            continue
        try:
            t = ast.parse(open(os.path.join(dirpath, f), encoding="utf-8").read())
        except Exception:
            continue
        for n in ast.walk(t):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ps = [a.arg for a in n.args.args if a.arg != "self"]
                ps += [a.arg for a in n.args.kwonlyargs]
                defs.setdefault(n.name, (os.path.relpath(os.path.join(dirpath, f), ROOT), ps))

print(f"MCP tools found: {len(tools)}\n")
rows = []
unresolved = []
for name, params, called in tools:
    cands = [c for c in called if c in defs]
    if not cands:
        unresolved.append(name)
        continue
    # a tool usually delegates to the same-named core function; otherwise take the richest callee,
    # since a wrapper that drops parameters drops them from the widest signature it touches
    target = name if name in cands else max(cands, key=lambda c: len(defs[c][1]))
    src, core_params = defs[target]
    missing = [p for p in core_params if p not in params and not p.startswith("_")]
    crit = [p for p in missing if CRITICAL.search(p)]
    if missing:
        rows.append((len(crit), name, target, src, missing, crit))

rows.sort(key=lambda r: (-r[0], r[1]))
print(f"{'tool':26s} -> core fn                 missing parameters")
for ncrit, name, target, src, missing, crit in rows:
    mark = "!!" if ncrit else "  "
    print(f"{mark} {name:24s} -> {target:22s} {', '.join(missing)[:70]}")
    if crit:
        print(f"      CORRECTNESS-RELEVANT: {', '.join(crit)}   ({src})")

print(f"\ntools whose wrapper drops a correctness-relevant parameter: "
      f"{sum(1 for r in rows if r[0])}  (of {len(tools)} tools; {len(unresolved)} unresolved)")
if unresolved:
    print("UNRESOLVED (delegate not found - inspect by hand, do NOT read as clean):")
    print("   " + ", ".join(unresolved))
