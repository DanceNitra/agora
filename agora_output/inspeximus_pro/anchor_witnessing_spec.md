# inspeximus-PRO — Anchor-Witnessing Service (MVP mini-spec)

**Status:** BUILD-READY PLAN, not built. Build only on the trigger (first paying signal + CORE proven #1;
see memory `inspeximus-pro-scope-two-pillars`). PRO = proprietary/hosted — do NOT put this in the public inspeximus repo.

## Why this is the first paid wedge
inspeximus's free `erasure_certificate` / `DeletionManifest` / write-receipt chains are tamper-evident, but their
signatures are load-bearing only against a party who does NOT hold `receipt_key`. An operator who holds the key
can rewrite the whole history AND re-sign it so it verifies internally. The ONE thing that closes this
(Certificate-Transparency model, RFC 6962) is an **independent witness** that recorded a prior `anchor()` the
operator cannot retroactively change. That witness **cannot be self-hosted** (that's the point) → it is a clean
paid line, and it upgrades every free receipt from "operator-adversarial-weak" to "operator-adversarial-proof."
Low infra: append-only log + Ed25519 + a verify endpoint. NO LLM, NO GPU.

## Builds directly on existing free CORE (no new crypto needed)
- `m.anchor()` already returns a CT-style signed tree head: `{n_writes, writes_tip, n_tombstones,
  tombstones_tip, ts, sth_hash, witness_sig?}` — a compact commitment to the entire write + tombstone history.
- `m.verify_consistency(prior_anchor)` already proves the current log is an append-only extension of a prior
  anchor. The service only needs to STORE anchors trustworthily and serve them back.

## API (thin, stateless-ish; per-tenant API key)
- `POST /v1/anchor` — body `{anchor: <m.anchor() STH>}`, header `Authorization: Bearer <tenant-key>`.
  Appends the STH to the tenant's append-only witness log, stamps `received_ts`, Ed25519 **counter-signs** it
  with the WITNESS key, returns `{witness_seq, received_ts, witness_sig, witness_pubkey}` (the witness receipt).
- `GET /v1/anchors?tenant=&since_seq=` — returns the tenant's witnessed anchors (for the auditor to pick a
  prior one). Each carries the witness counter-sig.
- `POST /v1/verify` — body `{current_anchor, prior_witness_seq}` → runs `verify_consistency(current, prior)`
  server-side and returns `{ok, problems}`. (Auditor can also do it locally: fetch the witnessed prior anchor,
  run `m.verify_consistency(prior)` — the service is only the trusted source of the prior.)
- `GET /v1/witness-sth` — the witness log's OWN append-only tree head (so the witness itself is auditable —
  CT gossip: monitors can detect a witness that rewrote its log). Closes "who witnesses the witness."

## Data model (append-only, itself tamper-evident)
`witness_entry = {tenant, seq, anchor: <STH>, received_ts, prev_hash, entry_hash, witness_sig}` — hash-chained
per tenant (like the write-receipt chain), so the witness log is tamper-evident too. Store: sqlite/Postgres.
Keys: one Ed25519 witness keypair (public key published); one API key per tenant.

## Threat model / honest scope
- CLOSES: operator (key-holder) rewrites/rolls back history → the rewritten tip can't match an anchor the
  witness already recorded (append-only violation is provable via `verify_consistency`).
- Does NOT: reach the customer's other stores (that's cross-infra ErasureTargets), nor prove physical
  destruction, nor defend against a compromised witness that colludes — mitigate by publishing `witness-sth`
  for external monitors (CT gossip) and, later, multiple independent witnesses.

## Client integration (one call added to their flow)
```
sth = m.anchor()
receipt = POST /v1/anchor {anchor: sth}      # store receipt alongside the erasure/write receipts
# at audit time:
prior = GET /v1/anchors (pick the witnessed one) ; ok, problems = m.verify_consistency(prior)
```

## Build estimate & cost
~1 engineer-day when triggered: 4 endpoints + an append-only hash-chained store + Ed25519 counter-sign +
per-tenant keys. Serverless-friendly. No LLM/GPU/heavy infra. Pricing: the Pro tier ($29/mo or $99-499/yr),
"the receipt's independence."

## Do NOT build until
first organic inbound / paying signal AND CORE demonstrably #1 (owner rule). This doc exists so that when the
signal comes we ship in a day, not a month.
