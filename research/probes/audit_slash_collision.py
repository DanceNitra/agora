"""Does an IRREVERSIBLE act land on the party it names, or on everyone sharing their host?

The ghost arm came back clean (`slash('crm/nobody-here')` -> slashed 0), but that is the easy half and I
did not measure the one that matters: naming a REAL subject and seeing who else goes down with them. The
docstring of `_source_expansion_collisions` already states the answer as history --

    caught on 'crm.example.com/alice', `slash` forfeited 'crm.example.com/bob' too (measured: slashed 2,
    Bob's standing inverted to bad). Same lossy-key-as-selector defect as the erasure paths, one lever over.

-- so the collision is known. What is NOT established is what the code does about it now: REFUSE, refuse
unless overridden, or proceed while merely reporting the collateral. For erasure the answer is refuse-by-
default with an `exact=True` escape. Slashing is worse than erasing in one specific way: erasure has a
dry_run and a manifest, and standing that was forfeited by mistake has no receipt to walk back.

Arms, each with the control that separates "narrow" from "does nothing":
  S1  slash a subject who shares a host with a stranger  -> does the stranger's standing move?
  S2  slash a subject who shares a host with NOBODY      -> must still work (else narrowing broke it)
  S3  same two arms for spend_irreversible
"""
import json
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


def store():
    return Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), receipts=True)


def shared_host_store():
    st = store()
    st.remember("alice invoice 100", key="i::alice", object="100", source={"doc": "crm.example.com/alice"})
    st.remember("bob invoice 200", key="i::bob", object="200", source={"doc": "crm.example.com/bob"})
    return st


def standing(st):
    """Whatever the store exposes as per-source standing, without assuming a field name."""
    for name in ("standing", "source_standing", "reputation"):
        fn = getattr(st, name, None)
        if callable(fn):
            try:
                return name, fn()
            except Exception:
                pass
        elif fn is not None:
            return name, fn
    return None, None


print("=== S1: slash a subject who shares a host with a stranger ===")
st = shared_host_store()
name, before = standing(st)
try:
    out = st.slash("crm.example.com/alice")
    print(f"   slash('crm.example.com/alice') -> {json.dumps(out, default=str)[:300]}")
    n = out.get("slashed")
    srcs = out.get("sources") or []
    print(f"   slashed={n}  sources={srcs}")
    if n and n > 1:
        print("   -> COLLATERAL: more than the named subject's records were forfeited.")
    bob_hit = any("bob" in str(s) for s in srcs) or any(
        "bob" in (r.get("text") or "") for r in st.items
        if (r.get("meta") or {}).get("slashed") or r.get("status") == "slashed")
    print(f"   bob reachable in the outcome? {bob_hit}")
except Exception as e:
    print(f"   raised {type(e).__name__}: {str(e)[:160]}")
_, after = standing(st)
print(f"   standing surface={name!r} changed={before != after}\n")

print("=== S1b CONTROL: does it REFUSE, or proceed and merely report? ===")
st2 = shared_host_store()
try:
    out = st2.slash("crm.example.com/alice")
    refused = bool(out.get("refused") or out.get("error") or out.get("collisions"))
    print(f"   keys returned: {sorted(out.keys())}")
    print(f"   refusal/collision signal present: {refused}")
    print("   -> erasure refuses by default on this exact ambiguity and offers exact=True.")
    print("      If slash only REPORTS, an irreversible act is the one place with the weaker guard.")
except Exception as e:
    print(f"   raised {type(e).__name__}: {str(e)[:160]}")

print("\n=== S2 CONTROL: a subject sharing a host with nobody must still be slashable ===")
st3 = store()
st3.remember("erin invoice 300", key="i::erin", object="300", source={"doc": "vendor-erin"})
try:
    out = st3.slash("vendor-erin")
    print(f"   slash('vendor-erin') -> {json.dumps(out, default=str)[:200]}")
    print("   -> must be non-zero. A fix that made everything refuse would pass S1 and break the feature.")
except Exception as e:
    print(f"   raised {type(e).__name__}: {str(e)[:160]}")

print("\n=== S3: spend_irreversible, same two arms ===")
for label, subj, st4 in (("shared host", "crm.example.com/alice", shared_host_store()),
                         ("sole tenant", "vendor-erin", None)):
    if st4 is None:
        st4 = store()
        st4.remember("erin invoice 300", key="i::erin", object="300", source={"doc": "vendor-erin"})
    try:
        out = st4.spend_irreversible(subj)
        print(f"   {label:12s} spend_irreversible({subj!r}) -> {json.dumps(out, default=str)[:220]}")
    except Exception as e:
        print(f"   {label:12s} raised {type(e).__name__}: {str(e)[:120]}")
print("   -> the two arms must differ, or the call is not resolving the subject at all.")
