"""The rest of the echo-guard audit: the OFF switch, the reports, and the docs.

The load-bearing finding (a retired write reported as a landed one) is fixed. Three remain, and each is
the same shape as the defects this month kept producing -- a surface that answers about something it never
examined:

  F4  INSPEXIMUS_ECHO_GUARD=0 was the documented way to turn the guard off. Once the default flipped, does
      the env var still reach LIBRARY code, or only the MCP server? An operator who reads the README, sets
      the var, and sees writes still being retired has no way to tell the switch is dead.
  F8  governance_report()/memory_report() summarise what the store did. A record retired by policy rather
      than by a newer assertion is a different event. Do the reports distinguish it, or does a value the
      guard dropped look identical to one a later write replaced?
  F9  The docs. If any of them still say the guard is OFF by default, a reader configures against a
      default that no longer exists.

Nothing here is inferred from reading. Each is executed, and each has a control -- a variant that MUST
come out the other way, so a probe that passes everything cannot be passing vacuously.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = r"C:\Users\Danculus\inspeximus-repo"
sys.path.insert(0, REPO)
from inspeximus import Inspeximus  # noqa: E402


def store(**kw):
    return Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), **kw)


def active(st, key):
    return [r.get("object") for r in st.items if r.get("key") == key and r.get("status") == "active"]


def echo_survives(st):
    """Write A, B, then A again. Returns True if the third write LANDED (guard not acting)."""
    st.remember("v is A", key="k", object="A")
    st.remember("v is B", key="k", object="B")
    st.remember("v is A again", key="k", object="A")
    return active(st, "k") == ["A"]


print("=== F4: does INSPEXIMUS_ECHO_GUARD=0 still reach library code? ===")
# Run in a SUBPROCESS: the module reads env at import time, so setting it in this process proves nothing.
prog = (
    "import sys, os, tempfile; sys.path.insert(0, r'%s');"
    "from inspeximus import Inspeximus;"
    "st = Inspeximus(path=os.path.join(tempfile.mkdtemp(), 's.json'));"
    "st.remember('v is A', key='k', object='A');"
    "st.remember('v is B', key='k', object='B');"
    "st.remember('v is A again', key='k', object='A');"
    "print(getattr(st, 'echo_guard', 'MISSING'),"
    "      [r.get('object') for r in st.items if r.get('key')=='k' and r.get('status')=='active'])"
) % REPO
for val in ("0", "1", None):
    env = dict(os.environ)
    env.pop("INSPEXIMUS_ECHO_GUARD", None)
    if val is not None:
        env["INSPEXIMUS_ECHO_GUARD"] = val
    out = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, env=env)
    label = "unset" if val is None else f"={val}"
    print(f"   INSPEXIMUS_ECHO_GUARD{label:6s} -> {out.stdout.strip() or out.stderr.strip()[:100]}")
print("   -> '=0' must print False and leave active ['A']. If it prints True/['B'], the documented")
print("      off-switch is dead in the library and only the MCP server honours it.\n")

print("=== F4b: is the constructor kwarg honoured, and is it the only remaining lever? ===")
for kw in ({"echo_guard": False}, {"echo_guard": True}, {}):
    try:
        st = store(**kw)
        print(f"   Inspeximus({kw or 'defaults'}) -> echo_guard={st.echo_guard}  "
              f"echo landed={echo_survives(st)}")
    except TypeError as e:
        print(f"   Inspeximus({kw or 'defaults'}) -> TypeError: {str(e)[:70]}")
print("   -> CONTROL: the two explicit arms must disagree with each other, else the flag does nothing.\n")

print("=== F8: do the reports distinguish a policy retirement from an ordinary supersession? ===")
guarded = store()
guarded.remember("v is A", key="k", object="A")
guarded.remember("v is B", key="k", object="B")
guarded.remember("v is A again", key="k", object="A")      # retired BY POLICY

plain = store()
plain.remember("v is A", key="k", object="A")
plain.remember("v is B", key="k", object="B")
plain.remember("v is C", key="k", object="C")              # ordinary supersession, no policy involved

for name in ("governance_report", "memory_report", "supersession_report"):
    for label, st in (("policy-retired", guarded), ("ordinary     ", plain)):
        fn = getattr(st, name, None)
        if fn is None:
            print(f"   {name}: MISSING on the store")
            break
        try:
            rep = fn()
        except Exception as e:
            print(f"   {name} ({label}) raised {type(e).__name__}: {str(e)[:60]}")
            continue
        blob = json.dumps(rep, default=str)
        hit = [w for w in ("echo", "echo_guard", "blocked", "retired_by_policy") if w in blob]
        print(f"   {name:20s} {label}: {len(blob):5d} chars, policy words present: {hit or 'NONE'}")
print("   -> the two arms must NOT produce the same summary. If they do, an operator reading the report")
print("      cannot see that the store dropped a write rather than accepting a newer one.\n")

print("=== F9: do the docs still say the guard is OFF by default? ===")
pat = re.compile(r"echo[_ ]?guard", re.I)
offish = re.compile(r"\b(off|disabled|opt[- ]in|False)\b", re.I)
hits = 0
for root, dirs, files in os.walk(REPO):
    dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".pytest_cache", "build", "dist"}]
    for fn in files:
        if not fn.endswith((".md", ".py", ".txt", ".toml")):
            continue
        p = os.path.join(root, fn)
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if pat.search(line) and offish.search(line):
                rel = os.path.relpath(p, REPO)
                print(f"   {rel}:{i}: {line.strip()[:104]}")
                hits += 1
print(f"   -> {hits} line(s) pair the guard with off/disabled/opt-in language. Each needs reading:")
print("      a line DOCUMENTING how to turn it off is fine; a line stating the DEFAULT is off is stale.")
