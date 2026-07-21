# Correcting a corrupted agent memory is not the same as reversing its harm

**STATUS: KILLED AT THE PUBLISH GATE — NOT FOR PUBLICATION (2026-07-12). Recorded as an honest dead-end.**

Two independent reasons the audit (stress-claim, 5 lenses + citation verification) killed the flagship:

1. **The behavioral 40-47% override was an artifact of the context construction.** The LLM context was built
   as the UNION of top-k lexical recall over four neighborhood queries, which deterministically stacked all
   k=3 poison-mentioning derived entries against a single correction line (a 3:1 majority). The decisive
   control — a single realistic value-weighted recall on the direct question — collapses naive_overwrite
   behavioral harm from 0.40-0.47 to **0.00 (0/15)**; the correction surfaces in 15/15 scenarios and poison
   in 0/15 without it. The override was our own stacked context, not a store-integrity property. (What the
   naive_overwrite arm does show — that a keyed supersession leaves keyless free-text derivatives active — is
   real but is exactly the knowledge-editing ripple effect, textbook.)

2. **The gap and the fix are both textbook, verified against real primary sources.** Recovery gap = Cohen et
   al. RippleEdits (TACL 2024, arXiv 2307.12976) + Truth-Maintenance Systems (Doyle, AIJ 1979). The fix
   (retract_lineage = demote-but-retain a derived lineage) = TMS retract-and-retain + provenance/bitemporal
   invalidation-with-retention, already ported to LLM-agent memory in TOKI (arXiv 2606.06240) and MemLineage
   (arXiv 2605.14421). Not a novel discovery.

Kept: `inspeximus.retract_lineage` ships as a modest product primitive with prior-art citations in its docstring.
Not published. The original draft is preserved below for the record.

---


## The question

Everyone building agent memory (us included) assumes store integrity matters because a corrupted memory
harms the agent downstream. The intake-gate storm showed that half of that is textbook: injected/conflicting
corruption, once retrieved and queried, causes large measured harm (RGB AAAI'24; AgentPoison NeurIPS'24;
MINJA NeurIPS'25; PoisonedRAG USENIX'25; STALE'26). But nobody deploys memory believing it will never be
corrupted — they deploy believing they can **fix** it. The unmeasured question is the recovery half-life:
once a fact is corrected, does its **harm** reverse, or is it sticky?

## Why this is non-circular (it survived the 7-lens stress-claim)

The original dose-response design was killed at the gate: harm reaches behavior only through retrieval, so
"does corruption harm the agent" on tasks that query the corrupted fact is circular. The recovery framing
escapes it: we hold the corruption **constant** and vary only the **correction method**. The mediator is
correction efficacy, not task/retrieval selection.

## Design (pre-registered in the probe docstring, fixed before results)

- A keyed root fact asserts a POISON value; the agent launders it into k derived free-text write-backs, each
  mentioning the poison and chained by `derived_from` (a mechanism prior art already establishes:
  Experience-Following arXiv 2505.16067; State Contamination arXiv 2605.16746 — we stand on it, not re-derive).
- Correction at time T, three arms:
  - `none` — no correction (baseline).
  - `naive_overwrite` — write the correct value to the key (what a bag-of-embeddings store can do); the k
    laundered derived entries survive.
  - `lineage_revert` — `inspeximus.forget_subject(root)` erases the root AND its derived_from lineage, then write
    the correct value. This is the inspeximus differentiator a value store lacks.
- Two metrics: (1) DETERMINISTIC retrieval residual harm (does the poison token still surface on neighborhood
  queries — no LLM); (2) BEHAVIORAL harm (does the agent, deepseek-v4-flash / glm-5.2 at temp 0, ANSWER with
  the poison value). The harm classifier is a deterministic string match, so there is NO LLM judge to
  contaminate (the method-auditor's fix, adopted by construction).
- FALSIFIER: if naive_overwrite reverses harm as well as lineage_revert (both ~0), the lineage infra is
  unnecessary and we publish the NULL. It could have fired; it didn't.

## Results (n=15 scenarios, inspeximus 0.7.15)

Retrieval residual harm (fraction of neighborhood queries still surfacing the poison token):

| method | k=0 | k=1 | k=2 | k=3 |
|---|---|---|---|---|
| none | 0.27 | 0.56 | 0.73 | 1.00 |
| naive_overwrite | 0.00 | 0.33 | 0.67 | 0.98 |
| lineage_revert | 0.00 | 0.00 | 0.00 | 0.00 |

Behavioral harm (agent answers with the poison value as current fact):

| model | method | k=0 | k=3 |
|---|---|---|---|
| deepseek-v4-flash | none | 0.67 | 0.73-0.80 |
| deepseek-v4-flash | naive_overwrite | 0.00 | **0.40-0.47** |
| deepseek-v4-flash | lineage_revert | 0.00 | **0.00** |
| deepseek-v4-flash | lineage_demote (NEW) | 0.00 | **0.00** |
| glm-5.2 (2nd family) | none | — | 1.00 (15/15) |
| glm-5.2 (2nd family) | naive_overwrite | — | **0.47** (7/15) |
| glm-5.2 (2nd family) | lineage_revert | — | **0.00** (0/15) |

- The behavioral gap at k=3 (naive 0.40 vs lineage 0.00, 6/15 vs 0/15) is significant (Fisher exact p ~ 0.017).
- The gap is CREATED by laundering depth: naive_overwrite is 0.00 at k=0 and 0.40 at k=3. Correcting the
  keyed root works until the poison has laundered into corroborating write-backs; then the corroborating mass
  overrides the single correction even though the correction is present in the agent's context.
- Buffering is partial, and now quantified: at naive k=3 the model split 6 poison / 4 correct / 5 other — it
  buffers some, the corroboration wins ~40%. The storm's "LLMs buffer corruption" is a half-truth.

## The honest tradeoff, and the fix we built (inspeximus 0.7.16 `retract_lineage`)

The experiment exposed a frontier: `naive_overwrite` leaves the derived facts ACTIVE and poisoned (harm),
while `lineage_revert` (forget_subject) HARD-DELETES them (0 harm but the legitimate payload — a connection
string location, a backup schedule — is lost with the poison). Neither RE-DERIVES.

So we built the middle path. `retract_lineage(subject)` demotes the subject and its derived_from lineage to
`status='superseded'` — excluded from default recall (so they stop asserting the retired value) but RETAINED
(recallable with `include_superseded`) and stamped `needs_rederivation`, so an agent can regenerate them
against the corrected root instead of losing them. A store with provenance can do this; a bag-of-embeddings
cannot. Measured (k=3):

| method | behavioral harm | derived payload: active / retained |
|---|---|---|
| naive_overwrite | 0.40-0.47 | 3.0 / 3.0 (active, poisoned -> harm) |
| lineage_revert | 0.00 | 0.0 / 0.0 (erased -> info loss) |
| **lineage_demote (retract_lineage)** | **0.00** | **0.0 / 3.0 (no harm AND payload kept for re-derivation)** |

This is the product half of the finding: the fix for laundered-lineage harm is not erasure, it is lineage-
aware demotion + flagging for re-derivation, which requires the write-history a value store does not keep.

## Cross-family generality (the overclaim lens's main concern — now tested)

The behavioral override is not a weak-model artifact. Across two families the naive_overwrite gap holds
(deepseek-v4-flash 0.40, glm-5.2 0.47), and lineage_revert is 0.00 on both. The stronger reasoning model does
NOT buffer the corruption away — if anything it takes the corroborating mass slightly more seriously (0.47 >
0.40). The "a frontier model would just reason around it" objection is empirically rejected for glm-5.2.

## Self-audit: is the override an artifact of context construction? (No — verified)

The agent's context is a broad recall over the entity's neighborhood (the union of top-k over several
questions about the entity), not a single direct-fact lookup. We verified the correction IS present in that
context (e.g. "Our primary database is PostgreSQL." sits alongside two surviving "MongoDB ..." derivatives).
So the override is genuine: with the correction visible, the corroborating mass (1 correction vs k surviving
derivatives) still flips the answer 40-47% of the time. The effect scales with k precisely because more
laundered derivatives outnumber the single correction — that IS the mechanism, not a rigged ratio. HONEST
SCOPE: the harm requires the agent to retrieve the neighborhood (which realistic context-gathering agents
do); an agent that only ever did a narrow direct-fact lookup, with the retriever ranking the correction
top-1, would not see the derivatives and would not be harmed.

## Honest scope / limits

- n=15 scenarios (pilot). One entity per scenario, synthetic domains.
- Two model families (deepseek-v4-flash, glm-5.2); not yet a frontier closed model (GPT-4/Claude).
- Retrieval uses lexical recall on a small store; a semantic-embedder run is a follow-up.
- Prior art to cite: this measures the RECOVERY direction (open per the intake-gate prior-art hunt); it
  stands on the laundering prior art (Experience-Following 2505.16067) and our own shipped echo-attack line
  (corrected facts resurrect under restatement) — related but distinct.
- The harm classifier is deterministic string-match (no LLM judge). The "other" bucket (5/15 on lineage for
  glm) is mostly multi-word correct values that don't string-match; it does NOT inflate the poison rate.

## Headline (scoped, final)

"Correcting a corrupted agent memory is not the same as reversing its harm. After a wrong fact launders into
k corroborating write-backs, a value-only correction (what a bag-of-embeddings store can do) is overridden by
the corroborating mass and the agent asserts the retired value ~40-47% of the time — on two different model
families, even with the correction present in context. A lineage-aware revert (inspeximus's provenance erasure)
holds behavioral harm at 0%. The cost: lineage revert also erases the derived scaffolding, so the real fix is
re-derivation from the corrected root."
