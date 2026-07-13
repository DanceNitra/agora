"""governance_sufficiency_probe.py — does a memory correction/erasure RECEIPT actually answer the auditor's
questions, or just look like it does?

Lead 2 of the 2026-07-12 world scan, and a self-incriminating Crucible-shaped test. "Governance-evidence
sufficiency" (can an INDEPENDENT auditor reconstruct who/what/when/on-what-authority/on-what-basis, and verify
it wasn't forged, from ONLY the emitted receipt bytes) is DIFFERENT from "primitive presence" (does the API
expose revert/retract/erase/audit at all). mnemo implements all the primitives; this probe asks whether its
receipt is SUFFICIENT — and leads with where it is NOT.

We run one real correction+erasure lifecycle through mnemo's actual primitives, capture the exact receipt
bytes an auditor would get (governance_report + the hash-chained write/tombstone receipts), and score them
against an 8-question DEMM-style rubric (arXiv 2606.20634, generalized to a memory store). Each question is a
STRICT, defensible predicate over the bytes — deterministic, no LLM, no judge variance. We deliberately write
the predicates to catch the questions mnemo FAILS, not to flatter it.

Falsifier: if mnemo scores 8/8, presence == sufficiency and there is nothing to publish (the leaderboard would
collapse to a feature matrix). The finding is the GAP: the primitives are present but the receipt does not, on
its own, answer every governance question — specifically authority-binding, decision-basis, and
external-anchorability (mnemo's own governance_report docstring concedes the third).

Run: python mnemo/probes/governance_sufficiency_probe.py   (deterministic, cloud-free)
Part of Agora / mnemo (MIT).
"""
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mnemo import Mnemo, new_receipt_keypair, new_source_keypair, sign_erasure, erasure_challenge  # noqa: E402
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey as _PK
except Exception:
    _PK = None


def run_lifecycle():
    """assert a fact -> launder a derived fact -> correct the root -> retract lineage -> rederive -> erase a
    subject. Returns the exact receipt bytes an auditor is handed (nothing else)."""
    fd, p = tempfile.mkstemp(suffix=".json", prefix="gov_"); os.close(fd)
    for suf in ("", ".receipts.json"):
        try:
            os.remove(p + suf)
        except OSError:
            pass
    sk, pk = new_receipt_keypair()
    m = Mnemo(path=p, receipts=True, receipt_key=sk, receipt_pubkey=pk)

    root = m.remember("the billing region is us-east", key="billing::region", object="us-east",
                      source={"doc": "ops"})
    m.remember("the billing region is us-east, so backups go to us-east",
               derived_from=[root], source={"doc": "ops"})
    m.remember("the billing region is eu-west", key="billing::region", object="eu-west",
               source={"doc": "ops"})                    # correction
    m.retract_lineage("ops", reason="region_corrected")
    m.rederive("ops", key="billing::region")
    # right-to-erasure act, bound to an authenticated principal (AUTHORITY) + a decision basis (BASIS)
    p_sk, p_pk = new_source_keypair()
    req = "dsar-2026-0042"
    authz = sign_erasure(p_sk, "ops", req)
    m.forget_subject("ops", request_id=req, basis="GDPR Art.17 erasure request; verified data subject 'ops'",
                     authorized_by=p_pk, authorization=authz)

    report = m.governance_report(expected_pubkey=pk)
    receipts = list(m._receipts)
    tombstones = list(m._tombstones)
    # the auditor is handed ONLY these bytes (no store internals, no source code)
    bytes_out = {"governance_report": report, "write_receipts": receipts, "tombstones": tombstones}
    for suf in ("", ".receipts.json"):
        try:
            os.remove(p + suf)
        except OSError:
            pass
    return bytes_out, pk


def score(bytes_out, pk):
    """8 governance questions, each a strict predicate over the receipt bytes ALONE. Returns list of
    (question, passed, note)."""
    rep = bytes_out["governance_report"]
    rcpts = bytes_out["write_receipts"]
    tombs = bytes_out["tombstones"]
    Q = []

    # 1. WHAT — which specific records were changed/erased, by id?
    ids = [mid for r in rep.get("by_request", {}).values() for mid in r.get("memory_ids", [])]
    Q.append(("WHAT: specific records identified by id", bool(ids),
              f"{len(ids)} memory ids in by_request"))

    # 2. WHEN — is each act timestamped?
    when = bool(rcpts) and all("ts" in r for r in rcpts) and (not tombs or all("ts" in t for t in tombs))
    Q.append(("WHEN: every act carries a timestamp", when, "ts present on receipts + tombstones"))

    # 3. TAMPER-EVIDENCE — is the history verifiably unaltered (hash chain checks out)?
    Q.append(("TAMPER-EVIDENCE: chain verifies (no silent edit)", bool(rep.get("proof", {}).get("verified")),
              "governance_report.proof.verified over write+tombstone chains"))

    # 4. COMPLETENESS — can a silently dropped/inserted record be detected (chained prev-links)?
    complete = bool(rcpts) and all("prev" in r and "hash" in r for r in rcpts) \
        and (not tombs or all("prev" in t and "hash" in t for t in tombs))
    Q.append(("COMPLETENESS: drops/inserts detectable (prev-linked)", complete,
              "every receipt/tombstone has prev+hash"))

    # 5. WHO / AUTHORITY — is each act bound to an AUTHENTICATED PRINCIPAL, beyond a free-text id? We do NOT
    #    trust presence of a field; the auditor VERIFIES the principal's Ed25519 signature over the erasure
    #    request. A free-text request_id or an unverifiable string would still FAIL here.
    def _authority_ok(t):
        a = t.get("auth") or {}
        pk, sig = a.get("authorized_by"), a.get("authorization")
        if not (pk and sig and _PK):
            return False
        try:
            _PK.from_public_bytes(bytes.fromhex(pk)).verify(
                bytes.fromhex(sig), erasure_challenge("ops", t.get("request_id")).encode())
            return True
        except Exception:
            return False
    authority_bound = bool(tombs) and all(_authority_ok(t) for t in tombs)
    Q.append(("AUTHORITY: act bound to an authenticated principal", authority_bound,
              "each tombstone carries authorized_by (principal pubkey) + a valid Ed25519 authorization over the "
              "erasure request — auditor-verified, not a free string" if authority_bound
              else "no verifiable principal signature binds the act"))

    # 6. DECISION BASIS — is the reason/evidence the change was made recorded in the auditor-facing bytes?
    basis_in_bytes = bool(tombs) and all((t.get("auth") or {}).get("basis") for t in tombs)
    Q.append(("BASIS: decision basis / evidence recorded in the receipt", basis_in_bytes,
              "each tombstone's auth.basis records why the record was erased" if basis_in_bytes
              else "the decision basis is not in the auditor-facing receipt bytes"))

    # 7. EXTERNAL ANCHORABILITY — can the auditor verify WITHOUT trusting the operator who holds the key?
    #    The scope text itself concedes the operator can forge the chain; there is no external anchor
    #    (no published chain-head / inclusion proof) in the bytes. EXPECTED TO FAIL.
    anc = (rep.get("proof") or {}).get("anchor") or {}
    anchored = bool(anc.get("sth_hash") and ("writes_tip" in anc))  # CT-style externally-witnessable tree head
    Q.append(("ANCHORABILITY: verifiable without trusting the key-holder", anchored,
              "governance_report.proof.anchor = a CT-style signed tree head (witness it out of band; "
              "verify_consistency() then catches a key-holder rewrite)" if anchored
              else "no external chain-head anchor / inclusion proof in the bytes"))

    # 8. SCOPE HONESTY — does the receipt state what it does NOT certify (act vs content, store-only)?
    scope = rep.get("scope", "")
    scope_ok = bool(scope) and ("NOT" in scope or "not" in scope) and "content" in scope.lower()
    Q.append(("SCOPE HONESTY: states what it does NOT certify", scope_ok,
              "governance_report.scope disclaims content/act and store-boundary"))

    return Q


def main():
    bytes_out, pk = run_lifecycle()
    Q = score(bytes_out, pk)
    passed = sum(1 for _, ok, _ in Q if ok)
    print("=== GOVERNANCE-EVIDENCE SUFFICIENCY (mnemo self-score) ===")
    print("8-question DEMM-style rubric (arXiv 2606.20634) over the receipt bytes an auditor actually gets.")
    print("deterministic; predicates written to catch failures, not flatter. Leads with where mnemo FAILS.\n")
    for q, ok, note in Q:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {q}")
        print(f"         -> {note}")
    print()
    print(f"SUFFICIENCY SCORE: {passed}/8")
    fails = [q.split(':')[0] for q, ok, _ in Q if not ok]
    if passed == 8:
        print("VERDICT: KILL — presence == sufficiency; the receipt answers every governance question, nothing to publish.")
    else:
        print(f"VERDICT: LIVE — gap confirmed. mnemo implements the primitives but its receipt FAILS on: "
              f"{', '.join(fails)}.")
        print("  Sufficiency is NOT predicted by presence — the self-incriminating, Crucible-shaped result. The")
        print("  three fails are concrete product gaps: emit the decision basis into the receipt; bind the request")
        print("  to an authenticated principal; publish an external chain-head anchor (Certificate-Transparency-style).")
    # persist the exact bytes scored, for reproducibility
    out = os.path.join(os.path.dirname(__file__), "governance_sufficiency_bytes.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(bytes_out, f, indent=1, default=str)
    print(f"\n(scored bytes written to {os.path.basename(out)})")


if __name__ == "__main__":
    main()
