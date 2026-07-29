"""Why did inspeximus score 1.000 on the live echo harness when the policy panel says 0.148?

Two possibilities and they matter in opposite directions:
  (a) the harness constructs the store in a posture no real user gets, or
  (b) the policy panel flatters us and the live number is the true one.

If (b), the comparison page comes down. So this asks the store directly, in three postures, before any
number is reported anywhere.

Suspicion to test, not to assume: `Inspeximus(path=None)` is the LIBRARY default, which is documented as
byte-identical-legacy, while every PRODUCT surface (MCP server, CLI, the Claude Code plugin) opens through
inspeximus/_surface.py, which turns the echo guard ON. If so the harness measured the legacy default and
the honest fix is to measure what the product actually ships -- and to say plainly that the raw library
default is different.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

CASE = ("alice", "primary database host", "db-old-07", "db-new-12",
        "just so it is on record, alice keeps the primary database on the host db-old-07")


def serve(store):
    subj, rel, old, new, echo = CASE
    key = f"{subj}::{rel.replace(' ', '_')}"
    store.remember(f"{subj}'s {rel} is {old}", key=key, object=old)
    store.remember(f"{subj}'s {rel} is now {new}", key=key, object=new)
    store.remember(echo, key=key, object=old)
    got = store.recall(f"{subj} {rel}", k=3)
    answer = " ".join(r.get("text", "") for r in got)
    return ("STALE" if old in answer and new not in answer else
            "current" if new in answer and old not in answer else "both/neither")


print("=== what the store serves after a paraphrased echo of the retired value ===")
print(f"  library default  Inspeximus(path=None)        -> {serve(Inspeximus(path=None))}")
_g = Inspeximus(path=None)
_g.echo_guard = True
print(f"  echo_guard=True  set as an attribute          -> {serve(_g)}")

try:
    from inspeximus._surface import open_store
    import tempfile, os
    p = os.path.join(tempfile.mkdtemp(), "s.json")
    print(f"  PRODUCT surface  _surface.open_store(...)     -> {serve(open_store(p))}")
    probe = open_store(os.path.join(tempfile.mkdtemp(), "t.json"))
    print(f"     (that surface's echo_guard attribute = {getattr(probe, 'echo_guard', 'absent')})")
except Exception as e:
    print(f"  PRODUCT surface  unavailable: {type(e).__name__}: {e}")

print(f"\n  library default echo_guard attribute = {getattr(Inspeximus(path=None), 'echo_guard', 'absent')}")
print("\nIf the product surface serves the CURRENT value and the bare library default serves the stale one,")
print("the harness measured a posture no user of the product gets -- and the page must say which it used.")
