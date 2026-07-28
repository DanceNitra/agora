"""Does the third party still survive, now that the collision guard no longer fires for them?

The path-preserving subject match stops 'crm/nobody-here' deleting crm/alice. It also means
'crm.example.com/alice' and 'crm.example.com/bob' no longer canonicalise alike -- so AmbiguousSubject stops
being raised for that pair, and several tests that assert the RAISE now fail.

That is only acceptable if the OUTCOME those tests exist to protect is still achieved. The guard was never
the goal; the goal is that a DSAR for Alice does not delete Bob. Refusing was the old way of getting there
when the two were indistinguishable. If they are now distinguishable, erasing exactly Alice is strictly
better than refusing.

So this asks the outcome question directly, and separately checks that a genuinely ambiguous pair -- two
different raw sources that still resolve alike WITH the path -- does still raise.
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402
from inspeximus.core import AmbiguousSubject  # noqa: E402


def store(pairs):
    d = tempfile.mkdtemp()
    st = Inspeximus(path=os.path.join(d, "s.json"), receipts=True)
    for i, (text, src) in enumerate(pairs):
        st.remember(text, key=f"k{i}", object=f"v{i}", source={"doc": src})
    return st


def alive(st):
    return sorted(r["text"][:26] for r in st.items if r.get("status") == "active")


print("=== 1. the case the old guard protected: two people under one host ===")
st = store([("alice's payout account is bank A", "crm.example.com/alice"),
            ("bob's payout account is bank B", "crm.example.com/bob")])
print(f"   canon_subject alice = {Inspeximus._canon_subject('crm.example.com/alice')!r}")
print(f"   canon_subject bob   = {Inspeximus._canon_subject('crm.example.com/bob')!r}")
try:
    res = st.forget_subject("crm.example.com/alice", request_id="D1")
    raised = None
except AmbiguousSubject as e:
    res, raised = None, str(e)[:70]
print(f"   raised AmbiguousSubject: {raised or 'no'}")
if res:
    print(f"   erased={res['erased']}   survivors={alive(st)}")
bob_safe = any("bob" in s for s in alive(st))
alice_gone = not any("alice" in s for s in alive(st))
print(f"   -> bob's data survives: {bob_safe}   alice erased: {alice_gone}")

print("\n=== 2. a genuinely ambiguous pair must STILL refuse ===")
st2 = store([("record about user 42 variant one", "User_42"),
             ("record about user 42 variant two", "user-42")])
print(f"   canon_subject 'User_42' = {Inspeximus._canon_subject('User_42')!r}, "
      f"'user-42' = {Inspeximus._canon_subject('user-42')!r}")
try:
    st2.forget_subject("User_42", request_id="D2")
    print("   raised: no  -> erased both without asking")
    still_guarded = False
except AmbiguousSubject as e:
    print(f"   raised: {str(e)[:80]}")
    still_guarded = True

print("\n=== VERDICT ===")
print(f"   third party protected without refusing : {bob_safe and alice_gone}")
print(f"   genuine ambiguity still refused        : {still_guarded}")
if bob_safe and alice_gone:
    print("   The guard's PURPOSE is met by a better mechanism: the two subjects are now")
    print("   distinguishable, so the DSAR completes AND the third party is untouched -- strictly")
    print("   better than refusing. Tests asserting the raise for this pair encode the old mechanism.")
