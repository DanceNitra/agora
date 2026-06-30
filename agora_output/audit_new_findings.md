# New findings + frontier questions surfaced BY the full-panel audits (#3, #7–#10)

## Audit #3 — the-operating-point-trap (full panel, 2026-06-30)
- **Frontier Q1 (the strong one): is the operating-point gap FORECASTABLE from benign-regime data?**
  For each rebuilt claim, fit error(stress) and test whether the LOCAL slope dError/dStress at LOW stress
  predicts the high-stress gap. Two publishable outcomes: (a) it extrapolates → a cheap "stress-sensitivity
  probe" you can run WITHOUT going to the dangerous operating point (operationalizes the post's own habit #2);
  (b) it does NOT (failures are threshold/phase-transition, flat-then-cliff) → a scarier finding: the trap is
  unforecastable from benign data, so "check if the bias grows in the stress variable" is unmeasurable exactly
  where it matters. Directly stress-tests the post's prescription. Runnable now on the existing probes.
- **Frontier Q2 — "conservation of fragility" test.** For each robust escape (median, value-aware eviction),
  identify its OWN stress variable and show the trap reappears: median → construct a skew/asymmetry regime,
  measure whether its error grows there; value-aware policy → inject value-estimation noise / distribution
  shift, measure re-coupling. If every robust estimator re-traps on a different axis, upgrade the insight from
  "use robust estimators" (a false free lunch) to a quantified **"fragility is conserved; minimize
  ∫error·P(stress) over YOUR deployment's stress distribution."** A more defensible, more original claim than
  the current post. (This conservation caveat was added to the post's "honest part" in this audit.)
- **Prior-art the diversification example should have named: Longin & Solnik 2001** (extreme/crash correlation
  → diversification fails when needed) — the single most famous on-the-nose version of the post's own headline;
  now credited. Also robust-statistics breakdown point (Huber 1964 / Hampel 1971) as the formal cousin.
- **Lesson:** in a SYNTHESIS post that quotes numbers from other posts, the citation LINK and the quoted
  NUMBER must come from the SAME experiment. The memory bullet quoted the access-reset-decay lab's dramatic
  "3%/kept-all/3×" while linking to the two-tier post (which reports 0.13/0.65) — a reader who clicks to verify
  lands on different numbers. Fixed by aligning the bullet to the linked post's own figures (13% vs 65%). Also
  the panel caught the post committing its OWN thesis sin twice (quoting a 30%-budget row as "tight budget"
  where the value policy "kept all", when at the genuinely tight 7% budget it too collapses to ~2.4%; and
  quoting a single t(1.8)/ES99 figure as "real markets"). Decisive bug: a garbled FAQ answering the hot-hand
  question with diversification text ("96% risk reduction"), live in EN + SK + the JSON-LD FAQPage schema.

# New findings + frontier questions surfaced BY the full-panel audits (#7–#10)

The full /stress-claim panels don't only catch overclaims — the 6th-lens (blind-spot) and the
severe-test re-runs PRODUCE new research leads. Capturing them here so they feed the flywheel instead of
evaporating. (Owner prompt 2026-06-29: "weren't you also doing audits ON new findings?" — yes; logging.)

## Measured side-results (real, runnable — candidate Crucible/posts)
- **Percolation cliff for note-vaults (#10, lab `percolation_vault_cliff.py`).** Swept link-removal on an
  ER graph at vault density (mean degree 13): giant-component holds ~1.0 until ~80% of links removed, then
  drops abruptly (1.000→0.892→0.771→0.411→0.066) at the Erdős–Rényi/Molloy–Reed threshold (q_c≈0.92,
  remaining mean-degree→1). NEW honest result: the "knowledge-debt cliff" is real & sharp, BUT a well-linked
  vault (13 links/note) is far above it — so the actionable signal is the *trend* of giant-component
  fraction toward the threshold, not the absolute score. (Substantiated the claim AND corrected the
  overclaim that 0.81 is near collapse.)

## Frontier questions (one per audit, from the blind-spot lens) — candidate hypotheses/Board open-Qs
- **#7 (coverage):** Can a posterior be built that is *simultaneously* sharp+calibrated for prediction yet
  *auto-widens to nominal coverage on non-identified causal directions* — estimand-aware calibration without
  a hand-specified sensitivity prior? (Test: vary misspecification; measure predictive calibration vs causal
  coverage separately.)
- **#8 (exit/quitkit):** What is the optimal *Bayesian sequential* stop that jointly infers
  depletion-vs-noise-vs-dormancy AND prices the option to return — and how far is the cheap drawdown
  heuristic from it as SNR, replenishment rate, and switch cost vary? (Our θ=0.6 is one no-noise, no-return,
  mid-switch-cost point.)
- **#9 (self-training):** Curation as effective real-data fraction — can a *verifier/selection* filter of
  given precision substitute for the ~5% real-data anchor, and where does the collapse knee move when
  synthetic data is *filtered* rather than raw? (Why AlphaZero improves under self-generation; Alemohammad
  2024, Feng et al. Ties to the [[adaptation-corruption-separation-law-breaktruth]] selector idea.)
- **#10 (second-brain):** Does giant-component fraction (or *any* connectivity statistic) actually predict
  retrieval recall@k? Build a retrieval ground-truth (real query → wanted note) and measure it; estimate the
  *optimal* link density (interior optimum — over-linking → link spam, GC saturates at 1.0 but recall drops)
  rather than maximizing connectivity. (Connectivity is currently an *unvalidated proxy* for the real
  objective; Goodhart risk in the "link the orphans" tool.)

## Pattern across audits (meta-finding)
Our published posts repeatedly ship a TRUE-but-textbook mechanism wrapped in a slightly-overclaimed headline
+ a single synthetic-model number stated too universally + missing the prior-art family. The full panel
reliably finds: (1) the established prior art, (2) a strawman/weak baseline, (3) a synthetic number quoted as
a constant, (4) one genuinely useful runnable artifact underneath. The honest reframe keeps (4), credits (1),
discloses (2)+(3). This is the [[audit-publish-full-procedure-never-shorten]] payoff.

## Next: feed the strongest to the flywheel
The #9-curation and #10-retrieval questions are the most testable + on-frontier. Candidate to POST to the
brain Board / hypothesis loop as open questions the agents re-test, or to run as the next Crucible probes.

## #1 (causal-inference-phase-diagram) — full /audit-post, verdict heavy REFRAME (estimand error)
Core error caught (all 5 lenses + code read): τ=2.0 is the DIRECT effect; difference-in-means consistently
estimates the TOTAL effect via M=(I−ρW)⁻¹, so the "96% bias" was a total-vs-direct ESTIMAND MISMATCH, not
RCT bias; the 1/(1−ρ) divergence is the Manski linear-in-means reduced form (multiplier label = Glaeser-
Sacerdote-Scheinkman 2003), baked in; "phase diagram" was a 1-D curve; "design matters less" was untested
and likely INVERTED. Rewritten honestly (estimand shift; design/estimand matters MORE), re-audited CLEAN.
**Frontier question:** on a scale-free network as ρ→ρ_crit, does a cluster-randomized estimator of the
TOTAL effect stay unbiased with finite variance, or does critical slowing-down make it unidentifiable? That
single test separates "design fixes it" from "near criticality nothing is estimable."

## #2 (pre-trends-test-weak-evidence) — full /audit-post, verdict REFRAME (real stats bug)
Method auditor + our own verify script caught a measurement bug the light pass missed: the pre-trends test
used a NORMAL (z=1.96) critical value on a t-statistic with only 4 pre-period df. Correct Student-t cutoff:
detection at slope 0.3 = 16% (not 31%), at 0.6 = 45% (not 70%); false-positive rate = nominal 5% (not 12%).
=> the published "short panels make the test oversized / ~12% false positives / misleads both directions"
claim was an ARTIFACT and is removed; the honest story is one-directional (pure low power), and stronger
("misses ~5 of 6", not 2/3). Fixed EN+SK+table+tldr+meta/og/twitter/JSON-LD; foregrounded the fix
(Rambachan-Roth HonestDiD + Roth's pretrends power package). Re-audit: 2 skeptics caught a leftover
"one-third" in the desc/tldr/meta -> fixed -> clean. Numbers = our sim reproducing Roth 2022, not his.
**Frontier question:** in a single-treated-unit design, what min pre-period length / effect size makes
honest-DiD sensitivity bounds informative rather than vacuous? **Lesson:** always use the correct t (not z)
cutoff on small-df test statistics — a z-on-4df error manufactured a whole false sub-claim.
