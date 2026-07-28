"""Verifying the red-team panel's four load-bearing findings against the LIVE repo, not a copy.

The panel is not evidence; it is a list of hypotheses. Two of its findings look like they were measured on
`agora/inspeximus_pypi/inspeximus/inspeximus.py` -- a stale vendored copy -- rather than on
`C:\\Users\\Danculus\\inspeximus-repo`, which is where today's fixes landed. Reading a claim off the wrong
artifact is the exact mistake that cost me a published physics claim, so every one gets re-run here.

  F-A  STEELMAN: `remember` is one of FIVE MCP write paths. `remember_decision`, `route`, `observe`,
       `resolve_reopened` reach the store and take no `source`, so an agent following the docstring that
       calls remember_decision "the thing that actually matters" reproduces would_erase=0.
  F-B  METHOD: `erasure_audit`'s `declared` counts lineage over the WHOLE store, so ONE unrelated record
       declaring a parent flips the verdict away from `unaudited` for a subject whose own derivatives
       declared nothing -- a FALSE PASS that only became reachable because of today's fix.
  F-C  METHOD: `dry_run` returns BEFORE the AmbiguousSubject raise, so a preview can report would_erase=2
       for a request that really raises and erases 0.
  F-D  BLIND SPOT: `_canon_source` keeps only the first path segment, so 'hr/alice', 'hr/bob' and
       'hr/carol' are one subject and one DSAR empties the namespace -- and the tombstones certify it as
       deliberate. If true on the live repo this is the most serious thing found all week. But today's
       work replaced the erasure selector with a path-preserving `_canon_subject` and added an
       AmbiguousSubject refusal, so the prediction is that this reproduces on the COPY and not on HEAD.
"""
import inspect
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LIVE = r"C:\Users\Danculus\inspeximus-repo"
sys.path.insert(0, LIVE)
from inspeximus import Inspeximus  # noqa: E402

print(f"live module: {Inspeximus.__module__} from {sys.modules['inspeximus'].__file__}\n")

print("=== F-A: how many MCP write paths can attach a source? ===")
os.environ["INSPEXIMUS_PATH"] = os.path.join(tempfile.mkdtemp(), "m.json")
import inspeximus.mcp_server as mcp  # noqa: E402

WRITE_TOOLS = ["remember", "remember_decision", "route", "observe", "resolve_reopened", "consolidate"]
for name in WRITE_TOOLS:
    fn = getattr(mcp, name, None)
    if fn is None:
        print(f"   {name:20s} ABSENT")
        continue
    params = list(inspect.signature(fn).parameters)
    has = [p for p in ("source", "derived_from") if p in params]
    print(f"   {name:20s} {has or 'NEITHER'}")
print("   -> if only `remember` has them, 'the product surface' in the claim means 'one tool of several'.")

print("\n   measured, not inferred -- write via remember_decision and try to erase the subject:")
mid = mcp.remember_decision("we will bill alice monthly", because="she asked", topic="billing::alice")
st = Inspeximus(path=os.environ["INSPEXIMUS_PATH"], receipts=True)
for subj in ("alice", "hr/alice", "billing::alice"):
    r = st.forget_subject(subj, request_id="d", basis="art17", dry_run=True)
    print(f"     forget_subject({subj!r}) would_erase={r['would_erase']}")

print("\n=== F-B: is the `unaudited` verdict store-wide or subject-scoped? ===")
st2 = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "b.json"), receipts=True)
# ALICE: a root and a derivative that does NOT declare its parent -- her lineage is undeclared.
a = st2.remember("alice file", source={"doc": "hr/alice"})
st2.remember("summary of alice", source={"doc": "summary-svc"})          # no derived_from: undeclared
print(f"   alice only            -> verdict={st2.erasure_audit('hr/alice')['verdict']!r}")
# BOB, entirely unrelated, declares lineage properly.
b = st2.remember("bob file", source={"doc": "hr/bob"})
st2.remember("summary of bob", source={"doc": "summary-svc"}, derived_from=[b])
print(f"   after BOB declares    -> verdict={st2.erasure_audit('hr/alice')['verdict']!r}"
      f"   (alice's lineage is STILL undeclared)")
print(f"   coverage seen by alice: {st2.erasure_audit('hr/alice')['coverage']}")
print("   -> if alice's verdict changed because BOB declared, the audit answers about the STORE while")
print("      being asked about a SUBJECT, and 'no_declared_residue' is then a pass over an uninspected")
print("      subject -- strictly worse than the honest 'unaudited' it replaced.")

print("\n=== F-C: does dry_run preview a request that would actually refuse? ===")
st3 = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "c.json"), receipts=True)
st3.remember("alice payroll", key="p::a", object="1", source={"doc": "crm.example.com/alice"})
st3.remember("bob payroll", key="p::b", object="2", source={"doc": "crm.example.com/bob"})
prev = st3.forget_subject("crm.example.com/alice", request_id="p", basis="art17", dry_run=True)
print(f"   dry_run  -> would_erase={prev['would_erase']}  also_carrying={prev.get('also_carrying')}")
try:
    real = st3.forget_subject("crm.example.com/alice", request_id="p", basis="art17")
    print(f"   real     -> erased={real['erased']}")
except Exception as e:
    print(f"   real     -> REFUSED {type(e).__name__}: {str(e)[:120]}")
print("   -> a preview that promises N where the real call refuses is a preview you cannot plan with.")

print("\n=== F-D: does one DSAR empty a shared namespace on the LIVE repo? ===")
st4 = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "d.json"), receipts=True)
for who in ("alice", "bob", "carol"):
    st4.remember(f"{who} record", key=f"k::{who}", object=who, source={"doc": f"hr/{who}"})
print(f"   _canon_source('hr/alice')  = {Inspeximus._canon_source('hr/alice')!r}")
print(f"   _canon_subject('hr/alice') = {Inspeximus._canon_subject('hr/alice')!r}")
print(f"   _canon_subject('hr/bob')   = {Inspeximus._canon_subject('hr/bob')!r}")
try:
    res = st4.forget_subject("hr/alice", request_id="DSAR-1", basis="art17")
    alive = [r.get("object") for r in st4.items if r.get("status") == "active"]
    print(f"   forget_subject('hr/alice') -> erased={res['erased']}   survivors={alive}")
    print("   -> erased must be 1 and bob+carol must survive. If 3, the namespace was emptied and the")
    print("      tombstones certify it as a deliberate, authorised erasure.")
except Exception as e:
    print(f"   forget_subject('hr/alice') -> REFUSED {type(e).__name__}: {str(e)[:140]}")

print("\n=== F-D control: the STALE VENDORED COPY the panel appears to have read ===")
copy_path = r"C:\Users\Danculus\agora\inspeximus_pypi\inspeximus\inspeximus.py"
print(f"   exists: {os.path.exists(copy_path)}")
if os.path.exists(copy_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("stale_insp", copy_path)
    stale = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(stale)
        S = stale.Inspeximus
        print(f"   copy has _canon_subject: {hasattr(S, '_canon_subject')}")
        s5 = S(path=os.path.join(tempfile.mkdtemp(), "e.json"))
        for who in ("alice", "bob", "carol"):
            s5.remember(f"{who} record", key=f"k::{who}", object=who, source={"doc": f"hr/{who}"})
        try:
            r5 = s5.forget_subject("hr/alice", request_id="DSAR-1", basis="art17")
            left = [r.get("object") for r in s5.items if r.get("status") == "active"]
            print(f"   COPY: forget_subject('hr/alice') -> erased={r5['erased']}  survivors={left}")
        except Exception as e:
            print(f"   COPY: REFUSED {type(e).__name__}: {str(e)[:100]}")
    except Exception as e:
        print(f"   could not load the copy: {type(e).__name__}: {str(e)[:100]}")
print("   -> if the copy erases 3 and HEAD erases 1, the finding is real ABOUT THE COPY, and the copy")
print("      is what we publish to PyPI from -- which would make it a shipping defect either way.")
