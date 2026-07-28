"""Pass 4 — the remaining verification-shaped surfaces. Contract first, attack second.

The class: a clean/empty verdict about input never structurally examined. An EMPTY result is the
sneakiest form of it — "no contradictions found" and "could not look for contradictions" print the
same way.

Each block prints the signature and the first lines of the contract before probing, because four of my
probes today were wrong about the contract rather than about the code.
"""
import inspect
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

FIND = []


def contract(fn, n=5):
    try:
        print(f"  sig: {inspect.signature(fn)}")
    except Exception:
        pass
    doc = (inspect.getdoc(fn) or "").splitlines()
    for ln in doc[:n]:
        print(f"    | {ln[:112]}")


def note(name, verdict, detail):
    FIND.append((name, verdict, detail))
    print(f"  >> {name}: {verdict}")
    if detail:
        print(f"     {detail}")


def store(n=6, receipts=True, embed=None):
    st = Inspeximus(path=None, receipts=receipts, embed=embed)
    for i in range(n):
        st.remember(f"the {['billing','auth','cache','queue','search','deploy'][i%6]} service "
                    f"uses method-{i}", key=f"svc{i}", object=f"m{i}", source={"doc": f"team-{i}"})
    return st


print("=== contradictions(): does an EMPTY list mean 'none' or 'could not look'? ===")
st = store()
contract(Inspeximus.contradictions)
plain = st.contradictions()
st2 = store()
st2.remember("the billing service uses method-0", key="svc0", object="TOTALLY-DIFFERENT")
conflicted = st2.contradictions()
print(f"  no conflict planted -> {len(plain)} found")
print(f"  conflict planted    -> {len(conflicted)} found")
note("contradictions",
     "OK" if len(conflicted) > len(plain) else "SUSPECT — planted conflict not detected",
     f"empty on a clean store={len(plain)==0}; detects a planted one={len(conflicted)>0}")

print("\n=== compliance_report(): does it claim evidence for controls it never exercised? ===")
from inspeximus.compliance import compliance_report  # noqa: E402
contract(compliance_report)
bare = Inspeximus(path=None, receipts=False)
bare.remember("one fact, no receipts, nothing exercised")
rep = compliance_report(bare)
txt = json.dumps(rep, default=str)
ev = txt.lower().count('"evidence"')
print(f"  bare store report keys: {sorted(rep)[:10] if isinstance(rep, dict) else type(rep)}")
print(f"  occurrences of 'evidence' in a report over a store with NO receipts: {ev}")
controls = rep.get("controls") if isinstance(rep, dict) else None
if isinstance(controls, list) and controls:
    st_counts = {}
    for c in controls:
        st_counts[str(c.get("status"))] = st_counts.get(str(c.get("status")), 0) + 1
    print(f"  control statuses: {st_counts}")
    note("compliance_report",
         "OK" if st_counts.get("evidence", 0) == 0 else "SUSPECT — 'evidence' on an unexercised store",
         f"{st_counts.get('evidence',0)} controls marked evidence with receipts disabled")
else:
    note("compliance_report", "inspect", f"shape: {str(rep)[:150]}")

print("\n=== forget_subject(): is the reported erasure verified, or just counted? ===")
contract(Inspeximus.forget_subject, 4)
st3 = store()
r = st3.forget_subject("team-1", request_id="DSAR-9", basis="art17")
left = [x for x in st3.items if (x.get("source") or {}).get("doc") == "team-1"
        and x.get("status") != "deleted"]
print(f"  report: {json.dumps(r, default=str)[:150]}")
print(f"  records still present for that subject afterwards: {len(left)}")
note("forget_subject",
     "OK" if (r.get('erased', 0) > 0 and not left) else "SUSPECT",
     f"claimed erased={r.get('erased')} and {len(left)} remained")

print("\n=== attest(): what does it actually assert? ===")
try:
    from inspeximus import attest
    contract(attest, 6)
    note("attest", "inspect", "contract printed above — attack chosen from it in pass 5")
except Exception as e:
    note("attest", "n/a", str(e)[:120])

print("\n=== grade(): does it grade on absent evidence? ===")
try:
    contract(Inspeximus.grade, 5)
    st4 = store()
    g_known = st4.grade(st4.items[0]["id"]) if st4.items else None
    g_unknown = st4.grade("0" * 10)
    print(f"  grade of a real id    : {json.dumps(g_known, default=str)[:120]}")
    print(f"  grade of an absent id : {json.dumps(g_unknown, default=str)[:120]}")
    note("grade",
         "OK" if (g_unknown is None or (isinstance(g_unknown, dict) and not g_unknown.get("ok", True))
                  or g_unknown != g_known) else "SUSPECT — same verdict for a record that is not there",
         "")
except Exception as e:
    note("grade", "n/a", f"{type(e).__name__}: {str(e)[:110]}")

print("\n\n================ PASS 4 ================")
for n, v, d in FIND:
    print(f"  {n:22s} {v}")
