"""consolidate(keep=10) reported {"kept": 10, "active": 0, "staled": 20}. What is the store afterwards?

`active: 0` would mean recall returns nothing. Either the field means something else, or the dream
pass demotes everything. Measure the status distribution and, decisively, whether recall still works —
a report is not the store.
"""
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


def build(n=30, distinct_keys=True):
    st = Inspeximus(path=None, receipts=True)
    for i in range(n):
        kw = {"key": f"k{i}", "object": f"v{i}"} if distinct_keys else {}
        st.remember(f"the {['billing','auth','cache','queue'][i % 4]} service fact number {i}",
                    source={"doc": f"team-{i % 3}"}, **kw)
    return st


for distinct in (True, False):
    st = build(distinct_keys=distinct)
    before = Counter(r.get("status") for r in st.items)
    hits_before = len(st.recall("billing service fact", k=10))
    rep = st.consolidate(keep=10)
    after = Counter(r.get("status") for r in st.items)
    hits_after = len(st.recall("billing service fact", k=10))
    print(f"=== distinct keys: {distinct} ===")
    print(f"  report : {json.dumps(rep, default=str)}")
    print(f"  status before: {dict(before)}")
    print(f"  status after : {dict(after)}")
    print(f"  recall hits  : {hits_before} -> {hits_after}")
    active_after = after.get("active", 0)
    print(f"  ACTIVE after consolidate(keep=10): {active_after}")
    verdict = ("OK — recall still works and the counts line up"
               if hits_after > 0 else "!! recall returns NOTHING after consolidation")
    print(f"  {verdict}\n")

print("=== what does `kept` mean against the store? ===")
st = build()
rep = st.consolidate(keep=10)
act = [r for r in st.items if r.get("status") == "active"]
print(f"  report kept={rep.get('kept')}  active records in the store={len(act)}  "
      f"total records={len(st.items)}")
print("  a `kept` that does not equal the surviving active population is a label, not a measurement —")
print("  unless the docstring defines it otherwise, which is the thing to check before calling it a bug.")
