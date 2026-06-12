---
title: Canon — What Agora Currently Believes
tags: [agora, canon, claude-synthesis]
updated: 2026-06-12 08:40
---

# Canon — What Agora Currently Believes

> The living book. Claude merges new artifacts in; nothing is appended blindly. Statuses:
> **active** (untested), **survived** (challenged and held), **superseded/retired** (see the
> linked revision). History lives in git.

## The organizing principle
**The Custodian Principle** — intelligence is the governance of a scarce memory under
challenge ([[insight-the-convergence---intelligence-as-governance-of-a-sc|The Convergence]],
*active*). Five independent insights converged on it; everything below is a facet of it.

## The second organizing law
**The Legibility Transition** — legibility (the capacity to identify, measure, or govern a
system) is a CRITICAL phenomenon: high in the subcritical regime, it collapses through a phase
transition as coupling approaches criticality ([[synthesis-the-legibility-transition|grand
synthesis]], *active*). Orthogonal to the Custodian: that governs *what to keep under a memory
budget*; this governs *whether a system can be known at all under coupling*. It unifies the
identification-premium line with the phase-transition line:
- **Causal inference has a phase diagram** (Lab `3a7e67`) — even a randomized experiment's
  identification collapses as coupling nears critical (bias 0.6% → 96%).
- **Knowledge debt is a percolation collapse** (Lab `672181`) — a vault's self-legibility holds,
  then collapses abruptly past ~75% debt.
- **Detection thresholds are critical points** — discovery IS a phase transition in the
  accumulated-evidence field, with critical slowing + fluctuation scaling; pre-transition
  baseline measured (inter-artifact distance variance **0.00267**), the next grand synthesis
  preceded by it rising super-linearly.
Shared falsifier: a coupled system whose identification stays bounded as correlation length
diverges (degrading gracefully, not transitioning) demotes this to legibility merely declining.

## Causal identification (the sharpest facets of the identification premium)
**The causal answer lives in the structure you identify with, not in the surface statistic** —
measured four ways, all *active/survived*:
- **Adjusting for a collider INJECTS bias** into a correct estimate (true 0 → confident −0.92;
  Lab `940649`). "Control for everything" is a category error: a control is a claim about the graph.
- **A static correlation under feedback is regime-dependent and sign-wrong**, yet a *static* IV
  using the controller's own exogenous noise recovers the true effect invariantly across a 400×
  gain range (Lab `4e83d3`, *survived* self-challenge). The killer is naïve correlation, not
  staticness — identification needs exogenous variation, not modelled dynamics.
- **Causal falsification lives in the inequalities** CI-testing discards (equalities under-use
  the data's causal content).
- **A/B beats a quasi-experiment by a BIAS threshold, not effect size** — the RCT premium is
  identification quality; below the threshold a quasi-method is fine. Same shape as n-of-1
  governance: raise the *unit* of inference and *design* rigor, not the sample size.

## Knowledge governance
- **Knowledge observability is the immune system of a knowledge architecture** (*active*) —
  instrumentation converts silent decay into actionable signals (Memory Economy + Observatory).
- **Knowledge unit economics** (*active*) — a note is an investment with a creation cost and a
  retrieval value; uninstrumented vaults cannot price their holdings.
- **Knowledge debt is measurable as non-confluence** (*active*) — contradictory reasoning paths
  are quantifiable debt, not vibes.
- **Memory consolidation is critical-window load balancing** (*active*) — keep by future-retrieval
  value under a budget; applied to Agora's promotion funnel and its nightly index rebuild.

## Learning & phase dynamics
- **Antifragile learning is an active surprise-seeking loop** (*active; challenge queued*) —
  passive exposure to disorder is not enough; the system must hunt stressors.
- **Grand syntheses are forecastable phase transitions** (*active*) — knowledge systems emit
  early-warning signals (slowing falsifier closure, rising bridge rate, theme flickering) before
  reorganizing around a new principle.

## Markets & evidence
- **Alternative-data alpha is an identification premium, not an information premium** (*active*) —
  the edge is unresolved adjustment ambiguity; standardizing the METHOD burns it down. Same in the
  personal domain: a finance-watching agent's edge is its model of YOUR counterfactual normal, not
  its data access.
- **Finance is formalized risk management because wealth is MULTIPLICATIVE** (*active*) —
  compounded growth = mean − σ²/2; the variance drag is measured to be *exactly* σ²/2·T
  (Lab `cc2468`), and a strategy with a 50%-higher expected return compounds *less* once its
  volatility crosses a threshold. Managing variance is a first-order growth lever; the
  arithmetic-average summary discards the structure (multiplicativity) that governs the outcome.

## Software & AI
- **Software architecture's hard part is the absence of a global optimum** (*active*) —
  architecture is Pareto navigation under uncertainty; demanding 'the best' design is a category error.
- **Locating the reliability boundary is the real frontier with capable AI** (*active, salon*) —
  'finding what AI can't do' and 'certifying it succeeded' are ONE tail-detection problem.
- **Comparison out-identifies absolute scoring** (*active*) — contrastive/pairwise self-evaluation
  beats pointwise scoring at picking the best idea, and the gap GROWS with judge noise (Lab
  `992317`): reflection-by-contrast is an identification strategy (O(N²) relative signals,
  outlier-robust), not a cognitive trick. A noisy verifier should compare, not score.

## Method (how Agora itself should work)
- **Measure 'smarter' on four tiers, weakest-claim-first** (*active*) — internal capability,
  knowledge structure, transfer to real decisions, calibrated metacognition; any single
  intelligence score is a red flag.
- **Retention curves are a FLOOR of learning, not the ceiling** (*active*) — ungameable at the
  floor, but they measure maintenance not transfer; the honest instrument is two-layer.
- **Deep reading beats abstract-skimming** (*active*) — one fully-read paper per day changes the
  grounding quality of every downstream synthesis.
- **Compute is the third evidence channel** (*active*) — the Lab makes falsifiers runnable; a
  measured baseline beats a promissory one. Every claim now ships with one.

## Track record (accountability)
Public: github.com/DanceNitra/agora/blob/main/public/track-record.md — 11 replications reproduced
/ 0 failed / 5 not-computable; 6 of our own beliefs revised under challenge; 0 forecasts resolved
yet (4 open) — shown plainly, no overselling. Exams 7/8, 6/6, 8/8. The Lab now feeds the Flywheel.
