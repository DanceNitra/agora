# STORM verdict — lead ① TOKI-under-concurrency (2026-07-13)

CLAIM under gate: "A one-shot dependency-directed lineage retraction does not survive out-of-order writes;
correction soundness under concurrency requires provenance CHECKED at READ time." Measured n=72: one-shot
lineage 0.61 / value-only LWW 0.92 / read-time guard 0.00.

## Gate: VALIDATE ok (numbers reproduce, deterministic). STORM -> KILL as research.

5/5 lenses converge that the THEORY is closed/textbook:
- ACADEMIC: CRDT causal-delivery theorem (Shapiro 2011, peer-reviewed) — a non-commutative op applied once
  needs causal delivery; retraction + stale derived write do not commute. Read-time = a monotone predicate
  over the full write-set = a semilattice join (CALM theorem: monotone = coordination-free). The real theorem
  is monotonicity/commutativity, NOT read-vs-write timing. TOKI (2606.06240) already ties soundness to an
  isolation precondition. Bitemporal as-of-query (Snodgrass) makes correction a read-time reconstruction by
  construction.
- SKEPTIC: eager-vs-lazy materialized-view maintenance (Zhou VLDB'07), SQL DEFERRABLE constraints, TMS must
  re-evaluate justifications (a one-shot cascade is a KNOWN-INCORRECT TMS). THE TELL: 0.92==0.92 for one-shot
  and value-only means the lineage primitive collapsed to LWW because it is a write-time trigger benchmarked
  against a self-chosen adversarial ordering — a CLOSED STRAWMAN (mnemo's own primitives). A publishable
  version must beat a real external baseline (deferred-check / lazy-IVM / a proper TMS).
- HISTORIAN: same lesson re-learned 4x — TMS 1979, eager-vs-lazy views 1986-2007, MESI cache coherence,
  NoSQL->ACID 2007-2012. "Write-time retraction is a performance optimization, never the correctness
  mechanism."
- PRACTITIONER: the failure is real in the wild (AgentScope #402, LangGraph out-of-order tool responses,
  RippleEdits ~50% ripple ceiling) — BUT Graphiti already SHIPS the read-time bitemporal fix. Both the failure
  and the fix are known/deployed.
- ECONOMIST: the only latent value is an EMPIRICAL cross-system measurement (under-tested for market reasons),
  not the theoretical claim.

## Decision
KILL as a research / Crucible finding. It is a textbook re-derivation (eager-vs-lazy / CRDT causal delivery /
TMS re-evaluation / bitemporal), and the comparison is a closed strawman (own primitives, self-chosen ordering).
This is the same pattern as recovery-halflife-finding (killed at gate, converted to product). No AUDIT/VERIFY
needed — STORM already adjudicated a fatal defect; nothing survives to verify.

KEEP as a PRODUCT improvement: ship recall(lineage_guard=True) — a read-time derived-from-superseded check —
as a mnemo feature, documented honestly against the prior art above (Graphiti bitemporal, lazy IVM, TMS/ATMS).
A correct, useful feature (mnemo today has only the write-time one-shot cascade), NOT a novel result.

The genuinely-open slice IF we ever want research value: a purely EMPIRICAL cross-system escape-rate benchmark
on REAL agent stores (mem0/Graphiti/mnemo) under realistic out-of-order delivery — but it largely reduces to
known architecture differences (Graphiti ~0, no-lineage systems leak), so it is a weak Crucible cell, not a
finding. Do not publish the theory.
