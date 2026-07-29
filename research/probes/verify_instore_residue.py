"""Does the erasure now notice a survivor that still holds what it just erased?

Built after measuring that it did not: a record reading "summary: she lives at 5 Elm St" survived
`forget_subject('hr/alice')` while holding the erased address verbatim, and the call returned `erased: 1`
with nothing else to say. The values were in hand at that instant and nobody looked -- and it is the only
instant possible, since tombstones are content-free by design.

Every arm has a control that must come out the other way, plus the two that matter for a compliance
surface: the values must never be echoed into the report, and a short value must not match everywhere.
"""
import json
import os
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


def st():
    return Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), receipts=True)


print("A: the case that started this -- an unattributed survivor repeats the erased value")
m = st()
m.remember("alice home address is 5 Elm St", key="a::addr", object="5 Elm St",
           source={"doc": "hr/alice"})
m.remember("summary: she lives at 5 Elm St", source={"doc": "svc"})
res = m.forget_subject("hr/alice", request_id="D", basis="art17")
r = res["residue_in_store"]
print(f"   erased={res['erased']}  residue ok={r['ok']}  findings={r['findings']}")
print(f"   problems: {r['problems']}")
print(f"   values NEVER echoed into the report: {'5 Elm' not in json.dumps(r)}")

print("\nB CONTROL: a clean erasure must report ok=True, or the field says 'incomplete' always")
m2 = st()
m2.remember("alice home address is 5 Elm St", key="a::addr", object="5 Elm St",
            source={"doc": "hr/alice"})
m2.remember("weather is fine", source={"doc": "svc"})
r2 = m2.forget_subject("hr/alice", request_id="D", basis="art17")["residue_in_store"]
print(f"   ok={r2['ok']}  findings={len(r2['findings'])}  checked={r2['checked_records']}")

print("\nC CONTROL: a short value must NOT match everywhere")
m3 = st()
m3.remember("x", key="k", object="ok", source={"doc": "hr/alice"})
m3.remember("this record says ok and x a lot", source={"doc": "svc"})
r3 = m3.forget_subject("hr/alice", request_id="D", basis="art17")["residue_in_store"]
print(f"   ok={r3['ok']}  searched_values={r3['searched_values']}")
print(f"   problems: {r3['problems'][:1]}")
print("   -> searched_values must be 0 and ok must be FALSE: nothing was compared, and an empty")
print("      search is not a clean result.")

print("\nD: cost on a larger store (1000 records, erase 1)")
m4 = st()
for i in range(1000):
    m4.remember(f"record number {i} with some text", source={"doc": f"src{i % 7}"})
m4.remember("alice home address is 5 Elm St", key="a", object="5 Elm St",
            source={"doc": "hr/alice"})
t0 = time.time()
r4 = m4.forget_subject("hr/alice", request_id="D", basis="art17")
dt = time.time() - t0
print(f"   erased={r4['erased']}  checked={r4['residue_in_store']['checked_records']}  {dt * 1000:.0f} ms")
print("   -> this runs on EVERY erasure, so a cost that grows with the store is the thing to watch.")
