"""Does erasing a subject that is not in the store delete somebody else's data?

Found by accident: a test asserting that forget_subject("crm/nobody-here") erases nothing instead saw it
erase 1 record -- the record belonging to crm/alice.

Suspected mechanism: subject matching runs on the CANONICAL form, and canonicalisation collapses a
path-style source to its head ("crm/alice" -> "crm", measured earlier today alongside "employee/1001" ->
"employee"). The ambiguity guard only fires when TWO DISTINCT sources share a canonical form; with a
single source in the bucket there is no collision to detect, so an unrelated subject string that
canonicalises into the same bucket matches it silently.

If that holds, a right-to-erasure request naming a person who was never in the store hard-deletes a
different person's records, and reports success. That is the most destructive version of the defect class
this audit has been closing -- not a clean verdict about unexamined input, but a DELETION on unexamined
identity.

CONTROLS: a subject in a genuinely different bucket must erase nothing; and the correct subject must still
erase its own records.
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


def store():
    d = tempfile.mkdtemp()
    st = Inspeximus(path=os.path.join(d, "s.json"), receipts=True)
    st.remember("alice's address is 12 Rose Lane", key="a::addr", object="12 Rose Lane",
                source={"doc": "crm/alice"})
    st.remember("alice's phone is 0900 111 222", key="a::phone", object="0900 111 222",
                source={"doc": "crm/alice"})
    return st


def alive(st):
    return [r["text"][:34] for r in st.items if r.get("status") == "active"]


print("canonical forms:")
for s in ("crm/alice", "crm/nobody-here", "crm/bob", "hr/alice", "totally-different"):
    print(f"   {s:20s} -> {Inspeximus._canon_source(s)!r}")

print("\n=== erase a subject that is NOT in the store ===")
st = store()
before = alive(st)
res = st.forget_subject("crm/nobody-here", request_id="D-ghost")
print(f"   before: {before}")
print(f"   forget_subject('crm/nobody-here') -> erased={res['erased']}")
print(f"   after : {alive(st)}")
ghost_deleted = res["erased"] > 0

print("\n=== CONTROL 1: a subject in a different bucket must erase nothing ===")
st2 = store()
r2 = st2.forget_subject("hr/someone-else", request_id="D-other")
print(f"   forget_subject('hr/someone-else') -> erased={r2['erased']}   survivors={len(alive(st2))}")

print("\n=== CONTROL 2: the real subject must still erase its own records ===")
st3 = store()
r3 = st3.forget_subject("crm/alice", request_id="D-real")
print(f"   forget_subject('crm/alice') -> erased={r3['erased']}   survivors={len(alive(st3))}")

print("\n=== VERDICT ===")
if ghost_deleted and r2["erased"] == 0 and r3["erased"] == 2:
    print("   CONFIRMED: a right-to-erasure request for a subject that was NEVER in the store")
    print("   hard-deleted another subject's records, and reported success. The controls hold:")
    print("   a different bucket erases nothing, and the correct subject still works.")
else:
    print(f"   NOT the clean picture assumed: ghost={ghost_deleted}, other={r2['erased']}, real={r3['erased']}")
