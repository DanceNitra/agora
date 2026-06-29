"""agent-receipts — tamper-evident, third-party-verifiable receipts for AI agent / MCP actions.

The problem: an AI agent's own logs are *self-reported claims*. Nothing stops the agent (or a
compromised proxy) from rewriting history after the fact, or from a hallucinated "I called the
database and it returned X" that never happened. A *receipt* is the opposite of a log: independent,
verifiable evidence of what an action consumed and produced, that a third party can check without
trusting the agent.

This single file gives the smallest honest version of that, in two layers:

  1. HASH CHAIN (integrity, zero extra deps).  Each receipt commits to the previous one
     (prev = hash of the last receipt), so the whole sequence is a Merkle-style chain. Edit ANY
     past receipt and every hash after it breaks -> a *partial* edit is detectable, and you can
     name the exact step that was altered. IMPORTANT, honest limit: the hash chain ALONE does not
     stop a thorough tamperer who recomputes the whole chain end-to-end (no link breaks then) -- so
     integrity-only is enough only if the chain head is published/anchored somewhere the attacker
     can't also rewrite. The SIGNATURE (layer 2) is what protects a self-held chain.

  2. ED25519 SIGNATURES (authenticity, needs `cryptography`).  Each receipt's hash is signed with
     the actor's private key. A third party verifies with the PUBLIC key only -> it proves *who*
     produced the receipt and that the content wasn't forged, without anyone sharing a secret.
     (Optional: if `cryptography` is not installed, the hash chain still works on its own.)

Privacy nod (the "zero-knowledge-ish" part): receipts store the SHA-256 of inputs/outputs, not the
raw content. You commit to *what* was processed; you reveal the content only if/when you choose, and
anyone can later check a revealed value against the committed hash. Real zero-knowledge proofs (ZK-
SNARKs) go further — proving a computation was correct without revealing inputs at all — and are the
heavier end of this same design space (see the README for the landscape and prior art).

Run the self-demo:  python agent_receipts.py
MIT. Part of the Agora project. Honest scope: this is a reference PoC, not a hardened product.
"""
from __future__ import annotations
import json
import time
import hashlib
from typing import Any, Optional

GENESIS = "0" * 64

# --- optional asymmetric signing (graceful if the lib is absent) ---
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    _HAVE_CRYPTO = True
except Exception:  # pragma: no cover - exercised only on installs without `cryptography`
    _HAVE_CRYPTO = False


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj: Any) -> bytes:
    """Deterministic JSON so the same content always hashes the same (sorted keys, no spaces)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def hash_content(content: Any) -> str:
    """Hash arbitrary input/output content. Bytes are hashed as-is; everything else is canonicalized."""
    if isinstance(content, (bytes, bytearray)):
        return sha256_hex(bytes(content))
    return sha256_hex(_canonical(content))


def generate_keypair() -> tuple[str, str]:
    """Return (private_key_hex, public_key_hex) for an Ed25519 actor identity."""
    if not _HAVE_CRYPTO:
        raise RuntimeError("signing requires the `cryptography` package (pip install cryptography)")
    sk = Ed25519PrivateKey.generate()
    sk_hex = sk.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    ).hex()
    pk_hex = sk.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()
    return sk_hex, pk_hex


def _sign(private_key_hex: str, message: bytes) -> str:
    sk = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    return sk.sign(message).hex()


def _verify_sig(public_key_hex: str, signature_hex: str, message: bytes) -> bool:
    try:
        pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        pk.verify(bytes.fromhex(signature_hex), message)
        return True
    except Exception:
        return False


def receipt_hash(r: dict) -> str:
    """The receipt's own hash commits to its content AND the previous receipt (the chain link)."""
    core = {
        "seq": r["seq"], "ts": r["ts"], "action": r["action"], "actor": r.get("actor"),
        "input_sha256": r["input_sha256"], "output_sha256": r["output_sha256"],
        "meta": r.get("meta"), "prev": r["prev"],
    }
    return sha256_hex(_canonical(core))


class ReceiptChain:
    """An append-only, hash-chained, optionally-signed sequence of action receipts."""

    def __init__(self, actor: Optional[str] = None, private_key_hex: Optional[str] = None,
                 public_key_hex: Optional[str] = None):
        self.actor = actor
        self._sk = private_key_hex
        self.public_key_hex = public_key_hex
        self.receipts: list[dict] = []

    def record(self, action: str, inputs: Any, output: Any, meta: Optional[dict] = None,
               ts: Optional[float] = None) -> dict:
        """Record one action (e.g. an MCP tool call): commit to its input/output hashes, chain, sign."""
        prev = self.receipts[-1]["hash"] if self.receipts else GENESIS
        r = {
            "seq": len(self.receipts),
            "ts": ts if ts is not None else time.time(),
            "action": action,
            "actor": self.actor,
            "input_sha256": hash_content(inputs),
            "output_sha256": hash_content(output),
            "meta": meta,
            "prev": prev,
        }
        r["hash"] = receipt_hash(r)
        if self._sk:
            r["pubkey"] = self.public_key_hex
            r["sig"] = _sign(self._sk, bytes.fromhex(r["hash"]))
        self.receipts.append(r)
        return r

    def verify(self, expected_pubkey: Optional[str] = None) -> tuple[bool, list[str]]:
        """Recompute the chain from scratch. Returns (ok, problems). Names the exact broken step."""
        problems: list[str] = []
        prev = GENESIS
        for i, r in enumerate(self.receipts):
            if r.get("seq") != i:
                problems.append(f"seq {i}: out-of-order (claims seq={r.get('seq')})")
            if r.get("prev") != prev:
                problems.append(f"seq {i}: broken chain link (prev mismatch -> a prior receipt was altered/removed)")
            if receipt_hash(r) != r.get("hash"):
                problems.append(f"seq {i}: content tampered (hash does not match this receipt's fields)")
            if "sig" in r:
                pk = r.get("pubkey")
                if expected_pubkey and pk != expected_pubkey:
                    problems.append(f"seq {i}: signed by an unexpected key (possible impersonation)")
                if not _HAVE_CRYPTO:
                    problems.append(f"seq {i}: signature present but `cryptography` not installed to verify it")
                elif not _verify_sig(pk, r["sig"], bytes.fromhex(r["hash"])):
                    problems.append(f"seq {i}: invalid signature (forged or wrong key)")
            elif expected_pubkey:
                problems.append(f"seq {i}: unsigned, but a signature was required")
            prev = r.get("hash")
        return (len(problems) == 0, problems)

    def to_json(self) -> str:
        return json.dumps(self.receipts, indent=2, ensure_ascii=False)

    @classmethod
    def from_receipts(cls, receipts: list[dict]) -> "ReceiptChain":
        c = cls()
        c.receipts = receipts
        return c


def _demo() -> None:
    print("=== agent-receipts: self-demo ===\n")
    signed = _HAVE_CRYPTO
    if signed:
        sk, pk = generate_keypair()
        chain = ReceiptChain(actor="research-agent-01", private_key_hex=sk, public_key_hex=pk)
        print(f"actor identity (public key): {pk[:16]}...  (third parties verify with this, no secret shared)\n")
    else:
        chain = ReceiptChain(actor="research-agent-01")
        pk = None
        print("(`cryptography` not installed -> hash-chain only, no signatures)\n")

    # An agent does three MCP tool calls. Each gets a receipt.
    chain.record("mcp.web_search", {"query": "supersession blind spot AUROC"},
                 {"results": 7, "top": "arXiv:2606.26511"})
    chain.record("mcp.memory.write", {"fact": "Pro tier costs 39 USD/mo", "source": "billing:tool"},
                 {"stored": True, "id": "m-1042"})
    chain.record("mcp.code.run", {"cmd": "python probe.py"}, {"exit": 0, "stdout_sha": "9f1c..."})
    print(f"recorded {len(chain.receipts)} receipts (one per tool call)")

    ok, problems = chain.verify(expected_pubkey=pk)
    print(f"[1] honest chain verifies?  {ok}  {problems if problems else ''}")

    # TAMPER: someone edits a past receipt's output AFTER the fact (e.g. to hide what really happened).
    chain.receipts[1]["output_sha256"] = hash_content({"stored": True, "id": "m-DIFFERENT"})
    ok2, problems2 = chain.verify(expected_pubkey=pk)
    print(f"[2] after editing receipt #1's output:  verifies? {ok2}")
    for p in problems2:
        print(f"      - {p}")

    # FORGE: rebuild #1 so its own hash matches the edit. The hash chain is now internally consistent,
    # but the SIGNATURE was made over the original hash by the real key -> still caught (if signed).
    chain.receipts[1]["hash"] = receipt_hash(chain.receipts[1])
    ok3, problems3 = chain.verify(expected_pubkey=pk)
    print(f"[3] after also recomputing the hash to match:  verifies? {ok3}")
    for p in problems3:
        print(f"      - {p}")
    if signed:
        print("    -> the signature (made by the real key over the ORIGINAL hash) exposes the forgery,")
        print("       and #2's broken chain link points downstream. Integrity + authenticity together.")
    else:
        print("    -> this lazy edit broke a chain link, so it's caught. But WITHOUT signatures a")
        print("       thorough tamperer would recompute the WHOLE chain (no link breaks) and it would")
        print("       pass -- integrity-only needs an anchored/published head. Ed25519 signing closes this.")

    print("\nMEASURED: an honest receipt chain verifies; a partial edit is detected at the exact step;")
    print("a re-hashed forgery is caught by the SIGNATURE (a full recompute defeats the hash chain alone).")


if __name__ == "__main__":
    _demo()
