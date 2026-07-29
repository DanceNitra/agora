"""Every verdict-returning surface, handed input it structurally cannot examine.

The owner's standing instruction: of 28 audit findings, six were one class -- a function whose only job is
to refuse returned True about input it never examined -- on exactly the surfaces the README and
docs/AI_ACT.md name as the moat. "If a seventh appears, look for it there."

Seven have appeared since, all in the erasure family, and that family now sweeps clean. So the question
moves to the OTHER verdict surfaces: verify_writes, verify_claim, verify_consistency, verify_attribution,
check_conflict, selection_integrity, index_coherence, check_self_narration, verify_witness.

The test is not "does it work". It is: give it something it cannot possibly know about, and see whether it
says so or says fine. A verdict surface has three honest answers -- yes, no, and "I could not look" -- and
the defect is always the third collapsing into the first.

Read-only. Reports; fixes nothing.
"""
import inspect
import json
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

VERDICT_SURFACES = [
    "verify_writes", "verify_claim", "verify_consistency", "verify_attribution",
    "check_conflict", "selection_integrity", "index_coherence", "check_self_narration",
    "verify_witness", "verify_audit_bundle", "verify_cosigned_anchor", "compliance_check",
    "detect_split_view", "contradictions", "erasure_audit",
]

print("=== which verdict surfaces exist, and what do they return? ===")
present = []
for name in VERDICT_SURFACES:
    fn = getattr(Inspeximus, name, None)
    if fn is None:
        print(f"   {name:24s} ABSENT")
        continue
    params = [p for p in inspect.signature(fn).parameters if p != "self"]
    present.append(name)
    print(f"   {name:24s} ({', '.join(params) or 'no args'})")

print("\n=== the empty-store question: does a surface with NOTHING to inspect say so? ===")
print("   A store with no records cannot support any claim. Anything that returns a clean")
print("   boolean here is answering about input it does not have.\n")
empty = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "e.json"), receipts=True)
for name in present:
    fn = getattr(empty, name, None)
    try:
        sig = inspect.signature(getattr(Inspeximus, name))
        required = [p for p, v in sig.parameters.items()
                    if p != "self" and v.default is inspect.Parameter.empty
                    and v.kind not in (v.VAR_POSITIONAL, v.VAR_KEYWORD)]
        out = fn(*(["the sky is green"] * len(required)))
    except Exception as e:
        print(f"   {name:24s} raised {type(e).__name__}: {str(e)[:70]}")
        continue
    blob = json.dumps(out, default=str)
    # Does the answer DISTINGUISH "clean" from "could not look"?
    says_unknown = any(w in blob.lower() for w in
                       ("unaudited", "not_computable", "insufficient", "unknown", "no_evidence",
                        "unverifiable", "uninspected", "no_data", "unregistered", "coverage"))
    print(f"   {name:24s} -> {blob[:110]}")
    print(f"   {'':24s}    distinguishes 'could not look': {says_unknown}")

print("\n=== the un-inspectable-claim question ===")
print("   A store holding ONE unrelated fact, asked to verify a claim about something else entirely.")
print("   The honest answers are 'no' or 'I have no evidence'. 'True' would be the seventh finding.\n")
m = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "f.json"), receipts=True)
m.remember("the deploy region is frankfurt", key="cfg::region", object="frankfurt")
for name, args in (("verify_claim", ("alice was born in 1987",)),
                   ("check_conflict", ("the deploy region is tokyo",)),
                   ("verify_consistency", ()),
                   ("selection_integrity", ()),
                   ("index_coherence", ())):
    fn = getattr(m, name, None)
    if fn is None:
        continue
    try:
        out = fn(*args)
    except Exception as e:
        print(f"   {name:22s} raised {type(e).__name__}: {str(e)[:70]}")
        continue
    print(f"   {name:22s} -> {json.dumps(out, default=str)[:150]}")

print("\n-> Read each line as: could this surface have returned a DIFFERENT answer, given what it")
print("   was actually handed? Where the answer is no, the verdict is a constant wearing a verdict's")
print("   clothes, and that is the shape worth chasing next.")
