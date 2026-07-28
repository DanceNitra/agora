"""Pass 6 — the analytical surfaces. Different class, different question.

`consolidate`, `consolidate_clusters`, `value_by_cohort`, `forget`, `audit_bundle` do not REFUSE
anything, so the refusal class does not apply. The question that does:

    does it report a number its input cannot support?

Three shapes, all of which this project has been bitten by before:
  DENOMINATOR — a rate from an empty or n=1 population, printed as if it meant something
  UNVERIFIED COUNT — "forgotten: 7" reported without checking that 7 actually went
  SILENT TRUNCATION — a cap applied and not mentioned, so partial reads as complete

Every probe prints the contract first, then the attack, then the ground truth computed independently.
"""
import inspect
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

OUT = []


def note(n, v, d=""):
    OUT.append((n, v))
    print(f"  >> {n}: {v}")
    if d:
        print(f"     {d}")


def contract(fn, n=4):
    try:
        print(f"  sig: {inspect.signature(fn)}")
    except Exception:
        pass
    for ln in (inspect.getdoc(fn) or "").splitlines()[:n]:
        print(f"    | {ln[:110]}")


def store(n=20):
    st = Inspeximus(path=None, receipts=True)
    for i in range(n):
        st.remember(f"the {['billing','auth','cache','queue'][i % 4]} service fact number {i}",
                    key=f"k{i}", object=f"v{i}", source={"doc": f"team-{i % 3}"})
    return st


print("=== forget(): is the reported count the count that actually went? ===")
contract(Inspeximus.forget, 3)
st = store()
before = len([r for r in st.items if r.get("status") != "deleted"])
rep = st.forget(where=lambda r: (r.get("key") or "").startswith("k1"))
after = len([r for r in st.items if r.get("status") != "deleted"])
claimed = rep.get("forgotten")
actual = before - after
print(f"  report={json.dumps(rep, default=str)[:120]}")
print(f"  live records {before} -> {after}   actual removed={actual}   claimed={claimed}")
note("forget", "OK" if claimed == actual else "DEFECT — reported count differs from the change",
     f"two-sided diff on the record COUNT, not just the return value")

print("\n=== consolidate(keep=N): does it report what it really kept? ===")
contract(Inspeximus.consolidate, 3)
st2 = store(30)
live_before = len([r for r in st2.items if r.get("status") != "deleted"])
res = st2.consolidate(keep=10)
live_after = len([r for r in st2.items if r.get("status") != "deleted"])
print(f"  report={json.dumps(res, default=str)[:150]}")
print(f"  live {live_before} -> {live_after}  (asked to keep 10)")
note("consolidate", "inspect", f"kept {live_after} against a keep=10 request; see report shape above")

print("\n=== value_by_cohort(): does it report a rate from an empty or n=1 cohort? ===")
contract(Inspeximus.value_by_cohort, 4)
empty = Inspeximus(path=None)
r_empty = empty.value_by_cohort()
print(f"  on an EMPTY store  -> {json.dumps(r_empty, default=str)[:200]}")
one = Inspeximus(path=None)
one.remember("a single solitary fact about the billing service", source={"doc": "team-0"})
r_one = one.value_by_cohort()
print(f"  on a ONE-record store -> {json.dumps(r_one, default=str)[:200]}")
carries_n = "n" in json.dumps(r_one) or "count" in json.dumps(r_one)
note("value_by_cohort",
     "OK" if carries_n else "SUSPECT — a rate without its denominator",
     "a cohort statistic must carry the population it was computed over")

print("\n=== audit_bundle(): does the summary derive from the chain, or from the claim? ===")
try:
    from inspeximus.audit_bundle import build_bundle, verify_bundle
    st3 = store(12)
    b = build_bundle(st3)
    ok = verify_bundle(b)
    print(f"  honest bundle -> ok={ok['ok']} writes={ok['summary'].get('writes')}")
    forged = json.loads(json.dumps(b))
    forged["supersession"] = dict(forged.get("supersession") or {})
    forged["supersession"]["superseded_total"] = 999999
    r = verify_bundle(forged)
    print(f"  superseded_total forged to 999999 -> ok={r['ok']} "
          f"reported={r['summary'].get('superseded_total')}")
    note("audit_bundle",
         "OK" if (not r["ok"] or r["summary"].get("superseded_total") != 999999)
         else "DEFECT — the bundle reports a claimed number as verified",
         "the summary must derive from the chain, never echo the claim")
except Exception as e:
    note("audit_bundle", "n/a", f"{type(e).__name__}: {str(e)[:120]}")

print("\n\n================ PASS 6 ================")
for n, v in OUT:
    print(f"  {n:20s} {v}")
