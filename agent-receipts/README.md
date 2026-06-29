# agent-receipts

**Tamper-evident, third-party-verifiable receipts for AI agent / MCP actions — in one small file.**

An AI agent's logs are *self-reported claims*. Nothing stops the agent — or a compromised proxy —
from rewriting history after the fact, or from emitting a hallucinated "I called the database and it
returned X" that never happened. A **receipt** is the opposite of a log: independent, verifiable
evidence of what an action consumed and produced, that a third party can check **without trusting the
agent**.

This is the smallest honest version of that idea, built to be read in one sitting and run in one
command. It is a reference proof-of-concept, not a hardened product — the scope below is deliberately
honest about what it does and does not give you.

```bash
python agent_receipts.py     # core: hash-chain + Ed25519 signatures + tamper/forgery demo
python mcp_wrapper.py         # wrap any MCP/agent tool so every call emits a receipt
```

## What it does — two layers

1. **Hash chain (integrity, zero extra deps).** Each receipt commits to the previous one
   (`prev = hash of the last receipt`), forming a Merkle-style chain. Edit *any* past receipt and
   every hash after it breaks — so tampering is **detectable**, and `verify()` names the exact step
   that was altered. The trail is append-only-or-caught.
2. **Ed25519 signatures (authenticity, needs `cryptography`).** Each receipt's hash is signed with
   the actor's private key; a third party verifies with the **public key only**. This proves *who*
   produced the receipt and that the content wasn't forged — no shared secret. (If `cryptography`
   isn't installed, the hash chain still works on its own.)

A receipt commits to the **SHA-256 of inputs/outputs, not the raw content** — so you prove *what* was
processed without exposing it, and reveal a value later only if you choose (anyone can re-check it
against the committed hash). Full zero-knowledge proofs (ZK-SNARKs) go further still — proving a
computation was correct while revealing *nothing* — and are the heavy end of this same design space.

## What the demo measures

The self-demo records three MCP tool calls, then attacks the trail:

| step | action | result |
|---|---|---|
| 1 | honest chain | `verify() → True` |
| 2 | edit a past receipt's output | caught: *content tampered* at the exact seq |
| 3 | re-hash the forged receipt to look consistent | still caught: *invalid signature* + *broken chain link downstream* |

Logs cannot do this: a self-reported log can be edited end-to-end and looks identical afterward.

## Use it

```python
from agent_receipts import ReceiptChain, generate_keypair

sk, pk = generate_keypair()                       # the actor's identity
chain = ReceiptChain(actor="my-agent", private_key_hex=sk, public_key_hex=pk)

chain.record("mcp.web_search", {"query": "..."}, {"results": 7})   # one receipt per tool call
chain.record("mcp.memory.write", {"fact": "..."}, {"stored": True})

ok, problems = chain.verify(expected_pubkey=pk)   # anyone with pk can run this
open("receipts.json", "w").write(chain.to_json()) # ship the receipts; the public key verifies them
```

`mcp_wrapper.py` shows a `ReceiptedDispatcher` that drops in around an MCP-style tool registry so you
don't touch your tools — you wrap the dispatch.

## Honest scope (what this is NOT)

- It proves a receipt **chain is internally consistent and authentically signed**. It does **not** by
  itself prove the agent reported *every* action — an actor that controls its own key can still
  withhold a receipt. Closing that needs an **external mediator/proxy** that signs receipts from
  outside the agent (see the landscape below), or anchoring the chain head to a third party.
- It commits to input/output **hashes**, not a proof that the tool *computed correctly*. That is what
  ZK-SNARK approaches add, at much higher cost.
- Keys here are raw/in-memory for clarity; real deployments use a KMS / hardware-backed key store.

## Landscape & prior art

This sits in an active, fast-moving space — **we build on it, we did not invent it.** In particular,
the exact pattern here (Ed25519 + canonical JSON + hash-chain) is the production-grade subject of
**Microsoft's [agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit),
Tutorial 33 "offline verifiable receipts"** (Ed25519 over RFC 8785 / JCS canonical payloads,
hash-chained, CLI-verifiable offline). Treat this repo as the *minimal one-file way to understand the
idea*, and that toolkit as the grown-up version.

Honest map of the space:

- **Production OSS (corporate):** Microsoft `agent-governance-toolkit` — Tutorial 33 = the same
  Ed25519 + canonical + hash-chain receipts, with policy/identity/sandboxing around it.
- **External-mediator receipts:** [`pipelock`](https://github.com/luckyPipewrench/pipelock) — an
  open-source MCP/egress firewall that emits *mediator-signed* Ed25519 receipts from **outside** the
  agent (core Apache-2.0; enterprise features Elastic-License), which is how you close the
  agent-can-withhold-a-receipt gap noted above.
- **Commercial:** [Zero Proof AI](https://zeroproofai.com) — a pre-launch "certificate authority for
  AI agents" issuing on-chain-anchored receipts for tool calls.
- **Research:**
  - Basu, *Tool Receipts, Not Zero-Knowledge Proofs: Practical Hallucination Detection for AI Agents*,
    [arXiv:2603.10060](https://arxiv.org/abs/2603.10060) (2026) — HMAC-signed tool-execution receipts
    (the pragmatic, symmetric camp; we use Ed25519 so a third party verifies without a shared secret).
  - Figuera, *Notarized Agents: Receiver-Attested Confidential Receipts for AI Agent Actions*,
    [arXiv:2606.04193](https://arxiv.org/abs/2606.04193) (2026) — receiver-signed receipts published
    to a transparency log (the external-attestation camp).
  - Jing & Qi, *Zero-Knowledge Audit for Internet of Agents … with Model Context Protocol*,
    [arXiv:2512.14737](https://arxiv.org/abs/2512.14737) (2025) — the zero-knowledge / privacy-
    preserving end of the same space.

## Roadmap (if this proves useful)

External-mediator mode (sign from a proxy, not the agent) · publish-and-anchor the chain head · a
verifier CLI (`verify receipts.json --pubkey ...`) · an `mnemo` integration so memory writes are
tamper-evident by default · selective disclosure of a single committed field.

MIT. Part of the [Agora](https://github.com/DanceNitra/agora) project — an autonomous research OS that
ships every claim with a runnable receipt. Feedback and adversarial testing welcome.
