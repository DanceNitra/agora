"""The ghost-subject fix is incomplete: it comes back through the taint branch I wrote to stop it.

My own docstring in `_narrow_to_subject` says the inherited set is "read from `taint` specifically, never
from a record's own source, so the ghost subject this narrowing exists to stop cannot sneak back in
through it." The audit says it sneaks back through exactly there, because `inherited` is matched against
`coarse = {subject, _canon_source(subject)}` -- the host-only key the whole fix exists to stop using -- and
when there are no roots the function returns ONLY that set.

Three cases, each with a control:
  A  ghost subject + a derived record          -> should erase 0
  B  Alice's DSAR + a record derived from BOB  -> should erase only Alice's
  C  punctuation-stripped identity             -> 'crm/alice-1' vs 'crm/alice1' should not be one subject
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


def store():
    d = tempfile.mkdtemp()
    return Inspeximus(path=os.path.join(d, "s.json"), receipts=True)


def alive(st):
    return sorted((r.get("text") or "")[:30] for r in st.items if r.get("status") == "active")


print("=== A. ghost subject, with a record DERIVED from a real one ===")
st = store()
a = st.remember("alice home address is 5 Elm St", key="a", object="5 Elm St", source={"doc": "crm/alice"})
st.remember("summary of alice file", key="s", object="sum", source={"doc": "summary-svc"},
            derived_from=[a])
res = st.forget_subject("crm/nobody-here", request_id="ghost")
print(f"   forget_subject('crm/nobody-here') -> erased={res['erased']}")
print(f"   survivors: {alive(st)}")
print(f"   -> should be erased=0. {'DEFECT' if res['erased'] else 'clean'}")

print("\n   CONTROL A1: same store WITHOUT the derived record")
st = store()
st.remember("alice home address is 5 Elm St", key="a", object="5 Elm St", source={"doc": "crm/alice"})
print(f"      ghost -> erased={st.forget_subject('crm/nobody-here')['erased']}   (expect 0)")
print("   CONTROL A2: the real subject still works")
st = store()
a = st.remember("alice home", key="a", object="x", source={"doc": "crm/alice"})
st.remember("summary", key="s", object="y", source={"doc": "summary-svc"}, derived_from=[a])
print(f"      forget_subject('crm/alice') -> erased={st.forget_subject('crm/alice')['erased']}"
      f"   (expect 2: the record and its derived summary)")

print("\n=== B. Alice's DSAR and a record derived from BOB ===")
st = store()
st.remember("alice salary 100", key="a", object="100", source={"doc": "crm/alice"})
b = st.remember("bob salary 200", key="b", object="200", source={"doc": "crm/bob"})
st.remember("summary of bob file", key="bs", object="sum", source={"doc": "summary-svc"},
            derived_from=[b])
try:
    res = st.forget_subject("crm/alice", request_id="dsar")
    print(f"   erased={res['erased']}   survivors: {alive(st)}")
    bob_ok = any("bob salary" in s for s in alive(st))
    sum_ok = any("summary of bob" in s for s in alive(st))
    print(f"   -> Alice owns 1 record. bob's record kept: {bob_ok}   bob's SUMMARY kept: {sum_ok}")
    print(f"   {'DEFECT: a third party derived record went with it' if not sum_ok else 'clean'}")
except Exception as e:
    print(f"   raised {type(e).__name__}: {str(e)[:70]}")

print("\n=== C. punctuation-stripped identity ===")
st = store()
st.remember("payroll row for alice1", key="p", object="x", source={"doc": "crm/alice1"})
res = st.forget_subject("crm/alice-1", request_id="punct")
print(f"   forget_subject('crm/alice-1') on a store holding only 'crm/alice1' -> erased={res['erased']}")
print(f"   -> should be 0. {'DEFECT' if res['erased'] else 'clean'}")
st = store()
st.remember("payroll row for bob9", key="p", object="x", source={"doc": "crm/bob9"})
print(f"   CONTROL: forget_subject('crm/alice-1') on a bob9 store -> "
      f"{st.forget_subject('crm/alice-1')['erased']}   (expect 0)")
