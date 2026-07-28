"""When nothing external is registered, does erasure still report success?

The measured gap: a store-native delete leaves the application's own vector index untouched -- 8/8 residue
(erasure_manifest_wired_cell, cell A). Wired to a registered target it is 0/8, and a BROKEN wiring cannot
produce a clean receipt (cell C: falsely-complete manifests 0/8, leak named 8/8).

So the mechanism is sound. The question this asks is the product one: what does a caller who never wired
anything SEE? If forget_subject() returns an ordinary success and the certificate reads clean, then the
default experience is a confident report about a surface the library never looked at -- the exact defect
class this audit has been closing all day, except here it is the flagship compliance surface.

Nothing is asserted below that is not read off a live call.
"""
import io
import json
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

d = tempfile.mkdtemp()
st = Inspeximus(path=f"{d}/s.json", receipts=True)
st.remember("alice's home address is 12 Rose Lane", key="alice::address",
            object="12 Rose Lane", source={"doc": "crm/alice"})
st.remember("alice's phone is 0900 111 222", key="alice::phone",
            object="0900 111 222", source={"doc": "crm/alice"})

print("=== the ordinary caller: erase a subject, nothing external registered ===")
res = st.forget_subject("crm/alice", request_id="DSAR-1", basis="GDPR Art.17")
print("  forget_subject ->", json.dumps({k: v for k, v in res.items() if k != "ids"},
                                        ensure_ascii=False, default=str)[:300])
print()
print("  Does the result mention external/unregistered coverage at all?")
blob = json.dumps(res, default=str).lower()
hits = [w for w in ("manifest", "target", "external", "coverage", "unregistered", "incomplete") if w in blob]
print("   ", hits or "NO -- the word 'external', 'target', 'coverage' appears nowhere in the result")

print("\n=== the compliance surfaces a DPO would read ===")
for name in ("erasure_certificate", "governance_report", "erasure_report"):
    fn = getattr(st, name, None)
    if not fn:
        print(f"  {name}: not present")
        continue
    try:
        out = fn() if name != "erasure_certificate" else fn("crm/alice")
    except TypeError:
        try:
            out = fn()
        except Exception as e:
            print(f"  {name}: raised {type(e).__name__}"); continue
    except Exception as e:
        print(f"  {name}: raised {type(e).__name__}: {e}"); continue
    s = json.dumps(out, default=str, ensure_ascii=False)
    warns = [w for w in ("external", "unregistered", "not covered", "coverage", "manifest") if w in s.lower()]
    print(f"  {name}: {len(s)} chars; coverage words present: {warns or 'NONE'}")
    if "scope" in s.lower():
        for k in ("scope", "limits"):
            if isinstance(out, dict) and k in out:
                print(f"     {k}: {str(out[k])[:180]}")

print("\n=== VERDICT ===")
print("  If the erasure result and the compliance surfaces never mention that ZERO external targets were")
print("  registered, then the default answer to 'did we erase this person' is a clean yes about a surface")
print("  the library did not look at -- and the fix belongs in the product, not in a comparison page.")
