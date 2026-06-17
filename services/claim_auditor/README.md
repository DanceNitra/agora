# Claim Auditor

**"Is this number real — or what would a matched null / proper identification produce?"**

A claim-diligence engine. Give it a reported quantitative claim and it scores it on the two ways a
reported effect is usually wrong, then returns a one-page verdict.

## Why this exists (the wedge)
- Marketing attribution **overcounts ad impact 20–40%**; 75% of marketers say measurement
  underperforms and the field is pivoting from attribution (credit) to incrementality (causation).
- The biggest unmet enterprise-AI need is **proving an intervention *caused* a measurable outcome**
  (60% of AI projects are abandoned for poor data/measurement).
- Agora's own measured result — *alt-data alpha is an identification premium, not an information
  premium* (Lab `11c99e`) — and the Business×Health bridge say the same thing: **the durable edge is
  causal identification, not data volume.** This tool productizes that edge as a service artifact.

It is a **service** (claim diligence for CFO / PE / performance-marketing / clinical-evidence buyers),
not a SaaS product.

## The two checks
1. **Matched null** — is the effect bigger than a properly randomised (placebo/permutation) baseline,
   or is it within what selection/chance alone would produce? *(credit only effect minus its own null)*
2. **Identification quality** — does the effect SURVIVE across the defensible analytic choices
   (controls, window, model), or does it swing with the specification? A specification-curve that
   collapses or flips sign = attribution dressed as causation. The tool also computes the
   identified (adjusted) effect and reports how much the headline claim **overstates** it.

Verdict ladder: `OVERSTATED/NOISE` (not above null) → `OVERSTATED by X%` (real effect, inflated claim)
→ `NOT IDENTIFIED` (spec-dependent) → `REAL (identified)`.

## Validated demo (`python claim_auditor.py`)
A marketing-attribution case with a **known** ground truth (ads are targeted at high-propensity
users — a selection confound), so the engine can be checked against truth:

```
CLAIM: 'ad exposure lifts conversion' (last-touch)   claimed +0.107 abs conversion rate
  matched null:        p = 0.000  -> ABOVE null (a real effect exists)
  identification:      effect spans [+0.045 .. +0.107] across 6 specs
  identified effect:   +0.045   (ground truth +0.040 — recovered)
  >>> the claim OVERSTATES the identified effect by +137%
VERDICT: OVERSTATED — a real effect exists (~+0.045) but the claim inflates it by +137%
```

The auditor recovers the true causal lift (+0.045 vs ground-truth +0.040) and flags that the
last-touch headline (+0.107) more than doubles it — the exact failure real teams report.

## Status / next
- v1 engine (matched-null + identification-quality + one-pager) — done, validated on a ground-truth case.
- Next: run on a **real public claim** with real data, then take the one-pager to a first customer
  (the unskipped distribution test). Adapters for incrementality holdouts and study-effect inputs.
