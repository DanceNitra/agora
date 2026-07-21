# Result — is there any headroom for a write-side correction layer? NO, and it is worse than neutral.

Run 2026-07-21. Pre-registered in `ORACLE_HEADROOM_PREREG.md` (+ Appendices D and E, both written
before the run). 54 deduped probes x 4 arms = 216 rows, 892s, zero drops, arms verified paired.

## Headline

| arm | what it is | accuracy (n=54) |
|---|---|---|
| `oracle_state` | the corpus's own resolved, labelled gold state (positive control — leaks the answer) | **0.870** |
| `oracle_evidence` | raw unresolved evidence quotes, instructed prompt | **0.870** |
| `oracle_evidence_neutral` | the same raw quotes, instruction removed | **0.833** |
| `oracle_current` | current values only — what a perfect supersession layer can emit | **0.481** |

Baselines on the identical probe subset, from the existing run: mnemo 0.545, naive 0.578.

## Against the registered predictions

**P8 (liveness gate) PASSES**: `oracle_state` 0.870 >= 0.85, so the judge/answerer is not the binding
constraint and a null here is interpretable rather than a broken harness.

**P6 (primary) — no headroom.** `oracle_current − oracle_evidence_neutral` on the 36 non-history
probes = **−13.9 pp**, unclustered CI [−30.6, +2.8] (family-clustered [−23.8, −2.8]). The registered
decisive threshold was |Δ| >= 25 pp, which is not met — so this is formally "no effect detectable at
n=36", **not** "proven zero". But the point estimate is NEGATIVE, so there is certainly no positive
headroom to chase.

**Resolution itself buys nothing.** `oracle_state − oracle_evidence_neutral` = **+3.7 pp**, CI
[−7.4, +14.8] — the corpus's own resolved, labelled state is no better than a pile of contradictory
raw quotes. With retrieval held perfect, **the answerer resolves corrections unaided.**

**P7 (registered against ourselves) — CONFIRMED, and it is the finding.**
`oracle_current − oracle_evidence_neutral` on the 18 history probes = **−77.8 pp**, CI [−94.4, −55.6].
`oracle_current` scores **exactly 0.000** on both `operation_trace` (n=12) and `trajectory_reasoning`
(n=6). A supersession layer hides superseded values; a third of the questions ask precisely for them.

**P9 — the prompt line buys nothing measurable.** `oracle_evidence − oracle_evidence_neutral` =
+3.7 pp, CI [−3.7, +11.1]. Deleting "if the user corrected a value, use the CURRENT one" changes
almost nothing, so the earlier arms were not propped up by that instruction either.

## What this settles

1. **The four nulls are the correct result of a well-specified experiment, not a defect.** There was
   never anything for the write-side correction layer to win on answer accuracy: perfect resolution
   beats raw contradictory evidence by +3.7 pp, CI through zero.
2. **On this task supersession is not neutral, it is destructive.** The best a correction layer can
   emit is 35 pp worse overall and zero on history questions. Hiding superseded records deletes the
   answer to a third of the corpus.
3. **The headroom that does exist is in RETRIEVAL, not resolution.** oracle_state 0.870 vs mnemo 0.545
   on the same probes — direction only, NOT budget-matched (200-800 chars vs ~11.9k, retrieval removed
   entirely), so no quantified "headroom = 0.325" claim is admissible.
4. **Therefore the product case for the correction layer cannot be made on QA accuracy.** It has to be
   made where hiding a superseded value is the point rather than a cost: deterministic state export,
   erasure receipts, right-to-be-forgotten, audit. Or recall must return history AND mark it stale —
   suppression at read time with the history still visible, not deletion.

## Scope and limits

- One answerer (`deepseek-v4-flash`), one judge (`glm-5.2`). "This answerer resolves it" is not "no
  answerer needs help". A second answerer is the follow-up, conditional on wanting to generalise.
- n=54 probes over 8 persona families; P6's subset is n=36. Small.
- Longitudinal setting only (dedupe keeps that copy).
- `oracle_state` leaks the graded answer by construction — it is a control, never a target.
- Not budget-matched to the retrieval arms; see point 3.

---

# ADDENDUM — order control, run in response to the storm pass. It changes two of the conclusions.

The multi-perspective pass surfaced published work that contradicts the headline above, and one
methodological gift I had not controlled:

- **HoH (ACL 2025, peer-reviewed)**: adding an outdated version of a fact costs mainstream LLMs
  **>=20% accuracy even when the current fact is retrieved**, with some models falling below random.
- **Xie et al. (ICLR 2024)**: models adopt conflicting evidence by *coherence and prior agreement*,
  not by recency.
- **Practitioner evidence**: LLMs detect context contradictions barely above chance
  (arXiv:2504.00180); order, not truth, drives the answer (arXiv:2605.14115).
- And our own evidence arm sorted the quotes by (segment, turn) — a **chronological timeline**, which
  a relevance-ranked retriever never produces.

So `oracle_evidence_shuffled` was added: identical quotes, deterministically shuffled per probe (order
changed for 44 of 54 probes), neutral prompt. n=53 (one row dropped, logged).

```
                          accuracy   stale-value (update scenarios)
oracle_state               0.870      0.000
oracle_evidence_neutral    0.833      0.000
oracle_evidence_shuffled   0.736      0.091
oracle_current             0.481      0.045
```

| paired contrast | all | non-history | history |
|---|---|---|---|
| shuffled − ordered | −9.4 pp [−20.8, +1.9] | **+2.9 pp [−5.7, +11.4]** | **−33.3 pp [−55.6, −11.1]** |
| state − shuffled | +13.2 pp [+0.0, +26.4] | +5.7 pp [−8.6, +20.0] | +27.8 pp [+0.0, +55.6] |
| current − shuffled | −24.5 pp [−37.7, −11.3] | −14.3 pp [−31.4, +0.0] | −44.4 pp [−66.7, −22.2] |

## What survives, what changes

**SURVIVES — the null on current-value questions.** Against shuffled evidence on non-history probes,
a resolved state is +5.7 pp, CI [−8.6, +20.0]. Ordering does not matter there either (+2.9 pp, CI
through zero). For "what is the value now", the model resolves the correction itself.

**CHANGES — the ordering was doing real work on HISTORY questions.** −33.3 pp, CI excluding zero, and
the stale-value rate goes 0.000 → 0.091 once order is scrambled. The original claim "the answerer
resolves corrections unaided" was, in part, an artifact of handing it a timeline.

**CHANGES — the −35 pp headline must not be read as "suppressing stale values hurts".** `oracle_current`
strips the stale values AND the surrounding context (dates, employer, reasons). It therefore tests
"current values only" rather than "the same context minus the stale value", and it does NOT contradict
HoH, which runs the clean version of that ablation and finds the opposite direction. The honest claim
is narrower: *a supersession layer that emits only current values loses information these questions
need.*

## Prior art — this is largely a re-derivation and must say so

- Keep-and-mark is the settled answer across four decades: **SQL:2011** system-versioned tables close
  the old row instead of overwriting; **Kimball SCD Type 2** keeps history and reserves overwrite
  (Type 1) for error correction; **CRDT OR-Sets** replaced last-write-wins with tombstones;
  event-sourcing under GDPR uses crypto-shredding rather than deletion.
- "Supersession retires a RECORD, not a VALUE" is **Hansson's kernel contraction (1994)**: removing a
  belief requires cutting every minimal entailing subset, not the one record you indexed.
- **Dong et al. (VLDB 2009)**: copying sources make recency a trap — a stale value repeated across many
  records outvotes a fresh one. That is our fifteen-records observation, published seventeen years ago.

## The one gap that appears to be open

No published study scores a delete/hide design on questions that ask for a fact's **history**.
Benchmarks measure whether the latest value is served. The missing experiment is the 2x2 —
**delete-at-write vs retain-but-suppress-at-read**, scored on current-fact accuracy AND trajectory
recovery. We now hold the retain-but-suppress mechanism (`recall(suppress_stale_values=True)`), so we
can run it.
