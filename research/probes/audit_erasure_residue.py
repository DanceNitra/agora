"""Does erasure leave the erased VALUE behind, and does the audit surface that or echo the request?

Four findings from the erasure audit, none of them yet measured. All four are the same class the whole
month has been producing -- a surface that reports a clean verdict about input it never examined:

  R1  `complete: true` while the erased value survives in `meta`. Erasure clears the text; if the value was
      also written to `object`, `key`, or a meta field, the report can certify a deletion that did not
      remove the data. This is the worst of the four: it is not a reporting defect, it is residue.
  R2  `erasure_audit` matches on the COARSE canonical key -- the same host-only collapse that let a DSAR
      for crm/alice reach crm/bob. If it echoes the request back rather than checking the store, a subject
      that was never erased reports clean.
  R3  `coverage` on dry_run. A rehearsal that reports the same shape as a real run, or no shape at all.
  R4  `slash` / `spend_irreversible` take a subject too. If they resolve it coarsely, an irreversible act
      lands on the wrong party -- worse than an over-broad read, because there is nothing to undo.

Every arm has a control that must come out the other way.
"""
import json
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


def store(**kw):
    return Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), receipts=True, **kw)


def residue(st, needle):
    """Every place the erased value could still be sitting, not just `text`."""
    out = []
    for r in st.items:
        blob = json.dumps({k: v for k, v in r.items() if k != "text"}, default=str)
        where = []
        if needle in (r.get("text") or ""):
            where.append("text")
        if needle in blob:
            where.append("non-text fields")
        if where:
            out.append((r.get("id"), r.get("status"), "+".join(where)))
    return out


print("=== R1: does the erased VALUE survive in object/key/meta while the report says complete? ===")
st = store()
st.remember("alice salary is 92000", key="pay::alice", object="92000",
            source={"doc": "hr/alice"}, meta={"note": "confirmed 92000 by payroll"})
res = st.forget_subject("hr/alice", request_id="dsar-1", basis="art17")
left = residue(st, "92000")
print(f"   forget_subject -> erased={res.get('erased')} complete={(res.get('coverage') or {}).get('complete')}")
print(f"   residue of the erased value '92000': {left or 'NONE'}")
for rid, status, where in left:
    rec = next(r for r in st.items if r["id"] == rid)
    print(f"      {rid} status={status} in {where}: object={rec.get('object')!r} "
          f"key={rec.get('key')!r} meta={rec.get('meta')!r}")
print("   -> a report that certifies completeness must have examined the fields the value can live in.\n")

print("=== R1b CONTROL: a value that was ONLY ever in text must come back clean ===")
st2 = store()
st2.remember("bob likes hiking", source={"doc": "hr/bob"})
st2.forget_subject("hr/bob", request_id="dsar-2", basis="art17")
print(f"   residue of 'hiking': {residue(st2, 'hiking') or 'NONE'}  (must be NONE, else the probe")
print("      would report residue everywhere and prove nothing)\n")

print("=== R2: does erasure_audit check the store, or echo the request? ===")
st3 = store()
st3.remember("carol salary 50", key="p::carol", object="50", source={"doc": "hr/carol"})
st3.remember("dave salary 60", key="p::dave", object="60", source={"doc": "hr/dave"})
fn = getattr(st3, "erasure_audit", None)
if fn is None:
    print("   erasure_audit: MISSING")
else:
    for subj, expect in (("hr/carol", "erased -> should be clean"),
                         ("hr/dave", "NOT erased -> must NOT report clean"),
                         ("hr/nobody-here", "never existed -> must not claim to have erased anything")):
        if subj == "hr/carol":
            st3.forget_subject("hr/carol", request_id="r1", basis="art17")
        try:
            out = fn(subj)
        except Exception as e:
            print(f"   {subj:18s} raised {type(e).__name__}: {str(e)[:60]}")
            continue
        blob = json.dumps(out, default=str)
        print(f"   {subj:18s} ({expect})")
        print(f"      -> {blob[:200]}")
print("   -> the three arms must NOT agree. If hr/dave reports the same as hr/carol, the audit is")
print("      answering about the request rather than about the store.\n")

print("=== R3: does a dry run report coverage, and does it differ from a real one? ===")
st4 = store()
st4.remember("erin salary 70", key="p::erin", object="70", source={"doc": "hr/erin"})
try:
    dry = st4.forget_subject("hr/erin", request_id="dry", dry_run=True)
    print(f"   dry_run  -> keys={sorted(dry.keys())}")
    print(f"              coverage={dry.get('coverage', 'ABSENT')}")
    print(f"   store still holds erin? {bool(residue(st4, '70'))}  (must be True -- a rehearsal that")
    print("              actually deleted would be the worst outcome of all)")
    real = st4.forget_subject("hr/erin", request_id="real", basis="art17")
    print(f"   real     -> coverage={real.get('coverage', 'ABSENT')}")
except TypeError as e:
    print(f"   dry_run not supported: {str(e)[:90]}")

print("\n=== R4: do slash / spend_irreversible resolve a subject coarsely? ===")
for name in ("slash", "spend_irreversible"):
    st5 = store()
    st5.remember("alice record", key="a", object="A", source={"doc": "crm/alice"})
    st5.remember("bob record", key="b", object="B", source={"doc": "crm/bob"})
    fn = getattr(st5, name, None)
    if fn is None:
        print(f"   {name}: MISSING")
        continue
    try:
        out = fn("crm/nobody-here")
        print(f"   {name}('crm/nobody-here') -> {json.dumps(out, default=str)[:160]}")
    except TypeError as e:
        print(f"   {name}: signature does not take a bare subject -- {str(e)[:90]}")
    except Exception as e:
        print(f"   {name} raised {type(e).__name__}: {str(e)[:90]}")
print("   -> a ghost subject must not be able to reach a real party through an IRREVERSIBLE act.")
