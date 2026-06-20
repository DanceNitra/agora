# Agent Research-Team Redesign (2026-06-20)

_Deep multi-agent study: 7 research facets, 64 findings, 10 agents._

## Diagnosis (code-grounded)

Confirmed. The hypothesis pipeline (`hypothesize_and_test` → `synthesize_and_record_hypothesis`) never calls the Lab — it "tests" against literature via an LLM only. The only Lab reference in `execution/` is in telegram_bot.py (a command handler), not in any agent organ. The severe-test rule is architecturally absent from the autonomous loop. I have everything I need.

Here is the diagnosis.

---

# Why 90% of Agora's output is value 0 — a code-grounded diagnosis

The system has three layers that each independently produce value-0 output, and they compound. The root cause is the same in all three: **the gates measure surface form (formatting, "grounded text exists", "a claim sentence was produced"), never the one thing the owner's bar requires — a measured result from a runnable test in the same cycle.** The severe-test rule exists in `CLAUDE.md` and in no executing code path.

## Failure 1 — The QA gate scores formatting, and the "strict" gate scores *prose plausibility*, never a test

Two gates exist, and **neither can tell a real finding from a confident-sounding empty one.**

The legacy rubric in `agent_definitions.py:543` is exactly what the prompt describes — 10 of 14 points are structural:
```python
QUALITY_RUBRIC = {
    "frontmatter_present": 2, "structure_clear": 2, "min_length": 2,   # 6 pts: pure format
    "sources_cited": 2, "wikilinks_present": 1, "tags_valid": 1,
    "no_ai_garbage": 1, "cross_links": 1, "frontier_relevance": 1, "grammar_ok": 1,
}
QUALITY_PASS_THRESHOLD = 6   # i.e. frontmatter+structure+length ALONE = 6 = PASS
```
A note with perfect frontmatter, headers and 15 lines passes at exactly 6 with zero scientific content.

The *active* gate (`vault_company_engine.py:592` → `quality_gate.assess_quality`) is better but is still **a single cheap-LLM "does this deserve a place in a vault?" vibe check** (`quality_gate.py:35-43`). Its only objective backstop is the heuristic (`quality_gate.py:20-33`): pass if `len(body) >= 140 and ("Source:" in c or a (Author 2024) regex matches)`. So the hard, non-LLM criterion for entering the vault is **"≥140 chars and the string 'Source:' appears."** That is satisfiable without any real source — and critically, **there is no check that a Lab run exists, that a number was measured, or that a falsifier could have fired.** This is Goodhart (finding #46) and reward-hacking (#55) operating exactly as predicted: the proxy is "looks grounded," so "looks grounded" is what gets produced 3,211 times.

## Failure 2 — The hypothesis organ violates the severe-test rule by construction (the 8.0M-token / value-38 leak)

This is the single most expensive false-value organ, and the code shows why. The pipeline is `hypothesis_induction.synthesize_and_record_hypothesis` → `_record_one` → `scientist.hypothesize_and_test`. Read what "test" means (`scientist.py:48-61`):

```python
# 2) test it against real literature
papers = await asyncio.to_thread(research, hyp[:100], 5)
raw = await asyncio.to_thread(call_llm, "Test the HYPOTHESIS against the REAL abstracts below...")
```

**The hypothesis is "tested" by asking a cheap LLM whether some abstracts support it.** There is no `/brain/lab/run`, no computational model, no measured number, no falsifier execution. I confirmed this: the only `lab/run` reference anywhere in `execution/` is a Telegram command handler — **zero agent organs call the Lab.** So `_record_one` (`hypothesis_induction.py:183`) writes a row with `knowledge_type='hypothesis'` whose "Verdict / Evidence / Falsifier" are all LLM prose. The flywheel then registers the falsifier as an "open question" (`:191`) that nothing ever runs. This is HARKing/post-hoc (#48, #27) and Sakana's 57%-hallucinated-numbers failure (#19) baked into the architecture. It spends 8M tokens producing rows that are, by the owner's own rule, **not claims at all** — hence value ≈ 0.

## Failure 3 — The Seminar's value contract is "a sentence was produced," not "a claim survived a test"

`seminar.py` is genuinely better engineered than the rest (it has a real value contract, dedup, refusal filter), but its bar is still purely textual. `extract_contribution` (`:314`) records a Contribution if the rapporteur LLM emits a `claim` ≥25 chars that isn't a near-duplicate and isn't a refusal. `verify_contributions` (`:408`) promotes it to "VERIFIED" when:
```python
has_fals = bool((c.get("falsifier") or "").strip())
has_src  = bool(_SOURCE_RE.search(evidence + claim))   # a [[link]] or "(Author 2024)" regex
```
**"Verified" = "the string contains a falsifier field and matches a citation regex."** No falsifier is ever executed; no source is ever checked to exist. So the 4.6M-token seminar produces grounded-looking contributions that score value in the ledger (`value_points()`, `:433`) but ship nothing — the ledger value is real *to the metabolism*, but the funnel's "shipped" count stays at 33 because none of this is a tested result anyone would publish.

## Failure 4 — The metric rewards the proxy, so the loop optimizes the proxy

`funnel.py:32` defines a "grounded" discovery as:
```python
_GROUNDED = re.compile(r"Source:|Hypothesis|Falsifier|Open frontier|\([A-Z][a-z]+ \d{4}\)|et al")
```
**A discovery counts as "grounded" if the word "Hypothesis" or "Falsifier" appears in its text.** This is the Natural-Selection-of-Bad-Science pressure (#47) made literal: the cheapest way to move the funnel is to emit text containing those words. 15,248 → 7,369 "grounded" is largely this regex matching, not real grounding. Meanwhile `metabolism.value_snapshot` (`:84`) *does* correctly reward the right outputs — replication FAILED=4.0, REPRODUCED=2.0, press published=5.0 — which is exactly why the honest ROI is near 0 for hypothesize/seminar/match: **those organs produce things the value ledger doesn't reward, because they never produce a tested artifact.** The metric is actually telling the truth; the organs just aren't built to earn it.

## Failure 5 — The "8 scientist personas" don't run the science; a separate generic corporation does

This is the structural mismatch behind finding #26 ("differentiation is cosmetic"). There are **two disconnected agent systems:**

1. `agent_definitions.py` — the 8 rich personas (Kael/Mira/Orin/… with souls, skills, the assembly-line `WORKFLOW`). But their workflow is the **content-curation factory** ("research brief → evergreen note → idea → bridge → QA"), driven by `vault_company_engine` whose terminal step is `quality_audit` writing a *Quality Report note*. Nothing here runs a Lab, designs a crucial experiment, or replicates a claim. The personas optimize **note volume + formatting**, full stop.

2. `agent_worker.py` (the dungeon `CorporationWorker`) — the loop that actually drives research, but it uses **generic roles** `scout / researcher / cto / ceo / designer / developer / qa` (`CORPORATION_FLOW`, `:32`), **not the 8 personas at all.** Its "evaluation" gate (`:654`) was deliberately softened to `cto_approved or ceo_approved or max(score) >= 60` because the strict AND-gate "rejected ~100%." So the corporation's quality filter is now "either of two LLM judges liked it, or one scored ≥60" — sycophancy-prone (#21), single-model, no diversity (#20), no adversarial step. Its output is a Telegram "ship-review" to Claude's inbox (`_file_ship_review`, `:943`) — i.e., **the corporation does not ship; it pushes the real judgement onto Claude.**

So the personas with the scientific souls never touch the scientific pipeline, and the pipeline that exists has none of the scientific roles. The skills are numbers that never become behavior (#56: "skill numbers are cosmetic labels, not behavioral levers" — `VAULT_ROLE_SKILLS` is literally `('research', 7, 0)` tuples consumed only to print a progress bar in `format_skill_progress`).

## The assembly line guarantees consolidation, not disruption

`NIGHT_CYCLE_CONFIG.phase_order` (`agent_definitions.py:568`) is the fixed linear chain `research_scan → write_notes → generate_ideas → bridge_notes → build_tools → quality_audit`. Orin's idea goes straight to Elara (bridging) and Mira (formatting) — it **never goes to an adversarial interrogator before being written.** This is precisely the large-coordinated-team consolidation failure (#1, #4, #9): no sub-squads, no forced collision, no explorer/exploiter split, and the one critic (Voss) fires last and checks format. The science-of-science findings predict this exact "busy but value-0" outcome.

---

## The precise X→Y the redesign must hit

The diagnosis reduces to **four concrete code-level changes**, in priority order:

1. **Make "verified" mean "a Lab run exists."** The hypothesis/seminar/QA gates currently terminate on text. Change the terminal gate from regex/LLM-prose checks to a **post-execution verification gate** (#18, #49): a finding propagates only if a `lab_results` row with a matching id, `FINISHED` status, and a numeric `measured_value` exists. Today `scientist.hypothesize_and_test` must be extended to actually call `/brain/lab/run` (X = LLM-tests-against-abstracts → Y = runs a minimal computational model and records the number), or the hypothesis is not recorded.

2. **Rip out the formatting rubric.** Replace `QUALITY_RUBRIC` and the `_heuristic` "≥140 chars + 'Source:'" backstop with three machine-checkable gates (#46, #55): claim has a stated falsifier, evidence points to an external DOI/arXiv id (not another vault note), and claim-vector distance > threshold from the 10 nearest notes (anti-degenerating, #54). Delete `min_length`, `wikilinks_present`, `frontmatter_present` from scoring.

3. **Wire the 8 personas into the science pipeline and break the line.** Map the personas onto explorer/exploiter (#4, #31), make Voss an adversarial pre-execution critic that fires *before* Orin's output is written (#8, #14, #44), and add the Rooke+Voss falsifier dyad (#1) that must sign a falsifier + Lab protocol *before* the run (#38). Replace the `CorporationWorker` generic roles with the persona roles, or merge the two systems.

4. **Stop rewarding the proxy.** Change `funnel._GROUNDED` from "contains the word Hypothesis/Falsifier" to "has a verified Lab receipt," and make null/FAILED results first-class value (#42, #50) — the metabolism already does this for replications; the funnel and the dungeon evaluation gate do not.

Key files to change: `server/agora/execution/scientist.py` (add the Lab call — the linchpin), `server/agora/execution/quality_gate.py` + `agent_definitions.py:QUALITY_RUBRIC` (the gate), `server/agora/dungeon_os/agent_worker.py:_process_evaluation` (the softened ≥60 gate) and `CORPORATION_FLOW` (generic→persona roles), and `server/agora/execution/funnel.py:_GROUNDED` (the metric).

## Operating model

Replace the linear 8-agent assembly line and the disconnected generic corporation with ONE pipeline driven by the 8 personas, organized as 2-3 agent SUB-SQUADS per claim (science-of-science: small teams disrupt, large teams consolidate; the 8-agent chain is structurally guaranteed to consolidate). Each agent emits a TYPED STRUCTURED ARTIFACT (not a vault note), and a note is written only AFTER the upstream typed artifacts exist (co-scientist: differentiation must be by output-type + verification-responsibility, not persona). The pipeline is phase-gated by hook policy, not prose: ship() is unavailable until a lab_run artifact with a measured number exists (Formal Skill JSON state machine; EviBound dual-gate: integrity is an architectural property, not model honesty). Compute is rationed by a CHEAP-FIRST HIERARCHY: Kael+Wren (cheapest scouts/mappers) front-filter to a short {claim, domain, novelty} tag; only claims passing a novelty gate AND a knowledge-graph-hole gate escalate to Orin (synthesis) and then to the expensive Rooke Lab run — this is the lever that fixes the 15,248->33 funnel by spending the scarce 3-concurrent LLM budget on the best hypothesis, not the first one generated.

Work flows as a tournament-of-sub-squads on a PRE-REGISTERED claim. Wren surfaces a structural hole and two disconnected vault subgraphs; Kael retrieves the best-grounded finding from each side (converting the hard cross-domain RETRIEVAL problem into the easy 78%-success TRANSFER problem); Orin generates COMPETING hypotheses (Platt strong inference: minimum 2 mutually-exclusive H with a crucial differentiating observable) anchored on >=2 conventional findings + 1 atypical bridge (Uzzi: conventional-anchor+novel-spike is 2x impact). Before any Lab spend, the Rooke+Voss falsifier DYAD jointly signs a pre-commitment block (expected direction, effect-size range, REPRODUCED/FAILED/INCONCLUSIVE decision rule) written immutably to the DB BEFORE the run (pre-registration kills HARKing and 2.25x effect inflation). Rooke runs the minimal computational model via /brain/lab/run + one isomorphic-perturbation variant; Voss runs a structured 4-check adversarial protocol (falsifier? rival? could-it-have-failed? did-it? textbook?) and a pre-mortem. Only after a measured number lands does Mira write the evidence-summary card with a GRADE certainty level. FAILED is a first-class, higher-value output (scarce, distribution-worthy for the Crucible). Aldric orchestrates routing of typed artifacts and reports an Elo/credibility scoreboard; the owner gets a one-line Telegram checkpoint per resolved claim (semi-autonomous mode with selective human gates).

## Value gate (replaces formatting-QA)

A unit of output (hypothesis, contribution, vault card, Crucible entry) counts as VALUE only if it passes a dual architectural gate — integrity is a property of the gates, not of model honesty (EviBound 0% hallucination at ~8% overhead). PRE-EXECUTION APPROVAL GATE (before any Lab/compute): the claim has (a) a stated falsifier, (b) a machine-checkable acceptance criterion / pre-commitment block (expected direction + effect-size range + REPRODUCED/FAILED/INCONCLUSIVE decision rule), (c) an external evidence id (DOI/arXiv) NOT another vault note, and (d) claim-vector distance >threshold from its 10 nearest vault notes AND cosine<0.85 vs the banned-textbook list (anti-degenerating). POST-EXECUTION VERIFICATION GATE (before propagation): a lab ledger row exists with a matching lab_run_id, ok/FINISHED status, and a numeric measured_value; the measured number is compared against the pre-committed prediction; an isomorphic-perturbation variant was run; and Voss's 4-check + 3-slot critique is filled. Only when BOTH gates pass does verified=True and the output reaches the Crucible / curated tier. CRITICALLY: a FAILED or NULL result that passes both gates is full value (>= a confirmed finding) — it is the scarce, falsifiable, distribution-worthy commodity. Formatting (frontmatter, wikilinks, length, headers) is UNSCORED. The single sentence: nothing counts as value unless a pre-registered, falsifiable claim was severely tested by a runnable Lab in the same cycle, produced a measured number compared to its prediction, survived an adversarial critique and an isomorphic perturbation — and a null result that meets this bar counts the same as a positive one.

## Cooperation loop

- 0. PRE-REGISTER: a candidate theme is checked against the banned-textbook-results list (cosine<0.85) and the vault novelty index. Degenerating/duplicate -> POST /brain/gatekeeper/skip, no compute spent (Lakatos progressiveness gate).
- 1. MAP (Wren, cheap): emit the top-ranked structural hole = two disconnected vault subgraphs. Once/cycle inject a forced-collision pair.
- 2. RETRIEVE (Kael, cheap): fetch exactly ONE best-grounded finding (with external id + effect-size audit) from EACH side of the hole. Low-credibility (N<50, no-prereg) findings are flagged, not escalated. This is the cheap-first filter — only claims with two real anchors escalate.
- 3. HYPOTHESIZE (Orin): build a Platt tree of >=2 mutually-exclusive hypotheses, each = conventional-anchor(>=2) + atypical-bridge, each with a crucial differentiating observable; classify Pioneer/Maverick/Vanguard.
- 4. TOURNAMENT (Aldric + Voss judge): if >1 hypothesis, run Elo pairwise comparison; only the top-Elo branch gets the scarce Lab run.
- 5. PRE-COMMIT (Rooke + Voss DYAD sign): jointly write the immutable pre-commitment block — expected direction, effect-size range, REPRODUCED/FAILED/INCONCLUSIVE decision rule, falsifier, and Voss's best-null H- + 3 pre-mortem scenarios — to the DB BEFORE any code runs (pre-registration; no HARKing).
- 6. SEVERE TEST (Rooke): build the minimal computational model, CALL /brain/lab/run, plus one isomorphic-perturbation variant. Record verdict + measured_value + lab_run_id. No measured number -> cycle CANNOT mark done.
- 7. INTERROGATE (Voss): run the 4-check adversarial protocol + 3-slot critique against the measured result; score which pre-mortem scenario was closest. A claim that contradicts its pre-commitment is logged FAILED (first-class), not reframed.
- 8. CURATE (Mira) — ONLY NOW: write the evidence-summary card with a GRADE level justified by the lab receipt. Null/FAILED gets equal-value curation.
- 9. INTEGRATE (Elara): log agent_id+role (transactive memory), update credibility scores, compute structural-diversity score, register cross-domain claims on the 90-day slow-burn ledger.
- 10. SHIP-GATE + CHECKPOINT (Aldric -> owner): Phase-1 auto gate (pre-registered + lab receipt + external source + falsifier) must pass for the vault curated tier / Crucible; then a one-line Telegram checkpoint (hypothesis + measured result + 'ship to Crucible? Y/N'). FAILED replications are flagged as the highest-distribution-value output.
- Sub-squad rule: steps 1-9 run as 2-3 agent DYADS per claim (Wren+Kael gap-hunt dyad, Rooke+Voss falsification dyad), NOT one 8-agent chain. The full 8 assemble only for synthesis/canon merges.

## Per-agent redesign

### Shadow Kael -> Targeted Retriever & Evidence Auditor (explorer, cheapest tier — first filter in the hierarchy). Given Wren's structural-hole coordinates, he retrieves the single best-grounded finding from EACH side of the gap, turning the 6.6% un-scaffolded cross-domain retrieval into the 78%-success transfer setup. He also runs the effect-size/credibility audit on every empirical claim before it can escalate.

**Current problem:** Files free-text 'research briefs' with no quantitative quality filter; in the assembly line he just feeds Mira. His outputs inflate funnel.GROUNDED because the regex matches any text containing source-words. No effect-size audit, no exaptation scan.

**Produces (measurable):** # of escalated claims that carry an external source id + effect-size audit AND survive to a Lab run; share of those that were [MECHANISM_TRANSFER] (cross-domain). Counted, not prose.

**New skills/playbooks:**
- claim-gap-retrieval playbook: given two disconnected vault subgraphs, semantic-search each independently, return exactly ONE highest-grounding finding per side with its source id — done only when a DOI/arXiv id exists
- effect-size audit (mandatory): record reported effect size, sample N, pre-registered? single-lab? Flag N<50 & no-preregistration as 'low-credibility, replicate before citing' (targets the underpowered-single-study inflation that floods the 15k discovery pool)
- exaptation scan: extract a finding's MECHANISM (function, not field label), embed it, semantic-search the open-question pool for a functionally-aligned problem in a DISTANT domain; a hit is tagged [MECHANISM_TRANSFER] and routed straight to Orin

**Remove:** the free-text 'research brief -> hand to Mira' assembly-line step (workflow lines in VAULT_ROLES); crediting raw gap COUNT; credit now requires a retrieved finding with an external id

### Sage Mira -> Critical-Appraisal Curator (exploiter). She writes NOTHING until the upstream typed artifacts (Lab receipt + Voss verdict) exist. Her output is an evidence-summary CARD with a GRADE certainty rating, not an essay. She is also Press/Forge but only on Phase-2-approved, lab-backed claims.

**Current problem:** Writes encyclopedic 'evergreen notes' (definition->examples->consequences->sources) that pass on formatting; quality_audit is not even in her skill set (level 0). She writes the note BEFORE any test exists, so her output is the 3,211 value-0 vault notes.

**Produces (measurable):** # of cards carrying a GRADE level justified by a real lab receipt; # of null/FAILED results curated as first-class (not silently dropped). Note volume is explicitly NOT a metric.

**New skills/playbooks:**
- evidence-summary card with mandatory fields: claim (1 sentence), evidence base (N studies/N subjects), risk-of-bias flags (single-lab/no-prereg/small-N), GRADE level HIGH/MODERATE/LOW/VERY_LOW with explicit justification, replication status (REPRODUCED/FAILED/UNTESTED) — frontmatter is cosmetic and unscored
- GRADE downgrade discipline: correctly LOWER certainty for risk-of-bias/inconsistency/indirectness/imprecision/publication-bias rather than aggregating citations
- null-result curation: a pre-registered Lab null is written with value EQUAL to a confirmed finding (PLoS-ONE equal-treatment removes the positivity filter)

**Remove:** the 'definition->examples->consequences' evergreen-note template as the unit of output; writing any note before a lab_run artifact exists (hook-gated: 'ship' tool absent until then)

### High Priest Orin -> Competing-Hypothesis Generator at domain boundaries (explorer). Receives exactly TWO pre-retrieved findings (one per side of Wren's hole, fetched by Kael) and produces a HYPOTHESIS TREE of mutually-exclusive alternatives, each anchored.

**Current problem:** Generates 3-5 non-competing 'ideas' with an Applicability score, recirculating Agora's own canon (within-graph, ~6% novelty), then hands straight to Aldric/Mira — never to an adversarial interrogator before being written. Pure free-floating novelty with no conventional anchor.

**Produces (measurable):** # of competing-hypothesis trees where >=1 branch was ELIMINATED by a Lab run in the same cycle; mean embedding distance between the two anchor domains (cross-domain depth). A tree with no falsifiable branch produces zero value.

**New skills/playbooks:**
- Platt strong-inference tree: minimum 2 MUTUALLY-EXCLUSIVE hypotheses (H1 vs H2 vs H3), each with ONE crucial observable that differentiates it — not a list of co-existing ideas
- conventional-anchor + atypical-spike record: output must be [conventional_base_A]+[conventional_base_B (>=2 well-grounded vault findings)]+[atypical_bridge (low co-citation across the corpus)] -> hypothesis; rejected if either part missing
- cross-domain analogy mapping: name source domain, target domain, the shared RELATIONAL structure, and the mapped prediction (operationalizes the measured 78% novelty gain) — and classify each output Pioneer / Maverick / Vanguard for differential routing

**Remove:** the '3-5 ideas with Applicability score -> Aldric/Mira' step; within-graph recirculation of Agora's own canon as the idea source (use external anchors only); IDEAOGENESIS as free idea-listing untethered from a crucial observable

### King Aldric -> Pipeline Orchestrator & CFO of compute. He routes TYPED artifacts through the correct sub-squad (not a linear chain), enforces the cheap-first hierarchy + the 3-concurrent budget, runs the hypothesis Elo tournament, and reports the scoreboard + cost-normalized ROI to the owner.

**Current problem:** 'Builds tools' as a fixed assembly-line step writing tool docs; his orchestration is a linear chain that guarantees consolidation, and he has no quality metric to report. The real orchestration is done by the disconnected generic corporation (cto/ceo).

**Produces (measurable):** value_per_1k_tokens per organ (target <200k tokens/shipped vs current ~1.1M); # of Lab runs spent on top-Elo (vs first-generated) hypotheses; one-line owner checkpoint per resolved claim.

**New skills/playbooks:**
- typed-artifact router: dispatch each agent by task-type, not by predecessor (Voss callable after ANY output; Rooke callable directly by Kael on a replication-worthy claim) — co-evolve routing with skills
- Elo hypothesis tournament: when >1 hypothesis exists, run pairwise Voss-judged comparisons (novel/falsifiable/testable); ONLY the top-Elo hypothesis gets the expensive Lab run (spends scarce compute on the best, not the first)
- compute-CFO ledger: track value_per_1k_tokens per organ; enforce a floor; cut budget from organs below it (seminar/match) and shift to high-ROI organs; quarterly quota review

**Remove:** the 'build_tools -> write tool doc' assembly-line step as a value-bearing output; the parallel generic CORPORATION_FLOW (cto/ceo/designer/developer/qa) — merged into the persona pipeline so judgement is no longer punted to Claude's inbox via _file_ship_review

### Dame Elara -> Generalist-Integrator & Knowledge-Graph Auditor (the T-shaped broker, finding division-of-labor + Burt structural-holes). Her activity is cross-domain synthesis with permission to pull from ANY agent's findings, not the adjacent step. She maintains the transactive-memory layer.

**Current problem:** 'Bridge builder' adds backlinks/MOCs after notes exist — a cosmetic graph-topology step that produces value-0 link notes and reinforces existing clusters rather than bridging structural holes.

**Produces (measurable):** structural-diversity score distribution of shipped ideas (target: rising share with >=3 bridged components); accuracy of the credibility ledger (does down-weighting low-credibility sources reduce later FAILED rate).

**New skills/playbooks:**
- knowledge-graph-hole audit: compute structural-diversity score per idea at runtime — count how many DISCONNECTED components of the vault graph it bridges (>=3 = structurally diverse, <2 = incremental); this score, not a 1-10 skill number, gates idea-type outputs
- transactive-memory ledger: log agent_id + role on every Crucible entry/hypothesis/contribution; maintain a per-domain agent credibility score (Rooke's Lab pass rate on causal claims, Voss's QA false-positive rate); downstream citations weight by it
- slow-burn cross-domain ledger: track Orin's cross-domain hypotheses on a 90-day clock (expertise diversity predicts 10-yr not 2-yr impact) so the gatekeeper doesn't prune the best cross-domain ideas for showing no immediate signal

**Remove:** the 'add backlinks/MOC' assembly-line step as a value output; treating all agent outputs as equally reliable (no credibility weighting)

### Sergeant Voss -> Adversarial Interrogator & Required Dissenter (exploiter) — fires BEFORE Orin's output is written and co-signs the falsifier with Rooke before any Lab spend. Protocol role, not personality: she must always argue the strongest null even if she agrees.

**Current problem:** The designated critic, but the QA gate checks FORMATTING and fires LAST, after the framing has locked in. She cannot tell a real finding from a confident empty one. This is the structural reason groupthink/sycophancy is unchecked (all 8 share one base model and converge).

**Produces (measurable):** # of claims KILLED before Lab spend (catching false positives is the reward, not passing them); calibration of her pre-mortem predictions vs actual Lab outcomes (a self-scoring QA track record); textbook-redundancy catch rate.

**New skills/playbooks:**
- 4-check structured adversarial protocol (replaces the formatting rubric): (1) what is the falsifier — what result kills this claim? (2) does a runnable Lab baseline exist? (3) is this a textbook result dressed up (cosine<0.85 vs banned-results list: collider bias, volatility drag, regression-to-mean)? (4) what is the strongest counter-evidence in the literature? Cannot answer all four -> rejected, not reformatted
- required-dissent + best-null: write the strongest version of the rival/null hypothesis in writing before Rooke designs the test; the test must be ADJUDICATIVE between Orin's H+ and Voss's H- (Platt step 2); generate exactly 3 pre-mortem failure scenarios committed to the DB before data is seen, then score which was closest
- 3-slot critique template (ICLR-style targeted feedback): (a) one specific vague claim needing a number/citation, (b) one unjustified inference, (c) confirm/refute the falsifier is testable as written; hypothesis passes only if all 3 slots filled and (a)+(b) resolved in revision

**Remove:** the QUALITY_RUBRIC formatting checks entirely (frontmatter/structure/min_length/wikilinks/tags/grammar — 9 of 14 cosmetic points); firing LAST in the chain (she now fires before write AND can be invoked after any agent's output)

### Artificer Rooke -> Confirmation Scientist (exploiter) operating OUTCOME-INDEPENDENT from the discovery pipeline — fed by an EXTERNAL claims queue (Folklore Index / Crucible) from Kael's scan of real papers, not internal hypotheses. He is the linchpin: the ONLY agent that turns text into a measured number via /brain/lab/run.

**Current problem:** Downstream of Orin, replicating hypotheses the system already wants to be true; runs full replications only, with no automatic contradiction detector between predicted and measured effect, and no isomorphic-perturbation check (this is exactly how the '+144%' artifact passed one test and failed every variant).

**Produces (measurable):** verdicts/week resolved with a runnable Lab receipt (FINISHED + measured number); share that are FAILED/PARTIAL (the scarce, distribution-worthy commodity); zero claims propagating without a matching lab_run_id.

**New skills/playbooks:**
- minimal-replication playbook as an executable skill (Voyager-style, code not prose): inputs (claim_text, source_doi, domain) -> steps (search_literature, build_minimal_model, CALL /brain/lab/run, record_verdict) -> outputs (verdict REPRODUCED|FAILED|NOT_COMPUTABLE, measured_value, lab_run_id). Termination FAILS if measured_value is null — the cycle cannot mark done
- pre-commitment block (immutable, written BEFORE the run): expected direction, expected effect-size range, decision rule for REPRODUCED/FAILED/INCONCLUSIVE; result compared against pre-commitment, never post-hoc
- three-check + isomorphic perturbation: (a) script executes? (b) measured number matches OR contradicts the prediction? (c) statistically meaningful (not a 1-second one-run diff)? PLUS one logically-equivalent variant (different k / domain) in the same Lab run -> passes original but fails variant = PARTIAL_REPRODUCED, not REPRODUCED
- lightweight statistical-reviewer pass (15-line check) on EVERY promoted finding: plausible effect size given N, appropriate (not weak) baseline, CI reported — catches the value-0 notes Voss's old gate let through

**Remove:** being fed internal hypotheses the system wants confirmed (now pulls from an external claims queue); scoring replication SUCCESS rate (now scored on VERDICT RATE; FAILED == REPRODUCED in value, and FAILED logged as HIGHER-value for the Crucible)

### Cartographer Wren -> Structural-Hole Broker & Institutional Outsider (explorer, cheapest tier — second front-filter). Her ranked structural-hole list is the ONLY permitted source for Orin's atypical bridges (Burt: the broker hands the gap coordinate to the hypothesis generator). Her gap-detection EXCLUDES existing vault themes (the outsider who isn't anchored to the paradigm).

**Current problem:** Charts the graph as a background mapping task that produces value-0 cartography notes; anchored to existing vault themes, so it reinforces the monoculture instead of finding the holes that drive disruption.

**Produces (measurable):** # of structural holes that produced a Lab-tested cross-domain claim; structural-diversity lift of forced-collision cycles vs normal cycles; under-explored-Board-domain coverage.

**New skills/playbooks:**
- ranked structural-hole list: emit pairs of vault subgraphs with high internal connectivity but near-zero bridge edges, ranked; publish to the squad BEFORE each ideation cycle — Orin draws only from this
- forced-collision protocol: once per cycle surface TWO findings from agents with NO recent co-occurrence and force Orin to attempt a bridge (the programmatic substitute for the hallway accident)
- frontier-mapping vs Board: chart which domains are under-explored relative to the owner's Board priorities; blank-slate scout cycles (Kael scouts with NO similarity-to-existing-notes boost) and track whether blank-slate cycles produce higher structural-diversity contributions

**Remove:** passive cartography notes as a value output; anchoring gap-detection to existing vault themes (now explicitly excludes them)

## Kill list

- scientist.py 'test against literature via call_llm' as the hypothesis test — it is not a test (no number, no falsifier execution); the 8.0M-token/value-38 leak
- QUALITY_RUBRIC formatting scoring (agent_definitions.py:543) — frontmatter_present, structure_clear, min_length, wikilinks_present, tags_valid, grammar_ok, cross_links (9 of 14 cosmetic points) and QUALITY_PASS_THRESHOLD=6
- quality_gate._heuristic backstop 'len(body)>=140 and (Source: in c)' as a vault-entry criterion
- funnel._GROUNDED regex matching the literal words Hypothesis|Falsifier|Source: — replace with a verified-lab-receipt count
- seminar verify_contributions promoting to VERIFIED on (falsifier string non-empty AND citation-regex match) with no execution — and the 4.6M-token/value-0 seminar as currently gated
- the disconnected generic CORPORATION_FLOW (scout/researcher/cto/ceo/designer/developer/qa) and its softened 'cto_approved OR ceo_approved OR max(score)>=60' gate (agent_worker.py:654) that rejected nothing
- _file_ship_review punting the real quality judgement to Claude's inbox instead of resolving it with a Lab
- VAULT_ROLE_SKILLS ('research',7,0) numeric tuples as behavior — they only drive a progress bar; replace with applicability-triggered playbooks
- the linear NIGHT_CYCLE_CONFIG.phase_order assembly line (research_scan->...->quality_audit) that guarantees consolidation
- note VOLUME and token THROUGHPUT as agent credit metrics (the Natural-Selection-of-Bad-Science publish-volume pressure)
- Big-Five trait strings injected into the LLM system prompt during scientific tasks (persona prompts cost up to -0.65 on knowledge-retrieval); keep souls for the 3D world + trust only
- the 'evergreen note' and 'tool doc' and 'cartography note' and 'MOC backlink' as value-bearing outputs

## Implementation steps (as proposed)

1. STEP 1 (THE LINCHPIN, reversible): in scientist.py add a real Lab call. After Orin's hypothesis, build a minimal computational model and POST to the existing /brain/lab/run (lab.run_experiment already executes Python and returns {id, ok, output}). Add a pre_commitment dict (direction, effect-range, decision rule) BEFORE the run. Replace the call_llm 'verdict' with a verdict derived from the measured number vs pre-commitment. If no lab_run_id with ok=True and a parsed measured number, return verdict NONE and DO NOT record. Keep the old code path behind an env flag AGORA_SCIENTIST_LAB=1 for instant revert.
2. STEP 2 (gate, reversible): in hypothesis_induction._record_one and seminar.verify_contributions, change the terminal check from regex/string to a post-execution verification gate: require a lab ledger row with matching lab_run_id + ok/FINISHED + numeric measured_value. Add verified=True only then. Guard behind AGORA_VERIFY_LAB_RECEIPT=1.
3. STEP 3 (rip out formatting): replace agent_definitions.QUALITY_RUBRIC + QUALITY_PASS_THRESHOLD and quality_gate._heuristic with three machine-checkable functions: has_falsifier(claim), evidence_is_external(text) (DOI/arXiv regex, reject if only a [[vault link]]), novelty_distance(claim) > threshold via SemanticIndex over the 10 nearest notes AND cosine<0.85 vs a banned-textbook list. Delete min_length/wikilink/frontmatter scoring. py_compile, keep old rubric constant present-but-unused for one cycle for revert.
4. STEP 4 (metric honesty): change funnel._GROUNDED from the word-matching regex to a count of discoveries that carry a verified lab_run_id; make FAILED/NULL lab results value 1.0 in funnel + metabolism value_snapshot (metabolism already does for replications — extend to hypotheses/seminar). Pure read-side change, trivially reversible.
5. STEP 5 (break the line + wire personas): introduce a SUB_SQUADS map and a typed-artifact router in the engine. Make Voss callable BEFORE write (pre-execution critic) and Rooke callable directly by Kael. Replace NIGHT_CYCLE_CONFIG.phase_order with the new cooperation loop as a phase state-machine (HYPOTHESIS_SKILL_PHASES=['map','retrieve','hypothesize','pre_commit','lab_run','interrogate','curate','ship']) where 'ship'/'curate' tools are unavailable until 'lab_run' wrote a measured_value (Formal-Skill hook policy). Behind a feature flag; old phase_order retained.
6. STEP 6 (merge the two agent systems): repoint dungeon_os CORPORATION_FLOW generic roles to the 8 personas, OR have agent_worker call the brain hypothesis/lab pipeline instead of the cto/ceo soft gate. Replace the >=60 OR-gate with the dual value gate. Replace _file_ship_review-only with: resolve via Lab first, file to inbox only the Phase-2 ambition/novelty judgement.
7. STEP 7 (skills as behavior): replace VAULT_ROLE_SKILLS numeric tuples with one applicability-triggered playbook file per agent (the new skills above), loaded by a SkillContextBuilder(agent_name, task_type) that injects ONLY the relevant playbook + scoped tools — not all 14 skills, not the Big-Five string. Reduce to <=8 maximally-distinctive skill names (Kael=claim-gap-retrieval, Orin=cross-domain-hypothesis, Rooke=minimal-replication, Voss=scientific-claim-stress-test, etc.) to avoid the skill-selection phase transition.
8. STEP 8 (pre-registration + Crucible integrity): add a pre_registered_hypotheses DB table written BEFORE /brain/lab/run; every hypothesis entering the Lab gets a pre-registered Crucible entry with predicted outcome, post-run actual fills in automatically — so ALL attempts (REPRODUCED/FAILED/NOT_COMPUTABLE) are logged in public crucible.json (kills post-hoc selection bias).
9. STEP 9 (owner control surface): after each resolved hypothesis_loop cycle, fire one ASCII Telegram line (hypothesis + measured lab result + 'ship to Crucible? Y/N'); FAILED replications flagged as highest distribution value. Semi-autonomous selective checkpoint, not a disruption.
10. STEP 10 (verify + commit discipline): py_compile each changed module, restart only the brain, verify health 200 + exactly one :8000 listener, run one end-to-end cycle, confirm a hypothesis now carries a real lab_run_id and a FAILED result earns value. Each step is a small separate reversible commit behind its flag; REVERT on any breakage. At most one self-upgrade landed per cycle.

## Skeptical-director critique (the refinement that matters)

I now have everything I need. The metric is confirmed: `metabolism.py:111` rewards `FAILED=4.0, REPRODUCED=2.0`, `press=5.0`. And critically, line 159: `hypothesize` spend is mapped to `flywheel` value — so hypothesize's ROI is measured against deepened falsifiers, which it never produces. The diagnosis is correct that the metric is honest and the organs don't earn it.

I have verified the diagnosis against actual code. I can now write the stress-test as a skeptical research director, grounded in what the code actually does.

---

# Stress-test: "Severe-Test Pipeline" redesign

I verified the diagnosis against the actual source before judging it. Bottom line: **the diagnosis is the strongest part of this document and is almost entirely correct in the code.** The redesign is directionally right but over-built, and it has one factual error and one structural blind spot that change the risk picture. Specifics below.

## Diagnosis accuracy (I checked the lines)

Confirmed true against code:
- `scientist.py:48-61` "tests" via `call_llm` over 5 abstracts, no number, no Lab call, all on the **cheap** tier. Correct.
- `quality_gate.py:29-33` heuristic passes on `len(body)>=140 and ("Source:" in c or cite-regex)`. Correct.
- `agent_definitions.py:543-557` `QUALITY_RUBRIC` gives 6/14 to format and `QUALITY_PASS_THRESHOLD=6`, so format alone = PASS. Correct.
- `seminar.py:422-425` promotes to `verified=True` on `has_falsifier (non-empty string) AND _SOURCE_RE match` — no execution. Correct.
- `funnel.py:32` `_GROUNDED` regex matches the literal word `Hypothesis|Falsifier|Source:`. Correct — "grounded" is largely regex-matching.
- `agent_worker.py:654` soft gate `cto_approved or ceo_approved or max(score)>=60`. Correct.
- `metabolism.py:111,124` `FAILED=4.0, REPRODUCED=2.0, press=5.0`, and line 159 maps `hypothesize`→`flywheel` value. Correct — the metric is honest; the organs don't produce the tested artifact it rewards.

**One material error.** The claim "ZERO agent organs call `lab.run_experiment()` … the only reference is the Telegram handler and the API endpoint" is **false**. `methods.py:382-400` (`run_method`) already calls `run_experiment()`, runs a vetted template, and parses `MEASURED:`/`VERDICT:` lines from stdout. This matters because: (a) the "linchpin" of building a programmatic Lab path is *partly already built and working* — Step 1 should extend `methods.py`, not pioneer from `scientist.py`; and (b) `methods.py` is the existing Methods Library the owner's own memory says is "the compounding loop." The redesign never mentions it. That is a real gap in the author's read of the codebase, and it changes the smallest-first-step answer (see Q4).

---

## (1) Real value, or a new Goodhart target?

**Both, and the document half-admits it.** The redesign correctly moves the gate from format to a measured Lab number. That is a genuine improvement — you cannot fake a `lab_run_id` with a `FINISHED` status and a parsed float as cheaply as you can fake frontmatter. But it introduces a fresh, richer surface to game, and the proposal's own metrics invite it:

- **The new churn is "trivial Lab runs."** `lab.py` executes *any* Python with a 60s timeout and records `ok=True` if returncode==0. A script that prints `MEASURED: 0.5\nVERDICT: REPRODUCED` passes every gate in the document: it has a `lab_run_id`, `ok=True`, a numeric `measured_value`. The whole edifice (pre-commitment, isomorphic perturbation, GRADE card) rests on the *content* of a script the cheap model influences. The gate checks that a number exists, not that the number measures the claim. **This is the central Goodhart risk and the document does not close it** — "EviBound 0% hallucination" is cited as if architecture alone solves it, but EviBound gates tool-call execution, not whether the executed code is a relevant test. You will get 15,248 → N trivial-but-passing Lab runs unless something judges *test validity*, and the only thing that can judge that is an expensive reasoning pass — exactly the compute you're rationing.

- **"FAILED == REPRODUCED in value, FAILED logged higher"** (metabolism already does this: 4.0 vs 2.0) is the most dangerous incentive in the redesign. You are paying agents *more* for FAILED replications and telling them FAILED is "distribution-worthy." Under a publish-volume selection pressure (which the document elsewhere names as the enemy), this directly incentivizes **manufacturing FAILED verdicts** — picking weak baselines, underpowered runs, or perturbations chosen to break. The Crucible's credibility *depends* on FAILED being honest, and the reward structure pushes the other way. The pre-commitment block mitigates HARKing but not baseline-shopping *before* pre-commitment. This needs an explicit guard: a FAILED verdict should require Rooke to show the REPRODUCED-direction baseline was fair (e.g., the same model reproduces a known-true control claim in the same harness).

- **Net:** value is real *if and only if* test-validity is judged. Without that, you've traded "format churn" (cheap, visibly worthless) for "trivial-Lab churn" (more expensive, and worse because it *looks* like science and pollutes the public ledger). The honest answer to the owner is: this will produce real value on the 10-50 claims/week a reasoning model can actually vet, and noise on everything below that line. Size the pipeline to that throughput, don't let the funnel-count metric pull it wider.

---

## (2) Weakest agent redesign

**Dame Elara is the weakest — least likely to change behavior and most likely to become the new value-0 organ.** Her three new skills (structural-diversity score, transactive-memory credibility ledger, 90-day slow-burn ledger) are all *bookkeeping over other agents' outputs*. None of them produces a tested artifact, so under the document's own value gate Elara structurally **cannot earn value** — she's in exactly the position `hypothesize` is in today (`metabolism.py:159` maps her downstream, she never lands the artifact). The "credibility-weighted citations" and "90-day clock" are speculative meta-features with no measurement that they reduce later FAILED rate; that's the kind of plausible-but-untested machinery the owner explicitly rejected. Elara is the agent most at risk of being kept for narrative symmetry (8 personas) rather than function. **Recommendation: in v1, Elara does nothing but the structural-hole audit that Wren needs, or she's cut from the pipeline and kept for the 3D world only.**

Second-weakest: **Cartographer Wren and Shadow Kael are nearly redundant** under the new design — both are "cheap front-filter," Wren emits hole-pairs and Kael retrieves one finding per side. That's one job (gap→two-anchors) split across two agents for persona reasons. The science-of-science "small teams" justification cuts the *other* way here: a 2-agent dyad to produce two retrievals is overhead. Fine to keep both for the world, but the pipeline logic is one step.

Strongest, by contrast: **Rooke and Voss**. Rooke's "termination FAILS if `measured_value` is null" and Voss's "fires BEFORE write + co-signs pre-commitment" are the only two changes that are both behavioral and architecturally enforceable. Build those two; they carry the redesign.

---

## (3) Is the value gate truly enforcing science, or gameable?

**It enforces *more* than today, but it is gameable at three seams, and one of them is fatal:**

1. **Test-relevance seam (fatal, covered above).** The post-execution gate checks `lab_run_id + FINISHED + numeric measured_value + isomorphic variant`. None of that verifies the script tests the hypothesis. `ok=True` means "Python didn't crash." A model that learns the gate will emit minimal scripts that print a number and a matching perturbation. The gate measures *that a measurement happened*, not *that the right thing was measured*. This is the difference between an architectural integrity gate and a science gate; the document conflates them.

2. **External-ID seam.** `evidence_is_external()` = DOI/arXiv regex. A real arXiv ID that doesn't actually contain the claimed result passes (this is *exactly* the failure mode in your own memory: the "+144%" artifact and the "verify before citing" lesson — a citation existing ≠ a citation supporting). The gate checks ID *shape*, not that the source *states the result*. `scientist.py:53-57` already tries to enforce "cite ONE SPECIFIC result with author/year" via prompt; moving it to a regex is *weaker*, not stronger, on this axis.

3. **Novelty seam.** `novelty_distance > threshold AND cosine<0.85 vs banned-textbook list`. The banned list is finite and hand-curated (collider bias, volatility drag, regression-to-mean). Textbook results not on the list pass; and a model can paraphrase a textbook result above 0.85 cosine. Embedding-distance novelty is a known-leaky proxy (your own lab notes on lexical-vs-embedding recall show this). It will catch the three named results and little else.

**Verdict:** the gate is a real upgrade on the *format* axis and a genuine enforcement of "a number must exist." It is **not** an enforcement of "the number tests the claim" or "the source supports the claim." Those two — the actual core of science — remain dependent on a reasoning-model judgment the design tries to ration away. The single-sentence summary in the proposal ("severely tested by a runnable Lab … produced a measured number compared to its prediction") is true and still insufficient, because "severely" is doing unverified work.

---

## (4) Biggest implementation risk + smallest first proof

**Biggest risk: the 10-step plan is a coupled rewrite masquerading as 10 reversible steps.** Steps 5-7 (break the assembly line, introduce SUB_SQUADS + typed-artifact router, replace skills with playbooks, merge the two agent systems) are a from-scratch re-architecture of both `agent_definitions.py`'s night cycle AND `dungeon_os/agent_worker.py`'s corporation flow into one new pipeline. That is not "one self-upgrade per cycle, revert on breakage" — it's a multi-week migration where the feature flags interact (a half-migrated router with an old phase_order is a third, untested state). The CLAUDE.md hard rule is "at most ONE self-upgrade per cycle." This plan violates the spirit of that rule even though each step is nominally flagged. **The risk is that you spend the scarce compute and weeks of build on the orchestration scaffolding (squads, Elo tournaments, credibility ledgers, 90-day clocks) before proving the one hypothesis the whole thing rests on:** *that an agent-driven Lab run with a pre-commitment actually produces a non-trivial measured verdict at acceptable cost.*

**Smallest first change that proves (or kills) the redesign — do ONLY this, this cycle:**

Wire the *existing* `methods.py:run_method` path (which already calls `run_experiment` and parses `MEASURED:`/`VERDICT:`) into `scientist.py` as the test step, behind `AGORA_SCIENTIST_LAB=1`. Concretely:

1. In `scientist.py`, after the hypothesis is generated (line 47), add a pre-commitment dict `{direction, effect_range, decision_rule}` from one cheap LLM call, write it to a new `pre_registered` JSON **before** the run.
2. Call `methods.match_and_run(hyp)` (already exists, line 403) instead of the abstract-vibe-check at lines 51-61. If it returns a template match + a parsed `MEASURED:` number, derive the verdict from number-vs-pre-commitment. If no match or `measured` is empty, return `verdict="NONE"` and **do not record**.
3. Change `metabolism._SPEND2VALUE["hypothesize"]` so hypothesize value reads the new lab-backed ledger, not `flywheel`.
4. Run ONE cycle. Measure exactly three numbers:
   - **What fraction of generated hypotheses actually match a Methods template and produce a real number?** (If it's near-zero, the whole "agents do severe tests" thesis is false at current template coverage — and *that* is the thing to fix first, by adding templates, not by building squads.)
   - **Cost per resolved verdict** (tokens). Compare to the document's ~200k/shipped target.
   - **Eyeball 5 verdicts: does the measured number actually bear on the hypothesis?** This is the manual proxy for the test-relevance seam you can't yet automate.

This is ~50 lines, reuses two working functions (`run_method`, `match_and_run`), touches one read-side metric, is trivially revertible by the flag, and **directly tests the load-bearing assumption** (agents can produce real measured verdicts cheaply) before you commit to squads, routers, Elo, GRADE cards, and credibility ledgers. If hypothesis-to-template match rate is too low, you've learned the real bottleneck is *Lab coverage*, not *agent orchestration* — and you've saved weeks. If it works, you've got a measured ROI number to justify the bigger build to the owner.

---

## Honest summary for the owner (one paragraph)

The diagnosis is correct and unusually well-evidenced — every gate does accept text instead of a measured result, and the metric already rewards the right things, which is why the big organs score zero. The redesign fixes the right wound (move the gate from format to a Lab number) but is over-engineered: roughly half the new machinery (Elara's ledgers, Elo tournaments, 90-day clocks, sub-squad tournaments) is unproven meta-structure that adds cost and new gameable surfaces before the core claim is tested. The core claim is *not yet proven*: that agents can produce a non-trivial measured verdict cheaply. The gate enforces "a number exists," not "the number tests the claim" or "the cited source supports it" — the two things that actually make it science — and those still need an expensive reasoning pass the design tries to avoid. The author also missed that a working Lab-calling organ (`methods.py`) already exists, which is both an error and good news: the smallest proving step is to route `scientist.py` through that existing path behind a flag and measure hypothesis→template match rate, cost-per-verdict, and test relevance on five cases — before building any of the orchestration. Biggest danger if you skip that: you pay agents *more* for FAILED replications, so under volume pressure they'll learn to manufacture FAILED verdicts and poison the one asset (the Crucible) whose entire value is that its FAILEDs are honest.

Relevant files: `C:\Users\Danculus\agora\server\agora\execution\scientist.py`, `C:\Users\Danculus\agora\server\agora\execution\methods.py` (the missed existing Lab path, lines 382-400), `C:\Users\Danculus\agora\server\agora\execution\lab.py` (line 53: `ok = returncode==0` — the trivial-run hole), `C:\Users\Danculus\agora\server\agora\execution\quality_gate.py`, `C:\Users\Danculus\agora\server\agora\execution\funnel.py` (line 32), `C:\Users\Danculus\agora\server\agora\execution\seminar.py` (lines 422-425), `C:\Users\Danculus\agora\server\agora\execution\metabolism.py` (lines 111, 124, 159), `C:\Users\Danculus\agora\server\agora\agent_os\vault_company\agent_definitions.py` (lines 543-578), `C:\Users\Danculus\agora\server\agora\dungeon_os\agent_worker.py` (lines 654, 960).
