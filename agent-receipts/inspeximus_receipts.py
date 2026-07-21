"""inspeximus + agent-receipts: tamper-evident memory.

inspeximus is already append-only and has deterministic supersession, so it never silently edits a fact in
the normal flow. But the store is just a file — anyone who can touch that file can rewrite a stored
memory after the fact, and inspeximus (like any store) would then serve the altered text as if it were the
original. Receipts close that: every `remember()` emits a signed receipt committing to the memory's
content hash, so the *write history* becomes independently verifiable. Re-hash the current store against
the receipts and any out-of-band edit is named.

This is a thin wrapper — it does NOT modify inspeximus's zero-dependency core; it composes the two.

Run:  python inspeximus_receipts.py
MIT. Part of the Agora project / agent-receipts.
"""
from __future__ import annotations
import os
import sys
from typing import Any, Optional

from agent_receipts import ReceiptChain, generate_keypair, hash_content, _HAVE_CRYPTO

# inspeximus lives in the sibling inspeximus/ package of the Agora repo
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "inspeximus"))
from inspeximus import Inspeximus  # noqa: E402


def _content_commit(rec: dict) -> dict:
    """What a receipt commits to for a stored memory: id + a hash of its content-bearing fields."""
    return {"id": rec["id"],
            "content_sha256": hash_content({"text": rec["text"], "key": rec.get("key"),
                                            "mtype": rec.get("mtype")})}


class Receiptedinspeximus:
    """Wrap a Inspeximus instance so every write produces a signed, hash-chained receipt."""

    def __init__(self, inspeximus: Inspeximus, private_key_hex: Optional[str] = None,
                 public_key_hex: Optional[str] = None, actor: str = "inspeximus"):
        self.m = inspeximus
        self.public_key_hex = public_key_hex
        self.chain = ReceiptChain(actor=actor, private_key_hex=private_key_hex,
                                  public_key_hex=public_key_hex)

    def remember(self, text: str, **kwargs: Any) -> str:
        mid = self.m.remember(text, **kwargs)
        rec = next(r for r in self.m.items if r["id"] == mid)
        self.chain.record("inspeximus.remember",
                          {"text": text, "key": kwargs.get("key"), "mtype": rec.get("mtype")},
                          _content_commit(rec),
                          meta={"memory_id": mid})
        return mid

    # read-through to the underlying store
    def recall(self, *a: Any, **k: Any) -> Any:
        return self.m.recall(*a, **k)


def audit_memory(inspeximus: Inspeximus, chain: ReceiptChain,
                 expected_pubkey: Optional[str] = None) -> tuple[bool, list[str]]:
    """Verify the write-receipt chain AND that each stored memory still matches what was written.

    Catches out-of-band edits to the store file that inspeximus itself cannot see."""
    ok, problems = chain.verify(expected_pubkey=expected_pubkey)
    problems = list(problems)
    by_id = {r["id"]: r for r in inspeximus.items}
    for rcpt in chain.receipts:
        mid = (rcpt.get("meta") or {}).get("memory_id")
        if mid is None:
            continue
        cur = by_id.get(mid)
        if cur is None:
            problems.append(f"memory {mid}: written (receipt seq {rcpt['seq']}) but missing from the store now (deleted out-of-band)")
            continue
        if hash_content(_content_commit(cur)) != rcpt["output_sha256"]:
            problems.append(f"memory {mid}: stored content no longer matches the write receipt (edited after it was written)")
    return (len(problems) == 0, problems)


def _demo() -> None:
    print("=== inspeximus + receipts: tamper-evident memory ===\n")
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "inspeximus_receipts_demo.json")
    if os.path.exists(path):
        os.remove(path)

    kw = {}
    if _HAVE_CRYPTO:
        sk, pk = generate_keypair()
        kw = {"private_key_hex": sk, "public_key_hex": pk}
    else:
        pk = None
    rm = Receiptedinspeximus(Inspeximus(path=path), actor="agent-memory", **kw)

    rm.remember("The prod database host is db-prod-01.", key="prod-db::host", mtype="semantic")
    rm.remember("The on-call engineer this week is Maria.", key="oncall::engineer", mtype="episodic")
    rm.remember("Always confirm a transfer over 1000 with a second approver.", mtype="procedural")
    print(f"wrote {len(rm.chain.receipts)} memories, each with a signed receipt")

    ok, problems = audit_memory(rm.m, rm.chain, expected_pubkey=pk)
    print(f"[1] honest store audits clean? {ok}  {problems if problems else ''}")

    # Attacker edits a stored memory directly in the file/store (out-of-band), e.g. redirecting prod-db.
    print("\nattacker edits a stored memory out-of-band (db-prod-01 -> db-attacker-07)...")
    rm.m.items[0]["text"] = "The prod database host is db-attacker-07."

    ok2, problems2 = audit_memory(rm.m, rm.chain, expected_pubkey=pk)
    print(f"[2] after the out-of-band edit, audits clean? {ok2}")
    for p in problems2:
        print(f"      - {p}")

    print("\nMEASURED: inspeximus's normal flow never edits a fact; an out-of-band edit to the store IS")
    print("detectable here because each write left a signed receipt committing to the content hash.")


if __name__ == "__main__":
    _demo()
