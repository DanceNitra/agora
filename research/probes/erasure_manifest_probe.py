"""erasure_manifest_probe.py — the cross-store deletion manifest, honest by construction.

Demonstrates deletion_manifest.DeletionManifest across two ErasureTargets — a mnemo memory store and an app-side
vector index — for a right-to-erasure request. The point the gate demanded: the manifest must SURFACE the
fan-out leak (erasure_fanout_probe measured index_residue 1.00), not hide it. So:

  Scenario A (naive app index that does NOT purge on the store delete): manifest.complete == False, and the
             residual target is named — an honest 'you did NOT actually erase; the vector index still has it'.
  Scenario B (the app index IS wired to purge): manifest.complete == True — erasure verified across BOTH stores.

Plus: the manifest is hash-chained + (optionally) signed, and verify() catches a tampered entry.

Run: python research/probes/erasure_manifest_probe.py   (cloud-free, deterministic)
Part of Agora / mnemo (MIT).
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus, new_receipt_keypair  # noqa: E402
from deletion_manifest import DeletionManifest, ErasureTarget  # noqa: E402


class MnemoTarget(ErasureTarget):
    name = "mnemo-store"

    def __init__(self, store: Inspeximus):
        self.m = store

    def erase(self, subject):
        return {"erased": self.m.forget_subject(subject, request_id=f"dsar-{subject}",
                                                basis="GDPR Art.17 erasure request")["erased"]}

    def still_recoverable(self, subject, values):
        active = " ".join((r.get("text") or "") for r in self.m.items if r.get("status") == "active").lower()
        return any(v.lower() in active for v in values)


class VectorIndexTarget(ErasureTarget):
    """A stand-in for the app's retrieval vector index (text kept alongside vectors). `purges` toggles whether
    the app wired the index into the erasure flow (True) or forgot it (False = the real-world default leak)."""
    name = "app-vector-index"

    def __init__(self, purges: bool):
        self.rows = []          # (subject, text)
        self.purges = purges

    def add(self, subject, text):
        self.rows.append((subject, text))

    def erase(self, subject):
        if not self.purges:
            return {"erased": 0}                                  # the leak: store delete never reached here
        before = len(self.rows)
        self.rows = [(s, t) for (s, t) in self.rows if s != subject]
        return {"erased": before - len(self.rows)}

    def still_recoverable(self, subject, values):
        blob = " ".join(t for (s, t) in self.rows if s == subject).lower()
        return any(v.lower() in blob for v in values)


def build(purges_index):
    fd, path = tempfile.mkstemp(suffix=".json", prefix="man_"); os.close(fd)
    for suf in ("", ".receipts.json"):
        try: os.remove(path + suf)
        except OSError: pass
    m = Inspeximus(path=path, receipts=True)
    idx = VectorIndexTarget(purges=purges_index)
    subj, value = "alice-42", "type-1 diabetes"
    root = m.remember(f"Alice's medical condition is {value}.", key=f"{subj}::cond", object=value, source={"doc": subj})
    m.remember(f"derived: {value} (context)", derived_from=[root], source={"doc": subj})
    idx.add(subj, f"Alice's medical condition is {value}.")
    sk, pk = new_receipt_keypair()
    man = DeletionManifest(sign_sk_hex=sk, pubkey_hex=pk).register(MnemoTarget(m)).register(idx)
    report = man.execute(subj, values=[value], request_id=f"dsar-{subj}",
                         basis="GDPR Art.17", authorized_by=pk)
    ok, probs = man.verify(report)
    for suf in ("", ".receipts.json"):
        try: os.remove(path + suf)
        except OSError: pass
    return report, man, ok, probs


def main():
    print("=== CROSS-STORE DELETION MANIFEST (honest by construction) ===\n")

    rA, _, okA, _ = build(purges_index=False)
    print("Scenario A — app vector index NOT wired to the erasure flow (the common real-world default):")
    for e in rA["entries"]:
        print(f"    {e['target']:<18} erased={e['erased']}  still_recoverable={e['still_recoverable']}  "
              f"verified_absent={e['verified_absent']}")
    print(f"  -> complete = {rA['complete']}   residual_targets = {rA['residual_targets']}")
    print(f"  -> HONEST: the manifest does NOT claim erasure; it names the store that still has the data.\n")

    rB, manB, okB, _ = build(purges_index=True)
    print("Scenario B — app vector index IS wired to purge:")
    for e in rB["entries"]:
        print(f"    {e['target']:<18} erased={e['erased']}  still_recoverable={e['still_recoverable']}  "
              f"verified_absent={e['verified_absent']}")
    print(f"  -> complete = {rB['complete']}   residual_targets = {rB['residual_targets']}\n")

    # tamper-evidence: flip a verified_absent claim and re-verify
    rT = {k: (list(v) if isinstance(v, list) else v) for k, v in rA.items()}
    rT["entries"] = [dict(e) for e in rA["entries"]]
    rT["entries"][1]["verified_absent"] = True  # forge 'we erased it' on the LEAKING index (was False)
    okT, probsT = manB.verify(rT)               # verify() is stateless (recomputes from the dict)
    print(f"Tamper test — forge verified_absent=True on the leaking index entry: verify -> ok={okT}  "
          f"{'CAUGHT: ' + probsT[0] if not okT else 'MISSED (FAIL)'}\n")

    passed = (rA["complete"] is False and rA["residual_targets"] == ["app-vector-index"]
              and rB["complete"] is True and okA and okB and not okT)
    if passed:
        print("VERDICT: PASS — the manifest is honest (Scenario A reports INCOMPLETE + names the leaking store,")
        print("  not a false 'deleted'), useful (Scenario B verifies erasure across BOTH stores), and")
        print("  tamper-evident (a forged claim fails verify). This is the cross-store deliverable a DPO needs:")
        print("  it makes the fan-out visible and auditable instead of certifying one copy of many.")
    else:
        print("VERDICT: FAIL — manifest did not behave as specified; do not ship.")


if __name__ == "__main__":
    main()
