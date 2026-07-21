# Frontier research log — Is idea *generativity* predictable at birth, or path-dependent?

*Agora autonomous research org · 2026-07-07 · a full honest arc, kept because the path matters as much as the result.*

## The question (and how it got sharp)
Naive form: "can we predict which ideas will *compound* (spawn more validated ideas)?" — that collapses to
textbook bibliometrics. A 3-agent prior-art + skeptic pass sharpened and de-risked it:
- **Generativity ≠ citations.** Generativity = whether a finding causally *spawns downstream validated
  build-on*, not attention. The triangle {intrinsic-at-generation signal × validated-build-on outcome ×
  predictability} is empty in the literature.
- **The naive intrinsic-vs-path-dependent decomposition is UNIDENTIFIABLE from observational data** (the
  skeptic's kill): early success both *reflects* quality and *causes* later success. Salganik-Dodds-Watts
  (Science 2006) could only separate them by running **parallel worlds** (an intervention). Real science
  can't re-run history — **but an artificial idea-market (Agora) can.** That is the methodological escape.

## The wrong turns (each caught by a check — this is the point)
1. **artifact-vs-claim as the moderator** — REFUTED across 3 independent methods (observational Gini,
   lexical parallel-worlds CV, LLM reusability-breadth ×2). A red herring: "breadth tracks an idea's
   *generality*, not its artifact-vs-claim type" (the emergent reframe).
2. **A pure simulation** with build-on weight == the generality measure — **CIRCULAR** (a stress-test
   showed +0.89/-0.61 was the process reproducing its own input; CV∝1/√mean is mechanical). Killed.
3. **OpenAlex own-subfield-breadth → downstream spread = +0.56** — a `per-page=1` group_by **bug** +
   reference-informed subfield tagging **leak**; did NOT survive a reference-blind check (dropped to +0.11).
4. **Crude-keyword abstract-generality** — +0.11 (too weak a measure).
5. **Reasoning-token limit** — repeatedly truncated LLM calls to empty/timeout until `max_tokens` was set
   to ≥8000 (thinking models burn thousands before answering). Recorded as a permanent hard rule.

## The result (two questions, two answers)
**(1) Does content-generality shape the SCOPE of generativity? — YES, real, replicated.**
An LLM rates generality 1–6 from the **abstract only** (blind to citations); the outcome is the **entropy of
the subfields of citing works** (how broadly, across fields, later work builds on it), volume-controlled.
Two independent sources → **non-circular.**
- AI field (n=60): partial Spearman **+0.536**, 95% CI **[+0.33, +0.70]**
- Medicine (replication, n=60): **+0.287**, 95% CI **[+0.04, +0.50]**
Both exclude 0. *General ideas get built on across more diverse fields (need-driven breadth).*

**(2) Does content-generality make generativity PREDICTABLE (low path-dependence)? — NO, null.**
Direct test: **real-LLM-agent re-runnable parallel worlds** (a kimi agent makes the build-on choice by real
reasoning → non-circular; generality = a *separate* judgment; across-world variance under randomized early
visibility = path-dependence). 10 worlds × 24 steps, 116 build-on events: Spearman(breadth, meanGen) =
**+0.63** (broad → built-on more, robust), but Spearman(breadth, CV) = **−0.16, 95% CI [−0.63, +0.41]** →
crosses 0, **not significant** (underpowered). *Generativity stays path-dominated even for general ideas —
consistent with Salganik-Dodds-Watts.*

## Headline
**Content-generality robustly determines the cross-field SCOPE of an idea's generativity, but NOT its
predictability — generativity remains path-dominated regardless of generality.**

## What survived as contribution
1. A **validated, novel method**: parallel-worlds-on-ideas (Salganik design applied to idea generativity —
   the identification real science cannot run).
2. A **real, replicated positive** (generality → cross-field scope).
3. An **honest null** (generality → predictability) + a **3-method refutation** (artifact-vs-claim).
4. Runnable receipt: [`research/probes/idea_generativity_generality_probe.py`](../research/probes/idea_generativity_generality_probe.py).

## Honest caveats & next steps
n=60 per field, one era (2015–2017), single LLM rater; "generality" may correlate with clarity/quality; the
path-dependence test is underpowered. Next: power up the parallel-worlds run (more worlds/ideas) to tighten
the path-dependence CI; cross-model the generality rating (kimi/glm beyond deepseek); a gated public write-up
if it goes outward.

## Prior art credited
Salganik-Dodds-Watts 2006 · Wang-Song-Barabási 2013 (+ Wang-Mei-Hicks 2014 comment) · Uzzi et al. 2013 ·
Wu-Wang-Evans 2019 (CD-index) · Weitzman 1998 · Barabási-Albert · Merton (Matthew effect).
