"""Is `coverage.confirmed` comparable to `coverage.external_targets`, or does it count the store itself?

The first attempt at this measurement was WRONG and its own controls hid it: my fake target declared
`still_recoverable(self, **kw)` while the manifest calls it positionally as
`still_recoverable(subject, values)`, so the adapter raised in EVERY arm and was recorded as
`recoverable=True, err=...`. Both arms then came back identical -- which I nearly read as "dissent does not
reach coverage", when what it actually showed was that I had measured nothing. Getting the same number from
two arms is only evidence when the arms genuinely differ.

Re-run with the real protocol shape. The question that survives is C2: a manifest always registers a
`_SelfTarget` alongside the app's targets, so `confirmed` counts this store's own attestation about itself.
Printed next to `external_targets`, an auditor reads `external_targets: 1, confirmed: 1` as "the external
store confirmed" -- which can be true while the external store erased nothing, errored, or dissented.
"""
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402


class Honest:
    """Implements the protocol as documented: erase(subject), still_recoverable(subject, values)."""

    def __init__(self, name, recoverable):
        self.name = name
        self._recoverable = recoverable

    def erase(self, subject):
        return {"erased": 1}

    def still_recoverable(self, subject, values):
        return self._recoverable


class WrongSignature:
    """The mistake this probe was rebuilt to avoid -- kept as an ARM, because a real integrator will
    ship this and the manifest must record it as a leak rather than silently as a pass."""

    name = "broken-adapter"

    def erase(self, subject):
        return {"erased": 1}

    def still_recoverable(self, **kw):
        return False


def run(label, targets):
    st = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), receipts=True)
    for t in targets:
        st.register_erasure_target(t)
    st.remember("alice salary 92000", key="p", object="92000", source={"doc": "hr/alice"})
    res = st.forget_subject("hr/alice", request_id="r", basis="art17", values=["92000"])
    cov = res.get("coverage") or {}
    print(f"   {label:30s} external_targets={cov.get('external_targets')} "
          f"confirmed={cov.get('confirmed')} complete={cov.get('complete')} "
          f"unconfirmed={cov.get('unconfirmed')}")
    return cov


print("=== C2/C3: what does `confirmed` count, and does a dissent stop `complete`? ===")
run("no external target", [])
run("1 honest, data absent", [Honest("vector-index", False)])
run("1 honest, DISSENTS", [Honest("vector-index", True)])
run("1 broken adapter (raises)", [WrongSignature()])
run("2 targets, 1 dissents", [Honest("a", False), Honest("b", True)])
print()
print("   -> `complete` must be False in every arm where a target dissented or errored: that half is the")
print("      mechanism working. The question is `confirmed`: if it reads 1 when ONE external target was")
print("      registered and that target dissented, the number counts the store's own self-attestation")
print("      and sits next to external_targets as though it were comparable to it.")
