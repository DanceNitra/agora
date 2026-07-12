# Deep world scan — 2026-07-12 (exponential research directions)

18-agent workflow (6 web-scan lenses -> synthesize/score -> adversarial filter -> design). 28 raw -> 12 scored
-> top 6 stress-tested -> 5 designed leads, 1 killed. All survivors came back REFRAME (core holds, honest
scoping added by the red-team). Full telemetry: tasks/wdvxpu0z3.output.

## Designed leads (survived the adversarial filter)

### 1. TOKI under concurrency — break a just-posted soundness proof  (exp 85 / def 78)
Q: TOKI (arXiv 2606.06240) proves soundness for LLM-memory update heuristics under a *well-ordered* write
stream. Real deployments never deliver that (async tools, parallel sub-agents, replays). Under adversarial
*re-ordering* (same facts, different order), do the heuristics corrupt the audit row — and is dependency-directed
provenance (mnemo retract_lineage + verify_writes) the UNIQUE policy whose audit trail survives?
First step (this week, deterministic, cloud-free): reuse the 8 triples in supersession_replication.py; write
root + derived fact; enumerate {in-order, reversed, interleaved} deliveries; run 2 policies (A value-only LWW,
B mnemo retract_lineage+verify_writes); measure "stale-derived-active rate" per policy + bootstrap CI on the gap.
Falsifier: gap <5pp / overlapping CIs => lineage confers no unique survival advantage, claim dies. (Also dies if
NO policy ever corrupts => TOKI robust in practice, no news.)
Why exp: a runnable receipt on a JUST-POSTED formal paper; pluggable policy => every memory system is a new row.

### 2. Governance-evidence sufficiency — does a retraction receipt actually answer the auditor?  (exp 81 / def 80)
Q: Is "can an independent auditor reconstruct who/what-authority/what-basis from ONLY the receipt bytes"
decorrelated from "does the API expose the primitive"? Score each system's real receipt on an 8-question
DEMM-style rubric with a ground-truth-blind judge. mnemo self-scores <8/8 (fails authority-binding, decision-basis,
external-anchorability — its own governance_report docstring concedes forge-able tombstones = self-incriminating,
shareable).
First step: run one correction lifecycle through mnemo, capture receipt bytes, blind-judge 8 questions (k/8).
Timed to (not headlined by) EU AI Act Art.12 enforceable Aug 2 2026.

### 3. Jepsen-for-agent-memory — a consistency-class classifier  (exp 75 / def 82, effort HIGH)
Q: Which formal consistency class (SC/causal/eventual) does each system satisfy under concurrent conflicting
writes, and is it a property of the PRODUCT or the control-plane placement? Hold mnemo fixed, move only the
control plane, show the class moves.
CAVEAT (red-team): 2606.17182 (June 2026) already ported SC/TSO/causal into agent memory ~1 month ago -> textbook
risk; novelty must be the standing runnable classifier + the placement axis, not the taxonomy.

### 4. Does provenance actually buy injection-resistance?  (exp 84 / def 72)
Q: The 2025-26 agent-provenance/payment specs (Portable Agent Memory "injection-resistant re-hydration", AIP
"100% rejection/600 attempts", AP2/FIDO "non-repudiable") advertise INTEGRITY but deliver only AUTHENTICATION.
Under a MINJA-style attack through the spec's OWN legitimate channels (honestly-signed poison), does ASR drop at
all, or collapse to source-auth while the poison lands?
First step: port MINJA (arXiv 2503.03704) into the integrity-bench harness as integrity_bench_inject.py; 3 cells
x N=30 (no-guard / attestation-on / forged-provenance); ASR + 95% CI per cell -> one Crucible row.
Why exp: a FAILED verdict on a Microsoft/Google/Mastercard-backed spec is immediate citable news.

### 5. Fault-to-fabrication on our LIVE 8-agent economy  (exp 68 / def 88 = highest defensibility)
Q: In a persistent live agent org, does a MAST-class integrity fault (echo of a retired value / unhonored revert)
CONVERT into a confident downstream fabrication, at what rate + latency, and does mnemo's integrity layer actually
cut it? Nobody else can run this — nobody else has a live org with weeks of real state.
First step: inject-and-replay over the 8 real .agent_memory/*.json stores; measure surfacing rate (stale value
re-appears in genuine top-k) with echo_guard OFF vs ON + Wilson CI. Deterministic, free.
Why exp: converts our one irreplicable asset into a standing measured falsifier; intervention arm IS mnemo.

## Killed (gate working)
**Cascade-repair / provable-forgetting** (shortlist #1, scored 88/86 — the top raw score, KILLED). Feature-presence
audit dressed as a test; MEMOREPAIR (2605.07242) already published the exact asymmetry (69.8-94.3%->0%); Graphiti
DOES bitemporal invalidation so "mnemo unique" collapses; and we already killed this on 2026-07-12
(recovery-halflife-finding.md). Self-serving home-turf trap. Good kill.

## Sleepers the (exp+def)-sum ranking squeezed out of the design pass (worth noting)
- **Neutral Crucible referee for the Mem0-vs-Letta / JordanMcCann benchmark fights** — exp **90** (highest of all),
  def 62, effort **LOW**. Both vendor camps already argue publicly; a dated neutral REPRODUCED/FAILED verdict gets
  pulled into an existing fight (whoever it favors amplifies it). Cheapest entries, highest built-in audience.
  Lower defensibility (methodology copyable) but first-mover standing-referee compounds. Best pure-DISTRIBUTION play.
- **Standing judge-integrity / preference-leakage ledger per model family** — exp 82, def 70. On the owner's
  headline frontier (epistemics); transfers our ground-truth-blind judge directly; one re-run per new model.
- **Re-standardize our echo/poison probes on FIELD-published attacks (MINJA / BackdoorAgent / MPBench)** — exp 66,
  effort LOW. Removes the "grading our own homework" critique; a credibility enabler under every other memory claim.
- CT-style public append-only log for agent-receipts (exp 70, def 80, HIGH effort); RAMR contamination ledger
  (exp 74, def 66).

## Read
Strongest "serious research + exponential" bet: **#1 TOKI-under-concurrency** (attacks a published formal proof
with a deterministic runnable falsifier this week, binds to mnemo's real differentiator, self-refilling ledger).
Strongest "pure reach, cheap" bet: **the Referee** (rides an existing public fight). They are complementary — one
is credibility/research, one is distribution.
