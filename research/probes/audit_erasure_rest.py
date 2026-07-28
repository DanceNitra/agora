"""The rest of the erasure audit: does `coverage` describe the run, or describe a hope?

Four findings left, all on the coverage block that shipped today and is now on every erasure path. Coverage
is the field an auditor reads to decide whether an obligation is discharged, so a wrong value here is not
cosmetic -- it is the difference between "we erased what we could reach" and "we erased everything".

  C1  `note` vs `external_targets`. The note says "no external erasure target is registered". Does it still
      say that when targets ARE registered? A note that hardcodes the empty case contradicts its own
      sibling field the moment the case changes.
  C2  `confirmed` counts the SELF target. If this store registers itself (or a target reports on itself),
      `confirmed` counts an attestation the store made about itself and presents it as independent.
  C3  `complete` when a target says NOT absent. The whole point is that a target can dissent. Does a
      dissenting target actually stop `complete`, or is `complete` computed before anyone answers?
  C4  `forget_pii` / `retention` cannot carry `authorized_by` / `authorization`. Erasure paths that accept
      no authority produce tombstones that `_deliberate()` cannot distinguish from housekeeping eviction --
      so a real Art.17 erasure through those paths is filed as a space reclaim.

Each arm has a control that must come out the other way.
"""
import inspect
import json
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


def store(**kw):
    return Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), receipts=True, **kw)


class Target:
    """A registered external erasure target that answers honestly about itself."""

    def __init__(self, name, absent=True):
        self.name = name
        self._absent = absent
        self.calls = []

    def erase(self, ids=None, subject=None, **kw):
        self.calls.append(("erase", ids, subject))
        return {"erased": len(ids or []), "verified_absent": self._absent}

    def still_recoverable(self, **kw):
        return not self._absent


print("=== C1: does `note` still claim nothing is registered once targets ARE registered? ===")
for label, targets in (("none registered", []),
                       ("one registered", [Target("vector-index")]),
                       ("one DISSENTING", [Target("vector-index", absent=False)])):
    st = store()
    reg = getattr(st, "register_erasure_target", None)
    if reg is None:
        print("   register_erasure_target: MISSING -- cannot measure C1/C2/C3")
        break
    for t in targets:
        try:
            reg(t)
        except Exception as e:
            print(f"   register raised {type(e).__name__}: {str(e)[:90]}")
    st.remember("alice salary 92000", key="p", object="92000", source={"doc": "hr/alice"})
    try:
        res = st.forget_subject("hr/alice", request_id="r", basis="art17")
    except Exception as e:
        print(f"   {label:18s} forget raised {type(e).__name__}: {str(e)[:110]}")
        continue
    cov = res.get("coverage") or {}
    note = (cov.get("note") or "")
    print(f"   {label:18s} external_targets={cov.get('external_targets')} "
          f"confirmed={cov.get('confirmed')} complete={cov.get('complete')} "
          f"unregistered={cov.get('unregistered')}")
    print(f"                      note says 'no external erasure target is registered'? "
          f"{'no external erasure target is registered' in note}")
    if cov.get("attested_by_targets") is not None:
        print(f"                      attested_by_targets={cov.get('attested_by_targets')}")
print("   -> the 'none' arm may say it; the other two must NOT. And the DISSENTING arm must not report")
print("      complete=True -- a target that says the data is still recoverable is the whole mechanism.\n")

print("=== C4: can the other erasure paths carry an authority at all? ===")
st = store()
for name in ("forget_subject", "forget_pii", "forget", "retention"):
    fn = getattr(st, name, None)
    if fn is None:
        print(f"   {name:15s} MISSING")
        continue
    try:
        params = list(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        params = ["<unavailable>"]
    auth = [p for p in params if p in ("authorized_by", "authorization", "basis", "request_id")]
    print(f"   {name:15s} authority params: {auth or 'NONE'}")
    print(f"                   all params: {params}")
print("   -> a path with no request_id and no basis produces a tombstone that _deliberate() reads as")
print("      housekeeping, so a real Art.17 erasure through it is filed as a space reclaim.\n")

print("=== C4b: measured, not inferred -- is such an erasure invisible to the audit? ===")
st2 = store()
st2.remember("bob ssn 123-45-6789", key="pii", object="123-45-6789", source={"doc": "hr/bob"})
fn = getattr(st2, "forget_pii", None)
if fn is None:
    print("   forget_pii MISSING")
else:
    try:
        out = fn()
        print(f"   forget_pii() -> {json.dumps(out, default=str)[:200]}")
    except Exception as e:
        print(f"   forget_pii raised {type(e).__name__}: {str(e)[:110]}")
    tombs = getattr(st2, "_tombstones", []) or []
    for t in tombs:
        print(f"   tombstone: request_id={t.get('request_id')!r} auth={t.get('auth')!r}")
    print(f"   erasure_audit verdict: {st2.erasure_audit('hr/bob').get('verdict')!r}")
print("   -> CONTROL: the same erasure through forget_subject(request_id=..., basis='art17') must be")
print("      distinguishable from this one, else the distinction the audit rests on does not exist.")
st3 = store()
st3.remember("bob ssn 123-45-6789", key="pii", object="123-45-6789", source={"doc": "hr/bob"})
st3.forget_subject("hr/bob", request_id="dsar-9", basis="art17")
for t in (getattr(st3, "_tombstones", []) or []):
    print(f"   control tombstone: request_id={t.get('request_id')!r} auth={t.get('auth')!r}")
