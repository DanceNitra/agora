"""Would `erasure_audit` have caught the routed-correction residue — or did it report clean?

`erasure_audit` exists to answer the question an operator hits after a DSAR: did anything survive that
still carries the erased material? Last night's finding is exactly that shape — a correction written
through `route()` survived the subject's erasure while holding their CURRENT value.

So the surface built to catch this had its chance. If it reported clean, then the defect had TWO layers:
the residue itself, and an audit that certified its absence. That is the class this whole month has been
about, and it would mean the audit's own honest-scope note ("it reads metadata the writer supplied, so it
cannot detect what was never declared") was doing more work than anyone realised — the routed correction
declared nothing, so it was invisible by construction.

Measured on the PUBLISHED 1.87.0 wheel, which still has the route defect (the fix is unreleased), against
the fixed local HEAD. Read-only.
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def probe(label, root):
    import importlib.util
    mod_path = os.path.join(root, "inspeximus", "__init__.py")
    if not os.path.exists(mod_path):
        print(f"   {label}: no package at {root}")
        return
    spec = importlib.util.spec_from_file_location(
        f"insp_{abs(hash(root))}", mod_path,
        submodule_search_locations=[os.path.dirname(mod_path)])
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    try:
        spec.loader.exec_module(m)
        S = m.Inspeximus
        st = S(path=os.path.join(tempfile.mkdtemp(), "s.json"), receipts=True)
        st.remember("alice home address is 5 Elm St", key="alice::addr", object="5 Elm St",
                    source={"doc": "hr/alice"})
        st.route("actually alice moved to 9 Oak Ave", key="alice::addr", object="9 Oak Ave")
        res = st.forget_subject("hr/alice", request_id="DSAR-1", basis="art17")
        blob = " ".join((r.get("text") or "") + str(r.get("object") or "") for r in st.items)
        survived = "9 Oak" in blob

        aud = st.erasure_audit("hr/alice")
        # `values=` is the heuristic arm: give it the erased string and see whether that changes anything.
        aud_v = st.erasure_audit("hr/alice", values=["9 Oak Ave", "5 Elm St"])
        print(f"   {label}")
        print(f"      version              {getattr(m, '__version__', '?')}")
        print(f"      erased               {res['erased']}")
        print(f"      CURRENT value left   {survived}")
        print(f"      audit verdict        {aud['verdict']!r}   residue items: {len(aud['residue'])}")
        print(f"      audit WITH values=   {aud_v['verdict']!r}  "
              f"advisory: {[a.get('kind') for a in aud_v.get('advisory') or []]}")
        print(f"      coverage             {aud['coverage']}")
        return survived, aud["verdict"]
    except Exception as e:
        print(f"   {label}: {type(e).__name__}: {str(e)[:120]}")
    finally:
        sys.modules.pop(spec.name, None)


print("=== does our own audit surface catch the residue it exists to catch? ===\n")
pub = None
for d in sorted(os.listdir(os.environ.get("TEMP", "."))):
    if d.startswith("verify187_"):
        cand = os.path.join(os.environ["TEMP"], d, "x")
        if os.path.exists(os.path.join(cand, "inspeximus", "__init__.py")):
            pub = cand
if pub:
    probe("PUBLISHED 1.87.0 (route defect present)", pub)
else:
    print("   published wheel not extracted locally; skipping that arm")
print()
probe("LOCAL HEAD (route fix applied)", r"C:\Users\Danculus\inspeximus-repo")

print()
print("-> On the defective build, if the CURRENT value survived AND the audit did not report residue,")
print("   then the audit certified an erasure that left the live data behind. Its honest-scope note")
print("   already says it cannot see what was never declared -- this measures what that costs in the")
print("   one case the whole surface exists for.")
