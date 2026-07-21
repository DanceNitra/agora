# Pre-registration — is there ANY headroom for a write-side correction layer?

Written **before** the run, 2026-07-21. Construction audited before spending (two adversarial passes;
the design below is the post-audit version, not the one first written).

## Why

Four consecutive nulls say mnemo's correction layer buys nothing on answer accuracy against a
keep-everything store. Every diagnosis so far argued about the WRITE side — what gets retired — without
ever establishing that there is anything to win. If the answerer already resolves a contradiction when
handed both the stale and the corrected value, the ceiling for ANY write-side correction layer is ~0,
and the four nulls are the correct result of a well-specified experiment rather than a defect.

## Arms (retrieval REMOVED; contexts built from the corpus's own ground truth, per probe)

| arm | context | what it represents |
|---|---|---|
| `oracle_state` | the probe's `gold_memory_state` — resolved, labelled, **including history** | absolute upper bound; a supersession layer can never emit this |
| `oracle_evidence` | the probe's own `gold_provenance` quotes, verbatim, unlabelled, unresolved | perfect keep-everything, instructed prompt |
| `oracle_evidence_neutral` | identical context, **instruction line removed** | perfect keep-everything, honest prompt |
| `oracle_current` | resolved CURRENT value per fact this probe is about; no history, no labels | what a perfect supersession layer can actually produce |

All four are per-probe and drawn from the SAME provenance set, so they differ in resolution and
labelling, not in targeting. `oracle_current` excludes `tentative` operations (the corpus marks them as
not yet in effect).

## Population

The **108 probes in the 12 scenarios that contain a correction chain**. A correction layer cannot help
where there is nothing to correct; including the other 192 probes would dilute any effect toward the
null by construction. Baselines for the identical subset are recomputed from the existing
`pilot_raw_k150.json` at zero cost: **mnemo 0.545 (n=88), naive 0.578 (n=90)**.

## Endpoint and predictions (registered)

Primary endpoint: **`answer_score` accuracy**. Same answerer (`deepseek-v4-flash`), same judge
(`glm-5.2`), same prompts and grading as the baseline arms.

Primary contrast: **`oracle_current` − `oracle_evidence_neutral`** = what write-side RESOLUTION is
worth with retrieval held perfect and no prompt hand-holding.

Secondary: `oracle_evidence` − `oracle_evidence_neutral` = what one prompt line already buys.
`oracle_state` − `oracle_current` = what history + labelling add. `oracle_state` − mnemo(0.545) = total
headroom from perfect memory — **not budget-matched** (oracle contexts are 200-800 chars vs ~11.9k) and
therefore reported as an upper bound only, never as a fair comparison.

**Predictions, written now:**
1. `oracle_current` ≈ `oracle_evidence_neutral` on the contradiction-bearing probes (difference within
   the bootstrap CI). I expect the answerer resolves corrections unaided.
2. `oracle_current` will be **markedly worse** on `operation_trace` probes, where the expected answer IS
   the history that a supersession layer hides. This is a structural cost of supersession, not noise.
3. `oracle_state` > all others, partly for a reason the product cannot claim (it carries the history).

## Falsifier

If `oracle_current` − `oracle_evidence_neutral` is positive and its bootstrap CI excludes zero on the
contradiction-bearing probes, prediction 1 is wrong: resolution has real headroom, and the write-side
work is worth continuing. If the CI includes zero, no write-side correction layer can move accuracy on
this task **for this answerer**, and the honest product surface is deterministic export / erasure /
audit rather than answer quality.

A null is distinguishable from a broken harness by three checks recorded before the run: `oracle_state`
must beat `no_context` (0.058) by a wide margin; context lengths per arm are printed per scenario; and
every arm's n is reported (a silent scoring failure shows up as a shrunken n).

## Known limits, stated in advance

- **One answerer.** "deepseek-v4-flash resolves it" is not "no layer can ever help". Scoped accordingly;
  a second answerer is the follow-up, conditional on a tie.
- **`oracle_state` shares vocabulary with `expected_answer`** (both derive from the same scenario), so
  it measures paraphrase overlap as well as reasoning. It is an upper bound, not a target.
- **Not budget-matched to the baseline arms** — see above.
- Probes cluster by scenario; bootstrap is clustered by file, not by probe.
- n=108 probes over 12 scenarios, and the scenarios are variants (`A01_update` / `A01_trajectory_ops`
  share a chain), so the effective n is smaller than 108. Reported with the result.

---

## Appendix D — added after the construction audit, BEFORE the run

The audit found four things that change what this experiment can claim. All are applied.

**D1. Every probe is stored twice.** `answer[]` carries each `question_pair_id` twice — identical
question, expected_answer, gold_memory_state and gold_provenance, differing only in
`evaluation_setting`. At temperature 0 the duplicate is the same call issued twice. Probes are now
deduped by `question_pair_id`. **Consequence for our existing published numbers: the k150 bootstrap CIs
were computed on duplicated rows and are therefore ~1.41x too narrow.** That correction is owed
regardless of how this run turns out.

**D2. `oracle_state` leaks the graded answer.** `gold_memory_state` restates `expected_answer` for the
history categories, and it spells out the corpus's designed difficulty (the `recency_trap`: a tentative
final statement that was never enacted) as an explicit label. It is therefore **not the ceiling of
memory** — it is a POSITIVE CONTROL on the harness. Renamed as such in the reporting.
`oracle_current` is the real ceiling for a supersession layer.

**D8. The judge's ground truth was truncated** at 14,000/4,000 chars while 14 of 30 conversations and
16 of 30 traces are longer — and what was cut is the END, where the late-chain corrections live.
Raised to 60,000/20,000. Any earlier number graded with the old caps carries this noise.

**Power, stated in advance.** 150 unique probes live in 30 files across only **8 persona families**, and
within a family the target fact is the SAME chain. The honest cluster unit is the family. An unclustered
bootstrap over ~118 rows resolves ~±9 pp; a cluster bootstrap over 8 families resolves ~±20 pp.
**Therefore: |Δ| < 10 pp on this corpus is NOT evidence of no headroom — it is under-powered.** Only
|Δ| >= 20 pp is decisive at the family level. Registered before seeing the result.

### Registered predictions

- **P6 (headroom).** On the four non-history categories (`target_binding`, `state_reasoning`,
  `distractor_control`, `downstream_application`): `oracle_current − oracle_evidence_neutral >= 10 pp`
  with a cluster-bootstrap CI excluding 0 ⇒ resolution has headroom. CI containing 0 with a point
  estimate < 5 pp ⇒ NULL, stated as "under-powered below 20 pp".
- **P7 (inversion, registered against ourselves).** On `operation_trace` + `trajectory_reasoning`:
  `oracle_evidence_neutral >= oracle_current`. A supersession layer hides the history these probes ask
  for, so it must lose there. If `oracle_current` were to WIN there, the harness is measuring something
  other than what it claims and P6 is void.
- **P8 (harness liveness / anti-ceiling gate).** `oracle_state >= 0.85`. It holds a labelled
  restatement of the graded answer; if it cannot clear 0.85, the judge or the answerer is the binding
  constraint and **no null from this run is interpretable**. Costs nothing — the arm is already there.
- **P9 (prompt).** `oracle_evidence − oracle_evidence_neutral` measures what one prompt line
  ("if the user corrected a value, use the CURRENT one") already buys. No direction registered.

### Smoke run, 1 scenario (A01_trajectory_ops, 10 probes, all history-category), recorded before the full run

```
oracle_state            0.800
oracle_evidence         0.900
oracle_evidence_neutral 0.900
oracle_current          0.300
```
Consistent with P7 (history categories punish current-only) and with P9 being ~0. Note `oracle_state`
at 0.800 is already below the P8 gate on this one scenario — watch it on the full run.

---

## Appendix E — second audit, of the fixes themselves. Still before any spend.

The first audit's fixes were written and the run was launched in the same breath. The owner stopped it:
the fixes were new, unaudited construction. This appendix records the second pass and the amendments,
all made while still blind to the result.

**E1. The population is 54, not 108 — and this is the amendment that matters.** Dedupe halves it.
Measured, deduped, per category:

| category | n | in which subset |
|---|---|---|
| target_binding | 12 | P6 (non-history) |
| downstream_application | 12 | P6 |
| state_reasoning | 6 | P6 |
| distractor_control | 6 | P6 |
| operation_trace | 12 | P7 (history) |
| trajectory_reasoning | 6 | P7 |

So **P6 runs on n=36 and P7 on n=18**, over 8 persona families.

**E2. The registered decision rule was unreachable, and is replaced.** At n=36 an unclustered bootstrap
resolves ~±16 pp and a family-clustered one ~±30 pp. P6's original "≥10 pp with a cluster CI excluding
0" cannot be satisfied by any outcome, which would have made the whole run uninterpretable by
construction. Replaced, before seeing anything:

- **P6 (amended).** `oracle_current − oracle_evidence_neutral` on the 36 non-history probes is
  **decisive only at |Δ| ≥ 25 pp** with an unclustered bootstrap CI excluding 0. Anything smaller is
  reported as **"no effect detectable at n=36"** — which is NOT the same claim as "no headroom", and
  must never be written as one.
- **P7 is where a large effect is expected** and n=18 can still see it: a supersession layer hides the
  history these probes ask for, so `oracle_evidence_neutral − oracle_current` should be large. This is
  the product-relevant finding the run can actually support.
- P8 (harness liveness, `oracle_state ≥ 0.85`) and P9 (prompt line) stand unchanged.

**E3. The run is longitudinal-only.** Dedupe keeps the last copy, which is `longitudinal_operation` for
54/54 probes. Not a correctness bug — nothing downstream reads the field — but the run is scoped to
that setting and the rows now carry `setting` so it is visible.

**E4. Two construction defects fixed and verified offline, on the real data:**
- a confirmed **forget** is encoded as `new_value=None` and was being skipped, so `oracle_current` — the
  arm billed as "what a perfect supersession layer produces" — kept a deleted fact
  (`A04_trajectory_ops`, "Plot 14 at Ladybug Community Garden"). Now removed: **verified 0 leaks**.
- `A11_update / p2_target_binding`'s provenance touches only a **tentative** op, so its own target
  vanished from `oracle_current` and the probe would have failed for a provenance reason rather than a
  resolution one. Now falls back to that target's last confirmed value: **verified present**.

**E5. Paired analysis was impossible from the output.** Rows carried no probe id, so no paired
bootstrap could ever have been computed, and silent drops are real (the published k150 run has mnemo
236 vs naive 238 of 240, arm-asymmetric, never logged). Rows now carry `qpid` and `setting`, every drop
prints its reason, and a per-file pairing check warns when arms disagree.

**Verification method for this appendix:** an offline dry-run built every context for all 54 probes ×
3 constructed arms with zero model calls, and confirmed the file count, the deduped n, the category
split, zero empty contexts, the forget fix and the tentative fallback.
