"""Pass 3 — same two surfaces, used the way their signatures say.

My pass-2 probe misused both:
  * verify_erasure_certificate(cert, store_path=None, store_items=None, expected_pubkey=None) returns a
    DICT, and its step 4 (every erased id is really gone) only runs when the store is supplied. I passed
    no store and then read a key that may not exist, so the honest case "failed" for want of an argument.
  * spend_irreversible(ids, amount, budget, ...) meters MEMORY ids against their sources' lifetime
    budget. I passed a source label as an id, so it found nothing to charge and allowed everything —
    a vacuous pass caused by me, not by it.

Both are now driven from what the signatures actually take.
"""
import copy
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402
from inspeximus.core import verify_erasure_certificate as V  # noqa: E402


def fresh(n=6):
    st = Inspeximus(path=None, receipts=True)
    ids = []
    for i in range(n):
        ids.append(st.remember(f"subject {i} has property value-{i}", key=f"k{i}", object=f"v{i}",
                               source={"doc": f"person-{i}"}))
    return st, ids


print("=== erasure certificate, verified WITH the store as the contract requires ===")
st, ids = fresh()
st.forget(where=lambda r: r.get("key") == "k0", request_id="DSAR-1", basis="art17")
cert = st.erasure_certificate(request_id="DSAR-1")
items = [dict(r) for r in st.items]

res = V(cert, store_items=items)
print(f"  honest verdict: {json.dumps(res, default=str)[:260]}")
keys = sorted(res) if isinstance(res, dict) else []
print(f"  return keys: {keys}")


def good(x):
    return bool(x.get("ok", x.get("verified", False))) if isinstance(x, dict) else bool(x)


honest = good(res)
print(f"  honest passes: {honest}")

if honest:
    attacks = {
        "erased id -> one never erased": lambda c: c.update({"erased_memory_ids": ["0" * 10]}),
        "count inflated": lambda c: c.update({"count": int(c.get("count") or 0) + 5}),
        "request repointed": lambda c: c.update({"request_ids": ["DSAR-999"]}),
        "tombstones emptied": lambda c: c.update({"tombstones": []}),
        "scope widened": lambda c: c.update({"scope": "all", "scoped_to": None}),
        "pubkey swapped": lambda c: c.update({"pubkey": "00" * 32}),
    }
    print()
    for label, mut in attacks.items():
        bad = copy.deepcopy(cert)
        mut(bad)
        r = V(bad, store_items=items)
        refused = not good(r)
        probs = (r.get("problems") or [])[:1] if isinstance(r, dict) else []
        print(f"  {label:32s} -> {'REFUSED' if refused else '!! ACCEPTED'}"
              f"   {probs[0][:70] if probs else ''}")

print("\n=== irreversible budget, metered on REAL memory ids ===")
st2, ids2 = fresh()
import inspect
print(f"  {inspect.signature(st2.spend_irreversible)}")
r1 = st2.spend_irreversible(ids2[:1], amount=0.5, budget=1.0)
print(f"  spend 0.5 of 1.0 on a real id -> {json.dumps(r1, default=str)[:170]}")
r2 = st2.spend_irreversible(ids2[:1], amount=0.9, budget=1.0)
print(f"  spend 0.9 more (over budget)  -> {json.dumps(r2, default=str)[:170]}")
r3 = st2.spend_irreversible(ids2[:1], amount=10 ** 6, budget=1.0)
print(f"  spend 1e6 at once             -> {json.dumps(r3, default=str)[:170]}")
print(f"\n  budget refuses the over-spend: {not bool(r2.get('allowed'))}")
print(f"  budget refuses the absurd one: {not bool(r3.get('allowed'))}")
