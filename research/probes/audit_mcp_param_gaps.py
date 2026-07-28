"""Which arguments can the core take that the MCP layer cannot pass -- and does the guarantee still report?

The class this month keeps producing is a surface that returns a clean verdict about input it never
examined. A structural way to hunt it: for every MCP tool that wraps a core method, list the core
parameters the tool has no way to supply. A missing parameter is not automatically a defect -- most are
sensible defaults -- but it IS a defect whenever the parameter is what makes a guarantee checkable, because
then the guarantee runs on nothing and still returns.

The sharp instance to look for here: `forget_subject(values=...)`. `values` is the list of sensitive
strings each erasure target checks for residue in `still_recoverable(subject, values)`. With no values, the
honest self-check has nothing to look for, `verified_absent` comes back True, and `coverage.confirmed`
counts a confirmation of a check that examined an empty list. That is not a hypothetical shape -- it is
the exact shape of the six findings the owner told me to keep hunting.

Read-only. Reports; fixes nothing.
"""
import ast
import inspect
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = r"C:\Users\Danculus\inspeximus-repo"
sys.path.insert(0, REPO)
from inspeximus import Inspeximus  # noqa: E402

MCP = os.path.join(REPO, "inspeximus", "mcp_server.py")
src = open(MCP, encoding="utf-8").read()
tree = ast.parse(src)

# Which core method does each MCP tool call, and with which keywords?
tools = {}
for node in ast.walk(tree):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    calls = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            calls.append((sub.func.attr, {k.arg for k in sub.keywords if k.arg}))
    if calls:
        tools[node.name] = {"params": list(inspect.signature(
            type("x", (), {node.name: lambda: None})).parameters) if False else
            [a.arg for a in node.args.args + node.args.kwonlyargs], "calls": calls}

print(f"scanned {len(tools)} MCP functions that call a method\n")

INTERESTING = {"forget_subject", "forget", "forget_pii", "erasure_audit", "slash",
               "spend_irreversible", "revert", "remember", "consolidate"}

rows = []
for fname, info in sorted(tools.items()):
    for core_name, passed in info["calls"]:
        if core_name not in INTERESTING:
            continue
        core_fn = getattr(Inspeximus, core_name, None)
        if core_fn is None:
            continue
        core_params = [p for p in inspect.signature(core_fn).parameters if p != "self"]
        # A parameter is UNREACHABLE if the tool neither passes it nor exposes it as its own argument.
        unreachable = [p for p in core_params if p not in passed and p not in info["params"]]
        if unreachable:
            rows.append((fname, core_name, unreachable))

for fname, core_name, missing in rows:
    print(f"  {fname} -> Inspeximus.{core_name}")
    print(f"     unreachable from MCP: {missing}")

print("\n=== the one that makes a guarantee run on nothing ===")
for fname, core_name, missing in rows:
    if core_name in ("forget_subject", "forget", "forget_pii") and "values" in missing:
        print(f"  {fname}: cannot pass `values`, so every registered erasure target runs")
        print("     still_recoverable(subject, []) -- a residue check over an empty list, which cannot")
        print("     fail, and whose success is then counted in coverage.confirmed.")
        break
else:
    print("  no erasure tool is missing `values` -- that specific hole is not present.")

print("\n=== CONTROL: measure it rather than infer it ===")
import tempfile  # noqa: E402


class Target:
    name = "vector-index"

    def __init__(self):
        self.seen = None

    def erase(self, subject):
        return {"erased": 1}

    def still_recoverable(self, subject, values):
        self.seen = list(values or [])
        return bool(self.seen)          # honest: with nothing to look for, it cannot find anything


for label, vals in (("values passed", ["92000"]), ("values OMITTED", None)):
    st = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), receipts=True)
    t = Target()
    st.register_erasure_target(t)
    st.remember("alice salary 92000", key="p", object="92000", source={"doc": "hr/alice"})
    kw = {"values": vals} if vals is not None else {}
    cov = st.forget_subject("hr/alice", request_id="r", basis="art17", **kw)["coverage"]
    print(f"  {label:16s} target was asked to look for {t.seen!r}")
    print(f"                   -> confirmed={cov['confirmed']} complete={cov['complete']}")
print("  -> if the OMITTED arm reports the same confirmed/complete as the passed arm, then a caller who")
print("     cannot supply `values` gets a clean cross-store erasure verdict from a check that looked")
print("     for nothing. Same shape as the six the owner told me to keep hunting.")
