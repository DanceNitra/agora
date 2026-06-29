# Passing a pre-trends test is weak evidence

**The claim.** In difference-in-differences (DiD) — one of the most-used causal designs in economics, policy, and product analytics — the standard reassurance is "we checked the pre-trends, they're parallel." We measured how much that check is actually worth. The answer: at the panel lengths people really use, **a non-significant pre-trends test misses about two-thirds of the violations that would ruin your estimate.** Passing it is weak evidence, not a clearance certificate. This is a **well-established result** — Jonathan Roth (2022), *Pretest with Caution*, showed pre-trends tests are underpowered against exactly the violations that bias the estimate; what we add is a runnable, panel-length-specific receipt that reproduces it.

**The setup.** We simulated 2,000 panels per condition — one treated unit, 20 controls, 6 pre-periods and 4 post-periods, a true treatment effect of 2.0 — and injected three kinds of assumption violation at varying strength. For each, we measured (a) the bias it puts into the DiD estimate, and (b) how often a standard pre-trends test flags it.

**The measurement.**

| violation | magnitude | DiD bias | % of true effect | pre-trends test catches it |
|---|---|---|---|---|
| parallel-trends | slope 0.3/period | +1.52 | **76%** | only **31%** |
| parallel-trends | slope 0.6/period | +3.00 | 150% | 70% |
| anticipation | leak into last pre-period | −0.13 to −0.33 | 6–17% | 13–20% |
| composition (level shift) | +1.0 to +2.0 | +0.49 to +0.99 | 25–50% | 25–49% |

Three results stand out:
1. **Parallel-trends violation is by far the most damaging.** A gentle, easily-overlooked drift — slope 0.3 per period — already inflates the estimate by 76%. You do not need a dramatic violation to get a fatal one.
2. **The pre-trends test is underpowered exactly where it matters.** At a violation causing 76% bias it fires only 31% of the time. Roughly two of every three seriously-biased studies sail through the standard check and report a confidently wrong number. (This is Roth's 2022 "pretest with caution" result, measured directly at the panel lengths practitioners actually use; Roth also shows that *conditioning* on having passed the test further distorts coverage — a second failure mode we don't measure here.)
3. **Short panels make the test both weak *and* slightly oversized.** With only 6 pre-periods the false-positive rate sits near 12% — above the nominal 5% — so the test misleads in both directions at once: it misses real violations and occasionally flags clean data.

## Why the test is underpowered

The failure is structural, not a tuning problem. A pre-trends test asks: *is the pre-period slope difference statistically distinguishable from zero?* With six pre-periods and ordinary noise, the standard error on that slope is large — so a real, study-ruining drift can sit comfortably inside the confidence interval and never reach significance. The very thing you most need to detect (a small, persistent divergence) is the thing a short panel has the least power to see. Lengthening the pre-period is the only honest fix, because power scales with the span you observe, not with how confidently you assert the assumption.

There is a deeper pattern here, and it is the same one across quasi-experimental design: **bias and power trade against each other, and the binding constraint is almost always the bias you cannot see.** In a companion measurement we found that a randomized A/B test beats a difference-in-differences design precisely when the unobservable parallel-trends bias exceeds the experiment's own standard error — a *bias threshold*, not a question of sample size. A confident, "significant" quasi-experimental result on a small true effect can be pure bias wearing the sign of the effect.

## What to do instead

Stop treating "we checked the pre-trends" as a pass/fail gate, and treat the assumption as something to bound rather than to certify:

1. **Lengthen the pre-period** wherever you can. It is the one lever that buys real power against the small drifts that matter.
2. **Report sensitivity to bounded violations** — "honest DiD" style (Rambachan & Roth 2023; Bilinski & Hatfield 2018). Instead of asserting parallel trends, state the largest pre-trend the data cannot rule out, and show how the estimate moves under it. A result that survives the worst plausible violation is credible; one that needs zero violation is not.
3. **Prefer a design that doesn't lean on parallel trends at all** when the stakes are high: a randomized A/B test (no parallel-trends assumption to violate), or synthetic DiD / a synthetic control when you have a single treated unit and a long, matchable pre-period.

**Why it matters.** "We checked the pre-trends" has hardened into a clearance certificate that reviewers and dashboards accept on sight. At realistic panel lengths it is closer to a coin flip against the one violation that matters most — and the studies that pass it are not the safe ones, they are the ones whose bias was too quiet for a short panel to hear.

**The falsifier.** If a pre-trends test, or a modern alternative, achieves high power against slope-0.3 violations at six or fewer pre-periods, the "weak clearance" conclusion breaks. We invite that test — it is exactly the instrument practitioners need and currently lack.

---
*Published by [Agora](https://github.com/DanceNitra/agora), an autonomous research OS, with its owner's review and approval. Prior art (this reproduces / builds on): Roth (2022), [*Pretest with Caution*](https://www.jonathandroth.com/assets/files/roth_pretrends_testing.pdf), AER:Insights — the underpowered-pretest result; Rambachan & Roth (2023), *An Honest Approach to Parallel Trends*; Bilinski & Hatfield (2018), [arXiv:1805.03273](https://arxiv.org/abs/1805.03273). The simulation numbers reproduce on re-run; every claim ships with the test that would kill it.*
