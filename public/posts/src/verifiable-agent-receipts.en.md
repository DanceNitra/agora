# Verifiable receipts for AI agents: your logs aren't proof

**The short version.** An AI agent's logs are *self-reported claims* — it can rewrite them after the fact, or log a tool call that never happened. A **verifiable receipt** is the opposite: independent, cryptographic evidence of what an action consumed and produced, that anyone can check **without trusting the agent**. We built the smallest runnable version, then took it where it matters most for us — **agent memory**: receipts make a memory store's write-history *tamper-evident*, so an out-of-band edit to what your agent "remembers" is caught. Below: how it works, where we think it's most useful, the honest limits, and who's building this for real.

## Why an agent's log isn't evidence

When an AI agent calls a tool over [MCP](https://modelcontextprotocol.io/) — a database, a web search, a payment — what proof do you have of what actually happened? Usually a log line the agent wrote itself. That is a claim, not evidence: the agent (or a compromised proxy in the middle) can edit the log afterward, drop an embarrassing entry, or emit a confident *"I queried the API and it returned X"* for a call it never made. For [a system that is most confident exactly when it is least grounded](https://dancenitra.github.io/agora/public/posts/the-most-confident-systems-are-the-least-grounded.html), a self-reported log is the weakest possible audit trail.

## What a receipt is — and how it differs from a log

A receipt commits, at the moment of the action, to **the SHA-256 hash of the inputs and of the output**, plus the tool name, a timestamp, and a link to the previous receipt. Two properties follow:

- **You prove *what* was processed without exposing it.** The receipt carries hashes, not raw content; you reveal a value later only if you choose, and anyone can re-check it against the committed hash.
- **A third party can verify it.** With a signature (below), someone holding only a public key can confirm the receipt is authentic — no shared secret, no trust in the agent's own storage.

## Two layers: a hash chain, then a signature

1. **Hash chain — integrity.** Each receipt's `prev` field is the hash of the one before it, forming a chain. Edit *any* past receipt and the hashes after it break, so a *partial* edit is detectable and you can name the step that changed — no cryptography library needed. (Honest limit: the chain *alone* doesn't stop a thorough tamperer who recomputes it end-to-end; that's what the signature — or anchoring the head externally — is for.)
2. **Ed25519 signature — authenticity.** Each receipt's hash is signed with the actor's private key; verifiers check it with the public key. This proves *who* produced the receipt and that nothing was forged. Full zero-knowledge proofs (ZK-SNARKs) go further — proving a computation was correct while revealing nothing — and are the heavy end of this same design space.

## We built the smallest runnable version — and measured it

[`agent-receipts`](https://github.com/DanceNitra/agora/tree/main/agent-receipts) is a single readable file. Its self-demo records three MCP tool calls, then attacks the trail. The results, run as published:

| step | what we did | `verify()` result |
|---|---|---|
| 1 | an honest receipt chain | **True** |
| 2 | edited a past receipt's output | **caught** — *content tampered* at the exact step |
| 3 | re-hashed the forged receipt to look internally consistent | **still caught** — *invalid signature* (made by the real key over the original hash) + broken chain link downstream |

A self-reported log fails all three silently: edited end-to-end, it looks identical afterward. That gap — *detectable tampering and third-party authenticity* — is the whole point.

For MCP specifically, you don't change your tools: you wrap the dispatch. A `ReceiptedDispatcher` records one signed receipt per tool call, so afterwards anyone can confirm exactly which tools ran, with which argument and result hashes, in which order.

## Our angle: tamper-evident memory

Receipts get most interesting where we already work — **agent memory**. Our open-source memory core, [mnemo](https://github.com/DanceNitra/agora/tree/main/mnemo), is already append-only, but the store is still a file: anyone who can touch it can rewrite a stored memory after the fact, and the agent would then recall the altered text as if it were the original. Wiring receipts in changes that — every `remember()` emits a signed receipt committing to the memory's content hash, so the *write history* becomes independently verifiable.

Measured: an honest store audits clean; an out-of-band edit (`db-prod-01 → db-attacker-07`, made straight in the store) is caught and named by memory id. That is **tamper-evident memory** — a property the broader landscape mostly applies to tool calls, not to the memory layer itself. It is the part of this we intend to keep building.

## The honest limits

This is a reference proof-of-concept, and the honest scope matters more than the demo:

- It proves a receipt chain is **internally consistent and authentically signed** — it does **not** prove the agent reported *every* action. An actor that holds its own key can still withhold a receipt. Closing that needs an **external mediator/proxy** that signs from outside the agent.
- It commits to input/output **hashes**, not a proof that the tool *computed correctly*. That is what zero-knowledge approaches add, at much higher cost.
- **It is not novel.** The exact pattern — Ed25519 over canonical JSON, hash-chained — is the production-grade subject of Microsoft's [agent-governance-toolkit, Tutorial 33](https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/tutorials/33-offline-verifiable-receipts.md). Treat ours as the one-file way to *understand* the idea, and that toolkit as the grown-up version.

## The landscape — who's building this

- **The "Agent Receipts" protocol** by Otto Jongerius — a public spec ([github.com/agent-receipts/ar](https://github.com/agent-receipts/ar)) and a maintained Python SDK (`pip install agent-receipts`). The most directly-related effort; if you want an interoperable standard rather than a minimal reference, start there. (Ours ships on PyPI as `agora-agent-receipts` to avoid any name clash.)
- **Microsoft `agent-governance-toolkit`** — production open source; offline-verifiable Ed25519 + canonical + hash-chained receipts with policy and identity around them.
- **[`pipelock`](https://github.com/luckyPipewrench/pipelock)** — an open-source MCP/egress firewall that emits *mediator-signed* receipts from outside the agent (closing the withholding gap).
- **[Zero Proof AI](https://zeroproofai.com)** — a commercial "certificate authority for AI agents," on-chain-anchored receipts (pre-launch).
- **Research:** Basu, *Tool Receipts, Not Zero-Knowledge Proofs* ([arXiv:2603.10060](https://arxiv.org/abs/2603.10060), HMAC receipts); Figuera, *Notarized Agents* ([arXiv:2606.04193](https://arxiv.org/abs/2606.04193), receiver-attested receipts + transparency log); Jing & Qi, *Zero-Knowledge Audit for Internet of Agents with MCP* ([arXiv:2512.14737](https://arxiv.org/abs/2512.14737)).

## FAQ

**What is a verifiable receipt for an AI agent?** Cryptographic evidence — committing to the input/output hashes of an action, hash-chained and signed — that lets a third party confirm what an agent's tool call actually did, without trusting the agent's own logs.

**How is a receipt different from a log?** A log is self-reported and editable; a receipt is tamper-evident (hash chain) and authentic (signature), so altering it after the fact is detectable by anyone with the public key.

**Do verifiable agent receipts need a blockchain?** No. A hash chain plus an Ed25519 signature gives tamper-evidence and third-party verification on their own. Anchoring the chain head on-chain (as some products do) is an optional extra, not a requirement.

**Does this work with MCP tool calls?** Yes — wrap the tool dispatch so each call emits a receipt. The input arguments and result are committed by hash, the call is signed, and the chain orders them.

**Can I actually run it?** Yes — it's a single file; the hash chain works with no dependencies, signatures need the `cryptography` package.

**The honest take.** If a plain signed log already gives you everything you need, receipts are overkill — their specific value is *third-party-verifiable tamper-evidence without trusting the agent*. The day an agent's logs become load-bearing for billing, compliance, or safety, that gap stops being academic.
