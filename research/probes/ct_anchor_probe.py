"""ct_anchor_probe.py — does an EXTERNAL Certificate-Transparency-style anchor detect an operator who rewrites
history while holding the receipt key?

inspeximus's governance_report docstring concedes the one hole verify_writes cannot close: "the operator who holds
receipt_key can forge tombstones too — anchor the chain head externally for operator-adversarial audit." The
new anchor() / verify_consistency() close it (RFC 6962 model: an untrusted log + external witnesses + a
consistency proof). This probe proves the boundary is real, not decorative:

  1. append-only extension          -> verify_consistency PASSES (a witnessed prefix still holds).
  2. operator rewrites history AND re-chains it so it verifies INTERNALLY (verify_writes = OK) ->
     verify_writes still passes (that is exactly the attack it cannot catch), but verify_consistency FAILS
     against a previously-witnessed anchor (fork detected). This is the whole point.
  3. operator rolls the log back (truncates) -> verify_consistency FAILS (log shrank).

Run: python research/probes/ct_anchor_probe.py   (deterministic, no LLM, no network)
Part of Agora / inspeximus (MIT).
"""
import os
import sys
import copy
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus, _sha256_hex, _canon, _GENESIS  # noqa: E402


def _store():
    fd, p = tempfile.mkstemp(suffix=".json", prefix="cta_"); os.close(fd)
    for suf in ("", ".receipts.json"):
        try:
            os.remove(p + suf)
        except OSError:
            pass
    return Inspeximus(path=p, receipts=True), p


def operator_forge(m, mem_index, new_text):
    """Simulate an operator WITH the key rewriting a stored memory and RE-CHAINING every receipt so the whole
    write history verifies internally (the sophisticated forge verify_writes alone cannot catch)."""
    m.items[mem_index]["text"] = new_text
    by_id = {it["id"]: it for it in m.items}
    prev = _GENESIS
    for r in m._receipts:
        rec = by_id.get(r["memory_id"])
        if rec is not None:
            r["commit"] = m._write_commit(rec)          # recompute the content commitment
        r["prev"] = prev
        r["hash"] = _sha256_hex(_canon({k: r.get(k) for k in ("seq", "ts", "memory_id", "commit", "prev")}))
        prev = r["hash"]


def main():
    print("=== CT-STYLE EXTERNAL ANCHOR: catch an operator who rewrites history holding the key ===\n")

    # --- Case 1: append-only extension stays consistent ---
    m, _ = _store()
    for i in range(4):
        m.remember(f"fact {i}: the region is r{i}", key=f"k{i}", object=f"r{i}")
    a1 = m.anchor()                                     # auditor witnesses this out of band
    for i in range(4, 7):
        m.remember(f"fact {i}: the region is r{i}", key=f"k{i}", object=f"r{i}")
    ok_wr, _ = m.verify_writes()
    ok_c1, prob1 = m.verify_consistency(a1)
    print(f"[1] append-only extension    : verify_writes={ok_wr}  verify_consistency(a1)={ok_c1}  "
          f"{'(expected: both True)' if ok_wr and ok_c1 else 'UNEXPECTED: '+str(prob1)}")

    # --- Case 2: operator rewrites history + re-chains it (internally valid) ---
    m2, _ = _store()
    for i in range(5):
        m2.remember(f"fact {i}: the region is r{i}", key=f"k{i}", object=f"r{i}")
    a2 = m2.anchor()                                    # witnessed
    forged = copy.deepcopy(m2)
    operator_forge(forged, 1, "fact 1: the region is ATTACKER")   # rewrite an early record + re-chain
    ok_wr2, prob_wr2 = forged.verify_writes()
    ok_c2, prob_c2 = forged.verify_consistency(a2)
    print(f"[2] operator rewrite+re-chain: verify_writes={ok_wr2}  verify_consistency(a2)={ok_c2}")
    print(f"      -> verify_writes {'PASSES the forge (as expected: it cannot catch a re-chained rewrite)' if ok_wr2 else 'caught it'}; "
          f"anchor {'CATCHES it: '+prob_c2[0] if not ok_c2 else 'MISSED it (FAIL)'}")

    # --- Case 3: operator rolls the log back (truncate) ---
    m3, _ = _store()
    for i in range(6):
        m3.remember(f"fact {i}: the region is r{i}", key=f"k{i}", object=f"r{i}")
    a3 = m3.anchor()
    rolled = copy.deepcopy(m3)
    rolled._receipts = rolled._receipts[:3]             # operator drops the last 3 receipts
    ok_c3, prob_c3 = rolled.verify_consistency(a3)
    print(f"[3] operator rollback/truncate: verify_consistency(a3)={ok_c3}  "
          f"{'CATCHES it: '+prob_c3[0] if not ok_c3 else 'MISSED it (FAIL)'}")

    print()
    passed = (ok_wr and ok_c1) and (ok_wr2 and not ok_c2) and (not ok_c3)
    if passed:
        print("VERDICT: PASS — the external anchor closes the operator-adversarial hole: a re-chained rewrite")
        print("  that verify_writes accepts is CAUGHT by verify_consistency against a witnessed anchor, and a")
        print("  rollback is caught too. inspeximus's ANCHORABILITY gap (self-conceded) is now sealed — given the")
        print("  auditor witnessed a prior anchor out of band (the honest CT boundary).")
    else:
        print("VERDICT: FAIL — the anchor did not behave as specified; do not claim ANCHORABILITY is closed.")


if __name__ == "__main__":
    main()
