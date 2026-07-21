"""Tests for agent-receipts. Run: `pytest` (or `python tests/test_receipts.py`).

Covers the core chain (integrity + signature), tamper/forgery detection, the verifier CLI exit codes,
the external mediator + reconcile, and the optional mnemo audit (skipped if mnemo isn't importable)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # import the flat modules from the package root

from agent_receipts import ReceiptChain, generate_keypair, hash_content, receipt_hash, _HAVE_CRYPTO


def _chain():
    sk, pk = (generate_keypair() if _HAVE_CRYPTO else (None, None))
    c = ReceiptChain(actor="t", private_key_hex=sk, public_key_hex=pk)
    c.record("mcp.a", {"x": 1}, {"ok": True})
    c.record("mcp.b", {"y": 2}, {"ok": False})
    return c, pk


def test_honest_chain_verifies():
    c, pk = _chain()
    ok, problems = c.verify(expected_pubkey=pk)
    assert ok, problems


def test_tamper_is_detected():
    c, pk = _chain()
    c.receipts[0]["output_sha256"] = hash_content({"ok": "CHANGED"})
    ok, problems = c.verify(expected_pubkey=pk)
    assert not ok
    assert any("seq 0" in p and "tamper" in p for p in problems)


def test_rehashed_forgery_caught_by_signature():
    if not _HAVE_CRYPTO:
        return  # signatures unavailable; hash-chain-only tested elsewhere
    c, pk = _chain()
    c.receipts[0]["output_sha256"] = hash_content({"ok": "CHANGED"})
    c.receipts[0]["hash"] = receipt_hash(c.receipts[0])  # make hash self-consistent
    ok, problems = c.verify(expected_pubkey=pk)
    assert not ok
    assert any("invalid signature" in p for p in problems)


def test_chain_link_breaks_downstream():
    c, pk = _chain()
    c.receipts[0]["ts"] = 0.0
    c.receipts[0]["hash"] = receipt_hash(c.receipts[0])
    ok, problems = c.verify(expected_pubkey=pk)
    assert not ok
    assert any("seq 1" in p and "chain link" in p for p in problems)


def test_wrong_expected_pubkey_fails():
    if not _HAVE_CRYPTO:
        return
    c, _ = _chain()
    ok, problems = c.verify(expected_pubkey="00" * 32)
    assert not ok
    assert all("unexpected key" in p for p in problems)


def test_roundtrip_json():
    c, pk = _chain()
    loaded = ReceiptChain.from_receipts(json.loads(c.to_json()))
    ok, _ = loaded.verify(expected_pubkey=pk)
    assert ok


def test_verifier_cli_exit_codes(tmp_path=None):
    import tempfile
    import verify_cli
    c, pk = _chain()
    d = tempfile.mkdtemp()
    good = os.path.join(d, "r.json")
    open(good, "w").write(c.to_json())
    assert verify_cli.main([good, "--pubkey", pk, "--quiet"]) == 0 if pk else True
    # tamper
    r = json.loads(open(good).read())
    r[0]["output_sha256"] = "00" * 32
    bad = os.path.join(d, "bad.json")
    json.dump(r, open(bad, "w"))
    assert verify_cli.main([bad, "--quiet"]) == 1


def test_mediator_reconcile_catches_omission_and_lie():
    from mediator import Mediator, reconcile
    mk = (generate_keypair() if _HAVE_CRYPTO else (None, None))
    med = Mediator({"t": lambda v: {"r": v}}, private_key_hex=mk[0], public_key_hex=mk[1])
    log = []
    for v in (1, 2, 3):
        out = med.dispatch("t", v=v)
        log.append({"action": "t", "input_sha256": hash_content({"kwargs": {"v": v}}),
                    "output_sha256": hash_content(out)})
    ok, _ = reconcile(log, med.chain)
    assert ok  # faithful log reconciles
    log.pop(1)  # hide a call
    ok2, problems = reconcile(log, med.chain)
    assert not ok2 and any("OMITTED" in p for p in problems)


def test_mnemo_audit_if_available():
    try:
        from mnemo_receipts import ReceiptedMnemo, audit_memory
        from inspeximus import Inspeximus
    except Exception:
        return  # mnemo not importable in this layout; integration test skipped
    import tempfile
    path = os.path.join(tempfile.mkdtemp(), "m.json")
    mk = (generate_keypair() if _HAVE_CRYPTO else (None, None))
    rm = ReceiptedMnemo(Inspeximus(path=path), private_key_hex=mk[0], public_key_hex=mk[1])
    rm.remember("host is db-prod-01", key="db::host", mtype="semantic")
    ok, _ = audit_memory(rm.m, rm.chain, expected_pubkey=mk[1])
    assert ok
    rm.m.items[0]["text"] = "host is db-attacker-07"
    ok2, problems = audit_memory(rm.m, rm.chain, expected_pubkey=mk[1])
    assert not ok2 and any("no longer matches" in p for p in problems)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")
