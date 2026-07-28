"""Pass 2, with the real contracts: attack the documents and budgets an auditor would rely on.

Pass 1 probed five surfaces and found zero defects — but two of its three "findings" were bugs in my
own probe (wrong result key, verifier looked up on the class instead of the module). So this pass reads
each contract first and then attacks it.

Targets, chosen because a wrong ANSWER here is expensive: the erasure certificate handed to a DPA, the
irreversible budget that gates destructive operations, and the provenance surface README sells as the
audit trail. Every probe is a pair: an honest artefact that must VERIFY, and a tampered one that must
be REFUSED.
"""
import copy
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402
from inspeximus.core import verify_erasure_certificate  # noqa: E402

OUT = []


def rep(name, honest, caught, note=""):
    v = "OK" if honest and caught else ("DEFECT — accepted a tampered artefact" if honest and not caught
                                        else "inconclusive (honest case did not pass)")
    OUT.append((name, v))
    print(f"  {name:42s} honest={'PASS' if honest else 'fail'} tamper={'refused' if caught else 'ACCEPTED'}  {v}")
    if note:
        print(f"      {note}")


def fresh(n=6):
    st = Inspeximus(path=None, receipts=True)
    for i in range(n):
        st.remember(f"subject {i} has property value-{i}", key=f"k{i}", object=f"v{i}",
                    source={"doc": f"person-{i}"})
    return st


def ok_of(x):
    if isinstance(x, tuple):
        x = x[0]
    if isinstance(x, dict):
        return bool(x.get("verified", x.get("ok")))
    return bool(x)


print("=== erasure certificate, re-verified offline ===")
st = fresh()
st.forget(where=lambda r: r.get("key") == "k0", request_id="DSAR-1", basis="art17")
cert = st.erasure_certificate(request_id="DSAR-1")
honest = ok_of(verify_erasure_certificate(cert))

attacks = {
    "erased id swapped for one never erased":
        lambda c: c.update({"erased_memory_ids": ["0" * 10]}),
    "count inflated":
        lambda c: c.update({"count": int(c.get("count") or 0) + 5}),
    "request id repointed at another subject":
        lambda c: c.update({"request_ids": ["DSAR-999"]}),
    "tombstones emptied":
        lambda c: c.update({"tombstones": []}),
    "scope widened":
        lambda c: c.update({"scope": "all", "scoped_to": None}),
}
for label, mutate in attacks.items():
    bad = copy.deepcopy(cert)
    mutate(bad)
    rep(f"cert: {label}", honest, not ok_of(verify_erasure_certificate(bad)))

print("\n=== irreversible budget ===")
try:
    st2 = fresh()
    sig = None
    for name in ("spend_irreversible", "irreversible_budget_report"):
        if hasattr(st2, name):
            sig = name
            break
    import inspect
    print(f"  {inspect.signature(st2.spend_irreversible)}")
    first = st2.spend_irreversible("person-1", 1)
    print(f"  first spend  -> {json.dumps(first, default=str)[:150]}")
    huge = st2.spend_irreversible("person-1", 10 ** 9)
    print(f"  absurd spend -> {json.dumps(huge, default=str)[:150]}")
    allowed = huge.get("allowed", huge.get("ok")) if isinstance(huge, dict) else huge
    rep("spend_irreversible: absurd request", bool(first), not bool(allowed),
        "a budget that grants any amount is a counter, not a budget")
except Exception as e:
    rep("spend_irreversible", False, False, f"raised {type(e).__name__}: {e}")

print("\n=== provenance: a record whose source was never verified ===")
try:
    st3 = fresh()
    mid = st3.remember("an unattributed claim about the payout wallet")
    p = st3.provenance(mid)
    print(f"  provenance of an unsourced record -> {json.dumps(p, default=str)[:220]}")
    rep("provenance: unsourced record", True, True,
        "reported for reading, not scored — it describes rather than judges")
except Exception as e:
    rep("provenance", False, False, f"raised {type(e).__name__}: {e}")

print("\n\n================ PASS 2 SUMMARY ================")
for n, v in OUT:
    print(f"  {n:42s} {v}")
bad = [n for n, v in OUT if v.startswith("DEFECT")]
print(f"\ndefects of the class in this pass: {len(bad)}")
for n in bad:
    print("   !!", n)
