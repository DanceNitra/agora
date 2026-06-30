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

## #11 (why-crowds-get-dumber / cascade) — 6th-lens (blind-spot) pass only
Backing lab = `herdcheck/herdcheck.py` (reproduces Lab 678a9c + red-team 14becd). Code facts the other
lenses skip: agents observe RANDOM earlier agents (not literal "neighbours"); each acts ONCE,
irreversibly, in a strict total order; headline metric = P(majority of all 401/1001 actions correct).
- **Sharpest blind spot — "worth ~3 minds" is the WRONG MOMENT.** A real 3-independent-mind crowd and the
  cascaded 1001-crowd match on EXPECTED accuracy (~0.64 at p=0.6) but not on observable uncertainty: 3 minds
  split their vote ~35% of the time (the disagreement itself warns you); the cascade is near-UNANIMOUS and
  wrong ~36% of the time with no internal signal. So "dumber / worth 3 minds" UNDERSELLS it — it is worse
  than 3 minds because the error is both correlated AND silent. The right frame is calibration (confidently,
  unanimously wrong), not a level ("dumber"). The post even prescribes "distrust unanimity" but never
  measures whether unanimity is a usable wrong-detector in this regime.
- **Internal inconsistency the citations/overclaim lens miss — the post lumps markets with committees, but
  its OWN unbounded-belief result puts them in different regimes.** Smith–Sørensen (the post's own caveat):
  unbounded private belief / continuous signal → complete learning → no collapse. A price-revealing
  prediction market shows a continuous near-sufficient statistic (≈shared evidence, unbounded), so the model
  PREDICTS markets are in the SAFE class — contradicting the post's example list ("committee, market, or AI
  agent-swarm" all cascade-prone). Action-only + bounded → collapse; price/evidence/continuous + unbounded
  → safe. The "which real systems?" question has a sharp, runnable answer the post hand-waves past.
- **Two different cures conflated; the post prices the expensive one as "the" cure while the shipped tool
  ships the cheap one.** Post §3 "need >80% independence" is the COMPOSITION cure (who is in the room —
  contrarian quota mixed into a sequential herd). But `herdcheck` measures an INFORMATIONAL cure that is
  cheap and total: `discount=0.5` or `own_weight=3` → 100% at peers_seen=2. "Surprisingly expensive cure"
  is true only for the composition intervention; the headline is in tension with our own released tool.

### Frontier questions (runnable now on herdcheck.py — zero-dep, deterministic)
- **FQ-A (the strong one — is single-file load-bearing?):** Replace the strict total order with (a)
  simultaneous one-shot, (b) R synchronous rounds where agents observe the PREVIOUS round and may revise
  (DeGroot-with-discrete-actions), (c) random small batches with partial observation. Measure collective
  accuracy AND unanimity rate vs batch size / #rounds. Hypothesis: collapse magnitude scales with the depth
  of the observation DAG — vanishes in pure simultaneous batches, and iterated revision either HEALS
  (private signal re-injected each round → recovers) or LOCKS HARDER (wrong consensus fixed point).
  Publishable either way; directly settles the post's own "order-of-arrival" next-test and tests whether
  the headline is an artifact of irreversible single-file action.
- **FQ-B (decision-relevance / calibration):** Add outputs P(wrong), P(unanimous), and crucially
  P(wrong | unanimous) vs P(wrong | split); compare to a true 3-independent-mind crowd at matched mean
  accuracy. Tests whether the post's prescribed signal ("distrust unanimity") is actually usable here, or
  self-refuting (if the cascade is ALWAYS unanimous, unanimity carries no information exactly where the post
  tells you to use it). Reframes "dumber" → "confidently, silently wrong."
- **FQ-C (regime taxonomy / which real systems):** Add a continuous-signal variant (noisy real-valued
  statistic, unbounded LLR), confirm Smith–Sørensen complete learning, then output a 2×2 (bounded vs
  unbounded × action vs evidence) of measured collective accuracy: committee-vote = bounded+action =
  collapse; price-market = unbounded+continuous = safe; CoT-sharing ensemble = evidence = safe;
  answer-voting LLM ensemble = action+bounded = collapse. One figure that tells a practitioner which real
  system is in the danger quadrant — and corrects the post lumping markets with committees.

### Stated as settled, actually open
1. "**two visible neighbours** trigger it" — the code observes RANDOM predecessors, not neighbours, and "2"
   is specific to own_weight=1, p=0.6; the neighbour-vs-random-predecessor conflation and the topology
   generality ("no dense network needed") are asserted, not shown across p / structure.
2. "**rescuing it costs >80% independence**" — true only for the composition cure; our own herdcheck shows
   the informational cure (discount redundant peers) is cheap and total. Two interventions, one headline.
3. "**collapse needs bounded beliefs**" — a Smith–Sørensen theorem, settled in theory; but whether REAL
   agents (LLMs in a swarm) have bounded or unbounded effective private belief is the unmeasured empirical
   premise that decides whether ANY of this applies to AI ensembles. Asserted relevance, untested premise.

### Cross-post synthesis lead (correlation as the stress variable)
Cascade (this post), diversity-is-noise-for-answers, and the operating-point trap are three mechanisms that
all drive the OFF-DIAGONAL of the error covariance toward 1: the cascade manufactures correlation
endogenously; diversity-flip shows LLM errors are systematically (not independently) correlated; the
operating-point trap shows dependence spikes exactly at stress. Unifying claim candidate: "independence
assumed, correlation delivered, and correlation is maximal exactly where it costs most." Candidate Board
open-Q / synthesis post.

**AUDIT OUTCOME (2026-06-30, full panel → REFRAME applied):** the boundedness scope (Smith & Sørensen 2000)
was added to §1 + footer + FAQ (EN+SK+JSON-LD); "two neighbours" demoted to the w=1 case with the general
law k_c=w+1 foregrounded; the broken EN "what to do" list (3 split <ul>) repaired to one clean <ul> matching
SK; "~3 minds" given its weak-clue regime label; "almost nothing at 50%" → measured 0.63→0.69; the
expensive-cure headline reconciled (contrarian-quota is the expensive one that barely works; structural cure
is cheap). All 5 sims reproduce; 6/6 citations TRUE. FQ-A/B/C remain the live flywheel leads.

## ⚠️ SYSTEMIC BUG (found during #6/#7): truncated meta descriptions across 16 published posts
A scan of `public/posts/posts.json` found **24 truncated `desc`/`desc_sk` fields across 16 posts** — the
description was cut off mid-word/mid-sentence (e.g. "…Under the kind of misspec", "…found none: each
degrades smoothly. But", "…the 16 fla"). This desc feeds the meta description + og + twitter + JSON-LD
Article description + the visible TLDR + the homepage card excerpt — so Google/social/LLM all show a
truncated snippet for these 16 posts. Affected slugs (from the scan): why-a-captured-company, we-built-a-
meter, we-built-a-firewall, robustness-checks-arent-ritual, why-a-more-capable-ai, we-looked-for-the-
grounding-tipping-point, we-hunted-for-the-tipping-point, the-most-confident-systems, a-pre-trend-too-
gentle, the-calibrated-prior-for-we-reversed-aging, i-scored-the-16-most-hyped-anti-aging, the-hot-hand-
fallacy, your-rag-store-is-rotting, your-second-brain-is-dying, your-ai-might-be-training, everyone-says-
set-exit-criteria. **Each is fixed as part of its own audit** (the audit queue covers most of these). The
root render cause (descriptions truncated at ~200 chars at generation time) should also be fixed in the
renderer so future posts don't regress — a separate small build task. #3/#4 (operating-point, why-crowds)
did NOT have this (their TLDR/desc were hand-written complete); it hits the posts whose desc was
auto-derived from the body's first chars.

## #7 (more-data-more-wrong) — FULL PANEL (after owner flagged the #7-#10 re-audits were shortened)
The 2-skeptic re-audit had only fixed truncation + SK quality. The owner correctly insisted on the FULL
5-lens + verify-claims panel. It caught a REAL content over-generalization the skeptics missed: the post
asserted "the estimator is consistent for the BLP coef (≈1.6), SO the interval is correctly calibrated for
that pseudo-true value" — the "so" is a non-sequitur in general and CONTRADICTS the post's own cited Müller
2013 (under generic misspecification even the pseudo-true value needs a sandwich correction). The method agent
MEASURED it: coverage of 1.6 = 95.2/94.2/95.5/95.5% at n=50/200/1k/20k — TRUE here, but only by a Gaussian/
homoskedastic accident (marginal residual conditionally homoskedastic → marginal model correctly specified →
model variance = sandwich). Fixed: substantiated (measured ~95% of 1.6) + scoped to the Gaussian structure +
noted generic misspecification needs the sandwich (Müller); added White (1982) as the QMLE/pseudo-true/sandwich
foundation; tightened the FAQ slogan "more data, more wrong" → "more confidently wrong" (snippet-safety).
**Lesson: the 2-skeptic-only re-audit is NOT equivalent to the full panel — the panel's prior-art/method
lenses catch technical over-claims a confirmation skeptic doesn't. Run the full panel.**
- **Frontier Q (the strong one, from the blind-spot lens): is confounder-induced overconfidence DETECTABLE
  in-sample?** On the same y=x+z+noise (ρ=0.6, omit z) setup, at each n run (a) a posterior-predictive check,
  (b) a misspecification/spec test (RESET, residual normality, heteroskedasticity), (c) held-out predictive
  log-likelihood vs the correct model (without access to z). Conjecture: because z is absorbed into the error
  and only shifts x's coefficient, the omitted-confounder model is observationally indistinguishable in-sample
  (PPCs pass, spec tests fire at ≈ nominal α, flat in n) → the overconfidence is UNDETECTABLE from the data you
  have. If it holds, THAT is the non-tautological, publishable result ("the failure is silent — no in-sample
  diagnostic flags it, which is exactly why more data is dangerous"). If some diagnostic's power grows with n →
  the actionable rule "run test X". Either way a sharper post than the coverage-collapse receipt.

## #6 (a-95-confidence-interval-covers-31 / DiD 1-treated-unit) — full panel, verdict REFRAME
Numbers reproduce within MC noise (DiD coverage 0.305→re-run 0.301; SC 0.891→0.898; widths/RMSE all match;
kept 800 reps — swapping to 2000 would force "31%"→"30%" + a title/slug change for a 1pp wobble). Real
defects the prior "nums re-run" pass missed: (1) EN TLDR + meta/og/twitter/JSON-LD + homepage card +
posts.json `desc` were all TRUNCATED mid-sentence at "…In a clean"; (2) SK body+h1+TLDR+footer were
diacritic-stripped and used the non-word "ostatkovaná jednotka" (vs the correct "ošetrená" in the SK FAQ);
(3) **estimator-vs-inference conflation** — the table compares DiD-with-analytic-SE vs SC-with-placebo-
inference, changing BOTH at once, so "SC fixes coverage" is under-identified; SC's coverage comes mainly from
its placebo/permutation inference (Abadie-Diamond-Hainmueller 2010, was UNCITED), and valid inference
(Conley-Taber/permutation/wild-cluster bootstrap) on the DiD estimate also restores coverage — the real fix is
the inference, not abandoning DiD; (4) AF2020 MISCREDIT — Alvarez-Ferman 2020 is about *spatial* correlation
(across units) and is an arXiv working paper, but the post replicates AR(1) *serial* correlation over time =
the BDM-2004 / Conley-Taber design; recredited; (5) "mean abs(bias)" mislabel (estimator is unbiased under
true=0) → "mean abs error".
- **Frontier Q (the strong one): disentangle estimator-failure from inference-failure + map the coverage
  surface.** On the same AF-style panels run the 2×2 {estimator: DiD, SC} × {inference: analytic-SE,
  permutation/placebo} + a 3rd arm Conley-Taber-on-DiD, reporting coverage AND power AND width at true effects
  τ∈{0,0.5,1,2}. Prediction: DiD+permutation restores coverage ~0.95 AT the DiD estimator (proves "switch to
  SC" is a false dichotomy); SC's 4× width costs real power. Then map coverage-vs-(ρ, n_treated, T_pre): sweep
  ρ∈{0,.2,.4,.6,.7,.9}, n_treated∈{1,2,5,10}, T_pre∈{4,8,20} → the boundary where naive DiD inference becomes
  trustworthy (coverage≥0.93). A phase-diagram that ties into the "causal inference has a phase diagram" post.
- Missing prior art added: Abadie-Diamond-Hainmueller 2010 (JASA, the SC method + placebo inference) +
  Ferman-Pinto 2019 (REStat, few treated groups). Real-data ρ≈0.8, so the post's ρ=0.7 is conservative.

## #5 (passing-a-pre-trends-test / twin of #2) — full panel, verdict REFRAME (SAME z-vs-t bug, unfixed)
The render_piece twin of #2 still carried the EXACT z-vs-t bug #2's full audit fixed (det 31%→16%, 70%→45%,
removed the spurious 12% "oversized/misleads-both-directions" FP — real size nominal 5%; "2/3"→"5/6";
"one-third"→"one in six"). Prior pass a641c69 added only Roth-2022 credit. Lesson: **when a post is the
twin of an already-fixed one, the fix does NOT propagate — re-audit the twin to the same standard.** Also
caught: Rambachan&Roth title was the working-paper "An Honest Approach" → published "A More Credible Approach
to Parallel Trends" (ReStud 2023); added Roth's `pretrends` package (already computes the headline) + "What's
Trending in DiD" survey; reframed the "which assumption fails worst" ranking (parametrization artifact — a
per-period slope compounds over post-periods, a one-time composition/anticipation shift does not) →
"a slow compounding pre-trend is most biasing AND hardest to see".
- **Structural finding for the owner:** #5 is a near-duplicate of #2 (same title; canonical already → #2; #2
  is richer + already corrected). Numbers now synced, but the panel recommends COLLAPSING #5 into #2 (redirect
  + de-list from sitemap/index) rather than maintaining two same-title posts. Flagged for owner (outward/SEO).
- **Frontier Q (blind-spot, the strong ones):** (F1) sweep J treated-units × T_pre pre-periods at slope 0.3,
  find the power≥0.80 contour → "you need ≥X treated units and ≥Y pre-periods before a passed pre-trends test
  carries real information" (bounds the scope instead of overgeneralizing from J=1). (F2) gating vs honest-DiD
  head-to-head on the SAME panels — measure effective coverage of the true effect + interval width (validates
  the post's own prescription, currently asserted-not-measured). (F3) conditional-on-passing bias: measure
  E[bias | pre-test PASSED] — pre-testing is a selection procedure that can leave survivors MORE biased; this
  is the mechanism Roth actually warns about and is absent from the post. All runnable on the existing DGP.
- **Scope caveat added:** the n=1-treated-unit / few-pre-period design is the worst corner AND a known-
  degenerate inference case (Conley–Taber 2011); serious single-treated-unit practice uses placebo/permutation
  or Conley–Taber, not a 4-df t-test. Result scoped accordingly.

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

## exit-criteria / quitkit (drawdown-stop, theta~0.6) — overclaim+blind-spot pass, verdict PUBLISH (minor fix)
Numbers reproduce EXACTLY off the numpy lab (757 baseline; 2010/2113/2569/2366/2053 sweep; +239.4%). Post is
already heavily hedged (interior-optimum honest, +239% explicitly called the worst-baseline gain, prior art
fully credited: Charnov MVT + Krebs/McNair/Green/Brown giving-up family, "nothing here is new theory").
- **Consistency fix (minor):** the SHIPPED public tool `quitkit/quitkit.py` (linked as "the proof") uses
  Python's `random.Random(3)` not numpy's PCG64, so it prints baseline=811, best=2535, **+212.6%** — NOT the
  headline +239%. A reader who runs the linked artifact gets a different number. Either align the tool's RNG
  to the numpy lab, or report the lift as a range ("~+210-240% depending on RNG"). The foot's "figures
  reproduce on re-run" is true for the lab but not for the public tool.
- **Seed robustness (measured, NEW):** over 40 numpy seeds, lift vs deplete = mean 223% / median 216% /
  range 162-311%; argmax theta = 0.6 in **37/40** seeds. => the qualitative claims (interior optimum at
  ~0.6, large positive lift) are ROBUST; the exact +239% is a slightly-high single seed (seed 3 > median).
  This strengthens the "theta~0.6 illustrative" framing rather than weakening it.
- **Blind-spot (the strong one) — the noise/SNR regime is the headline's blind corner:** the post mentions
  in WORDS that a drawdown stop "can quit a good vein on a temporary dip," but never measures it. Measured
  (lognormal multiplicative noise sigma on per-dig success prob, 20 seeds): lift collapses
  +231% (sigma=0) -> +198% (0.5) -> +119% (1.0) -> **+62% (1.5)**. The cheap proxy still WINS in this
  no-replenish model but gives back ~3/4 of its edge as SNR drops. The +239% headline lives at the
  zero-transient-noise corner; real efforts (ad campaigns, research lines) are noisy.
- **Blind-spot #2 — no-replenish / no-return over-generalization:** the model has finite veins, no
  replenishment, no switch cost, and quits PERMANENTLY. The post discloses this, but the headline domains
  it invokes (a field reopens, a method matures, a sales channel recovers) are exactly the replenishing /
  returnable case the model cannot speak to. The interior optimum here is driven purely by finite veins
  (post says this) — add a per-switch cost or replenishment and the optimal theta moves.
- **Frontier Q (runnable, the real science):** sweep drawdown-theta vs MVT-exact (marginal rate = habitat
  average) vs Gittins-index vs never-quit across a 3-axis grid: observation-noise sigma x replenishment-rate
  rho x per-switch-cost c. Map the region where the cheap model-free drawdown proxy is within X% of the
  MVT/Gittins optimum ("when is the free proxy good enough?") vs where it is actively dangerous (high noise,
  high replenishment -> quitting a recovering vein). The noise run above (edge +231%->+62%) is axis 1 of
  this grid and already shows the proxy's edge is SNR-graded; replenishment + switch-cost are the untested
  axes. This is a genuine Crucible-grade probe, not a textbook re-derivation.

---

## AUDIT — "Your AI might be training on itself..." (selfref / collapse+lock), 2026-06-30
OVERCLAIM/FRAMING + BLIND-SPOT (6th lens). Both halves reproduce locally (selfref.py):
f=0 -> 92% collapse, knee at f=0.05 -> 6%, f=0.20 -> 1%; lock p=1.5=0.177, p=2=0.500, p=3=0.809.

- **Overclaim (the one real fix) — FAQ answers drop the toy-scoping the body keeps.** Body says
  "In our minimal simulation ... ~92-94% of runs collapsed". FAQ (EN+SK+JSON-LD) says flatly
  "Yes, cheaply. A ~5% real ... anchor pulls the collapse rate from ~94% to under ~10%, and 20%
  makes it clean." — stated as a universal fact, no "in our toy". This is the only place stronger
  than the hedged body. Fix: prepend "In our minimal model," to the collapse-number FAQ answer in
  all three surfaces. Low effort, removes the lone overclaim.
- **Blind-spot — std-collapse is a PARTIAL proxy for model collapse.** The toy fits mean+std of a
  Gaussian and calls collapse = final std < 0.5*true_std. That captures Shumailov's *late-stage*
  variance collapse but a Gaussian has no tails/modes to lose, so it cannot exhibit the *early-stage*
  tail/rare-event/mode disappearance that is the actual production worry. The post says "diversity
  drains away" which reads as faithful, but "diversity = std" silently narrows it. Worth a one-clause
  disclosure (std = variance proxy, not tail-loss).
- **Frontier Q (runnable, the real science) — does verifier-FILTERED self-training reverse collapse,
  and at what filter precision does selection substitute for the real-data anchor?** The post already
  concedes (caveat 1) that selecting synthetic outputs (best-of-N / reward-model / AlphaZero regime)
  injects outside signal and is NOT modeled by the single external_fraction knob. Make it measurable:
  add a `filter_precision q` to collapse_risk (keep a synthetic sample only if it passes a verifier
  that is correct with prob q), then sweep a 2-axis grid q x external_fraction x {dimensionality d,
  tail-heaviness via Student-t nu}. Map the trade curve: how much filter precision q buys one point of
  real-data anchor f (the "selection-substitutes-for-data" exchange rate), and whether the ~5% knee
  moves with d / nu. Two sub-questions fall out: (a) is the 5% anchor robust or a 1-D Gaussian artifact
  (test t-distributed generators, d>1)? (b) below what q does filtering AMPLIFY collapse (a bad
  verifier selects on noise)? This is Crucible-grade: it tests the one claim the post hand-waves.

---

## Audit #11 — your-rag-store-is-rotting (ragfresh) — 2026-06-30 — HEAVY REFRAME (the most serious find of the run)

**The defect the FULL panel caught (a 2-skeptic re-audit would have missed it):** the post's headline
benchmark was RIGGED. The original A/B handed the value+freshness strategy the ORACLE true value while
the recency baseline got only `updated_ts`, AND the synthetic made content-age INDEPENDENT of value, so
"recency" was structurally ~random. That manufactured the hero number (+83% "value × freshness beats
recency"). Two framing errors compounded it: (a) "freshness beats retrieval" is a CATEGORY ERROR — no
retrieval/recall/embedding arm exists in the benchmark, it only compares keep/eviction policies; (b)
"access-frequency is the wrong signal" was asserted as fact and is FALSE in the model.

**The honest rebuild (6 arms x 2 age-regimes x 20 seeds, % of keep-best-by-true-value oracle):**
- realistic (age~value): value-only 100, value+freshness 95, hits-only 92, hits-proxy 91, recency 62, random 56
- worst (age independent of value): value-only 100, value+freshness 96, hits 91, hits-proxy 90, recency 56=random 56
Lessons the data forced into the post: (1) VALUE is the lever, not freshness — value-only (100) >=
value+freshness (95), so the freshness term is a small TAX on the keep-ranking, not a benefit; its real
job is the query-time staleness multiplier + orphan/stale lifecycle. (2) a decayed HIT-COUNT proxy is a
STRONG signal (~91%, the realistic observable arm with no labels), refuting "popular != valuable" — this
is just LFU-with-aging / LFUDA. (3) recency-only ~= random when age does not track value.

**Prior art the post had ZERO of (its biggest exposure):** the whole method IS cost-aware caching —
GreedyDual-Size (Cao & Irani 1997), GDSF (Cherkasova 1998), GreedyDual (Young 2002), LFU-DA (Arlitt et
al. 2000); freshness layer = temporal-RAG / FreshQA (Vu et al. 2023). Repositioned ragfresh as a
*packaged application*, not a discovery.

**Re-audit caught 3 more (all fixed):** (1) "1.5-1.8x MORE" -> "as much" (x-more = +180%, ~2x inflation);
(2) crossover 0.09 in post vs 0.07 in tool docstring — the REAL lab gives F* = edge/Δevents =
130.2/(1900-76) = 0.071, so 0.07 is canonical and the post's 0.09 was wrong (verified by re-running
20260615-070150_autophagy...); (3) TLDR/meta "~90%" undersold the value-aware arm (95-100%).

**Frontier question (runnable, Crucible-grade):** what is the value-vs-frequency CORRELATION threshold
above which a label-free hit-count proxy beats a value-aware policy that uses NOISY labels? Sweep
(label-noise sigma) x (popularity-value correlation rho) x (keep-budget): there is a crossover surface
where, below some label quality, you are better off NOT scoring value and just aging hit-counts. That
surface is the actual deployment decision ragfresh users face and nobody has mapped it.

**Meta-lesson (reinforces [[audit-publish-full-procedure-never-shorten]]):** the rigging was invisible to
re-running the OLD benchmark (it ran fine and printed +83%) — only REBUILDING the benchmark with the
obvious missing arms (give every strategy the same information; make age sometimes track value) exposed
it. An audit that only re-runs the author's own harness cannot catch a rigged harness. Rebuild the
measurement from the estimand, don't re-execute the artifact.

---

## Audit #12 — dunning-kruger-is-a-statistical-artifact — 2026-06-30 — REFRAME (prior-art + framing)

**Verdict: methodologically sound, citations clean (verify-claims 8/8: 0 FALSE, K&D 1999 / Gignac-Zajenkowski 2020 / Hiller 2023 all real+accurate; "+46" = DK Study-1 humor gap, conservative end), but a REFRAME on prior-art + two framing defects.**

**Defects the full panel caught:**
1. (HIGH) Table TOP cell "~77" was a row-splice (the reliability-0.85 run) while the other three cells are reliability-0.60 — at 0.60 the top self-estimate is 73.3 (gap -14.2). Fixed -> ~73.
2. (HIGH) Framing "every person has the SAME self-assessment error / no skill-dependent self-insight anywhere" is FALSE for a SHRINK=0.35 model: corr(self,skill)=0.59, mean-error skill-slope -0.66; what is actually flat is the self-knowledge NOISE (sd~14 in every decile). Reworded to "no skill-SPECIFIC deficit; self still partly tracks skill via regression; only the competence-specific blindness term is zero."
3. (MED-HIGH) "Two well-understood statistical effects, NOT psychology" — better-than-average IS a psychological bias (and per the lab it is the OFFSET, not regression, that creates the famous asymmetry). Reframed to "neither a skill-dependent deficit."
4. (REFRAME) Prior-art gap: the post credited Gignac-Zajenkowski 2020 as the artifact position's source, but Krueger & Mueller (2002, JPSP) ORIGINATED the regression+BTA account (DK replied same issue), and Nuhfer et al. (2016/2017, Numeracy) already published a RANDOM-NUMBER SIMULATION of this exact chart -- i.e. the "runnable null model" the post claimed as its contribution. Nuhfer is even cited in our own lab header (line 9) but was dropped from the post. Novelty demoted to "clean prediction-not-fit re-implementation"; added the autocorrelation account (Jarry 2020 / Fix 2022) as a distinct artifact family.

**Robustness (method/confound re-ran):** +45.8 is near-deterministic (20 seeds sd 0.047); OFFSET sweep (grand-mean 60->72th) keeps bottom large-+ / top negative; reliability sweep 0.45-0.85 keeps the monotone shape; binning correct; clip(1,99) immaterial (<0.4pp). The reliability-dependence (artifact grows as reliability falls, +47.8@0.45 -> +42.5@0.85) was the post's OWN most-original sliver, computed in the lab but omitted -- now surfaced.

**Frontier question (Crucible-grade, ON our frontier -- the genuinely novel science the debunk steps over):**
Does the SAME conditioning/regression artifact contaminate how WE measure LLM overconfidence & calibration?
When we bin model responses by correctness and plot stated confidence per bin (the standard reliability-
diagram / ECE workflow), are we partly MANUFACTURING the "models are overconfident on what they get wrong"
pattern the same way the DK quartile plot manufactures human overconfidence? Runnable probe: take a calibrated-
by-construction synthetic model (confidence = P(correct) + noise, NO miscalibration), bin by correctness,
and see whether the canonical "overconfident-when-wrong / underconfident-when-right" reliability curve appears
from regression-to-the-mean alone. If it does, a chunk of published LLM-overconfidence evidence (incl. our own
Overconfidence-Tax framing) needs the same null. Ties directly to [[flagship-publish-credibility-audit]] and
the Grounding-Meter / Overconfidence-Tax line. This is the "could it stand as serious science" version.

**Meta-lesson:** the lab's OWN header cited Nuhfer 2016 -- the prior art that guts the novelty claim was in our
source file and dropped from the public post. Audit check: diff the lab/source-file citations against the post's
citations; anything the author knew but omitted is a red flag.

---

## Audit #13 — the-hot-hand-fallacy-was-the-fallacy — 2026-06-30 — REFRAME (attribution + framing + truncation)

**Verdict: science is SOLID (lab verified 1:1: D=-0.0794 t=-27.7 @k3/p.5/n100; -0.033 k2; -0.170 k4; -0.082 @p.46; consistent with Miller-Sanjurjo 2018 -- difference estimator doubles the ~-4pp single-conditional to ~-8pp at p=0.5; GVT really used 100 shots/shooter). Citations all TRUE (GVT 1985 Cognitive Psychology 17:295-314; MS 2018 Econometrica 86:2019-2047). But REFRAME on attribution + framing + a P0 truncation.**

**Defects the full panel caught:**
1. (P0) EN truncation on 5 surfaces (meta/og/twitter/JSON-LD Article desc/EN TLDR): all read only "The claim. In 1985... does not raise the probability of the next make" -- truncated mid-thought, no result, no period -- while SK TLDR is complete. Replaced with a result-first EN takeaway.
2. (P1 CRITICAL) The post took credit for Miller-Sanjurjo's REVERSAL. "the hot-hand fallacy was the fallacy / the famous debunking debunked nothing" IS MS's published Econometrica conclusion, but the post credited MS only for the "selection effect" mechanism, never the reversal -- reads as if WE overturned GVT. Added explicit "the reversal is MS's (2018); our contribution is only the runnable null" early + in body.
3. (P1) "debunked nothing" over-generalized: GVT ran multiple analyses (serial corr, runs tests, betting study); the MS bias hits the conditional-probability streak estimator specifically. And GVT's broader PERCEPTION thesis (people overestimate streakiness) is a separate claim the bias doesn't overturn. Scoped.
4. (P2, all lenses) "Re-analyses generally find a SMALL but real hot hand" is wrong AND undercuts the post's own thesis: MS's correction of GVT's OWN controlled data recovered ~+11-13pp (substantial, "moderate-to-large") -- larger than the ~8pp artifact the post dramatizes. Fixed to "substantial ~11-13pp in controlled shooting; in-game smaller and still debated."
5. (P2) "~8-point headwind" is n=100/k=3-specific; the bias shrinks with record length (-3pp at n=248, measured in the lab but hidden). Scoped.
6. (P2) The giant t-values (t=-28 etc.) are SIMULATION precision across ~6000 records, not a per-player statistic; risked a lay misread. Caveated.
7. (P2) SK FAQ (lines 121-124) was never localized: dot decimals, English quote glyphs, anglicisms (estimator/null/bias/hot hand/streak) -- fixed to SK register. Added formal GVT + MS references with links (the post had none).

**Frontier question (Crucible-grade, ON our frontier -- the genuinely novel angle, not the known basketball reversal):**
The transferable structure is "CONDITION ON A STREAK / EXTREME, then evaluate on the SAME finite sample -> manufacture a sign-flipped null/optimistic estimate." This finite-sample selection bias is PERVASIVE and UN-bias-corrected in ML evaluation, where it's treated as folklore:
  - best-checkpoint / early-stopping selection (report the val-max checkpoint -> optimistic; the next step regresses -- hot-hand-in-reverse / winner's curse);
  - best-of-K seeds / hyperparameter "our best run" (max over seeds is upward-biased);
  - post-hoc "where the model is confident" subgroup slices (condition on a high-confidence streak -> biased accuracy-after-streak);
  - streaming/agentic eval: "LLM/agent accuracy AFTER a run of K successes/agreements" (self-consistency, RL reward streaks) is the EXACT Miller-Sanjurjo estimand on a finite trajectory -- and nobody bias-corrects it.
Runnable Crucible probe: take a real eval pipeline (checkpoint selection OR self-consistency-after-K), construct a ground-truth null, measure the manufactured effect in pp -- same recipe as this post, applied where FAILED is a live novel result. Ties to [[overconfidence-tax]] / calibration line. THIS is the original contribution worth leading future work with, vs re-running a famous Econometrica reversal.

**Meta-lesson:** when a post re-implements a FAMOUS published result (MS 2018 got NYT coverage), the attribution bar is higher, not lower -- the headline must credit the original authors for the HEADLINE CLAIM, not just the mechanism, or it reads as claiming their result. Same shape as #12 (Nuhfer). Audit check: is the post's HEADLINE someone else's published conclusion? If yes, credit them in the headline vicinity.

---

## Audit #14 — i-scored-the-16-most-hyped-anti-aging — 2026-06-30 — REFRAME (framing + attribution; medically SOUND)

**Verdict: REFRAME, not KILL. Medically clean** (verify-claims 7/7, 0 FALSE: PEARL, CALERIE, ASPREE, ITP, the NMN RCT meta-analyses, and the surprising 2026 "blood NAD+ doesn't decline with age" all TRUE vs primary sources -- the NAD claim is real: Tretowicz et al., Nature Metabolism 2026, 7 cohorts, correctly scoped to BLOOD NAD+). Tally 0/1/5/2/8 = 16 reproduces against the ledger. The defects are framing/attribution/truncation/SK, not facts.

**Defects the full panel caught:**
1. (HIGH) Headline "Zero have a proven human benefit" DROPS "on a hard endpoint" -> reads as "these do nothing in humans" (false; rapamycin/CALERIE/NMN have RCT biomarker effects). Restore the qualifier.
2. (HIGH, the informative reframe) "0 of 16 proven" is ~93% driven by ABSENCE of trials: only 1 of 16 (aspirin) was ever TESTED at the hard endpoint -- and it failed; the other 15 are unproven because UNTESTED, not tested-and-failed. Lead with "1 tested/failed, 15 untested" -> converts a near-tautology into an informative 16:1 hype-to-hard-evidence ratio.
3. (HIGH, doctrine) Calibration (the test-bed point) was buried in para 5; per CLAUDE.md longevity is the test-bed and the mouse->human translation prior is the headline. Reframe calibration-first.
4. (HIGH, most valid pushback) The 0 is partly engineered by selection: exercise/GLP-1/SGLT2/statins (which DO have hard-endpoint mortality RCTs) are absent; scope = "ITP + hyped supplements." Pre-empt with one scope sentence (this list = hyped geroprotective candidates, not "everything that extends life").
5. (HIGH, prior-art) Implies it invented a genre with living trackers: Lifespan.io's REJUVENATION ROADMAP (a live trial-stage tracker), geroevidence, evidence-tier guides. "living ledger" competes with the Roadmap -> credit it; reposition to "calibration snapshot." Add the ~90% preclinical-attrition base rate + ITP low-yield as the citation for the prior (currently uncited).
6. (MEDIUM) "with sources per row" is an overclaim -- the HTML had NO table and NO per-row citations. FIX = build the actual 16-row scorecard table (also solves the SEO "no table" gap + the "scorecard" the title promises).
7. (MEDIUM, verify) Senolytics quote "no suggestion of effectiveness" is from secondary coverage (lifespan.io), not the primary n=5 pilot (which was "not powered for efficacy") -> drop quotes / reframe. ASPREE mortality: add "cancer-driven." "cannot run a decades-long trial" overstates infeasibility (ASPREE = ~4.7yr healthspan RCT that DID run) -> "rarely/expensively run."
8. (P0) Truncation on 5 EN surfaces ("...the 16 fla") + empty SK footer + SK kicker/byline "Research"->"Vyskum" + inLanguage ["en"]->["en","sk"] + SK quote glyphs. dateModified -> 2026-06-30.
9. (LOW) Cite the geroprotector survival-statistic lab (re-run: 39.9% log-rank-vs-Gehan discordance on identical datasets, FPR 5.4%->7.6% best-of-3) to back "mouse wins are fragile + human effects smaller/harder to detect."

**Frontier question (Crucible-grade, ON our frontier -- ports the longevity anecdote to AI):**
Is there a measurable, transferable "TRANSLATION SHRINKAGE COEFFICIENT"? Across a corpus of interventions that went mouse->human (effect sizes both sides), estimate the multiplicative shrinkage distribution of effect size; does a single prior generalize across domains? Then port the SAME estimator to the AI side: LLM BENCHMARK score -> real-world/production task performance shrinkage (ties to RAMR, the overconfidence/grounding line). A runnable Crucible probe: N paired (animal effect, human effect) -> shrinkage distribution; test whether a fixed prior beats domain-naive optimism, and whether the benchmark->deployment shrinkage has the same shape. This converts "0 of 16" from a longevity takedown into a falsifiable calibration law on OUR frontier.

---

## Audit #15 — the-calibrated-prior-for-we-reversed-aging-in-mice (BLIND-SPOT / 6th lens) — 2026-06-30

**The single most important blind spot (all 5 other lenses miss it): the post titled "...here's the
ARITHMETIC" never does the Bayesian arithmetic it sells, and reports "near zero / 0%" — a max-likelihood
point estimate from a tiny, massively right-CENSORED sample — as the calibrated number.** This is the post
committing the exact statistical sin its OWN companion line (log-rank-vs-Gehan fragility, "more data more
wrong", credible-interval-is-not-coverage) exists to expose: a point estimate from censored small-n with no
posterior width. For a "science of better thinking" org preaching calibration ("the number you should carry
into the next headline"), the headline number is itself un-calibrated. The "0%" is not a measured failure
rate — it is near-total censoring: of the ~8 mouse winners only ~1 (aspirin) was ever fairly TESTED at a
hard human endpoint (and rapamycin's PEARL was safety-only / underpowered), so the human-stage likelihood is
almost uninformative and 0/8 carries almost no signal. The post SAYS this once in a caveat ("not proven yet
!= failed") but the headline, TLDR and all four FAQ answers still assert "zero conversion rate" as if it
were a rate. The honest posterior is single-digit-percent dominated by the PRIOR, not a point at zero.

**Consistency drift vs #14 (real, flag for owner):** #14 grounds its prior on "~90% of drugs entering human
trials fail" = a ~10% translation base rate; #15's headline is "near zero / 0%". 10% is "low" but is NOT
"near zero" — the two sister posts hand the reader two different priors (10% vs ~0%) for the SAME update,
and neither reconciles them. The fix below closes this gap. (All other numbers are consistent: ~35
compounds, ~8 winners/23%, acarbose +22%male/~5%female, captopril +4-5%female, NAD+/NMN, 40%≈39.9%
log-rank-vs-Gehan discordance, 8%≈7.6% best-of-3 FPR.) ONE citation-lens item to verify (not my lens):
#15's claim that the captopril female signal had "the male signal confounded by an unusually short-lived
control group at one of the three sites" is a specific ITP-paper detail ABSENT from #14's table — verify
against the captopril ITP primary before it stays public.

**One coherent thesis vs two stapled (answer): they are ONE funnel with a leak at each stage, but the post
presents them as loosely-bundled "three reasons."** The survival-test fragility (reason 1) is not a parallel
reason — it attacks the FIRST funnel stage, i.e. even the 23% mouse-win rate is inflated because some "wins"
are test-choice artifacts. The strong single thesis: *multiplicative attrition that starts earlier than you
think* — mouse "win" is fragile (test choice flips ~40%) -> survives to a smaller/sex-specific effect ->
then mouse->human censors the remainder to ~0 OBSERVED. The base-rate/epistemics half is the stronger,
more original contribution (clean ITP-anchored scorecard); the survival-statistics half is the mechanism for
stage-1 leakage. Make the linkage explicit instead of listing them side by side.

### Frontier questions (candidate Crucible probes / Board open-Qs)
- **FQ-A (the strong, runnable one — REAL curves, not our synthetic sim):** our "~40% log-rank-vs-Gehan
  discordance / FPR 5->8%" is measured on SYNTHETIC age-localized effects. Run the same test-choice
  discordance on the ACTUAL published Kaplan-Meier survival curves of the ~8 ITP winners (the ITP publishes
  per-cohort survival data). Question: of the 8 mouse "wins", how many FLIP to null under Gehan-Wilcoxon /
  Tarone-Ware vs the reported log-rank? If even 1-2 of 8 flip, the headline mouse-win rate (23%) is itself
  inflated by test choice — a newsworthy, Crucible-grade result that hardens the post from a synthetic
  illustration into a re-analysis of the real record. FAILED is a live possibility (the dataset moat play).
- **FQ-B (the self-referential one — actually DO the arithmetic the title promises, and reconcile #14/#15):**
  put a Beta prior on the mouse->human conversion rate anchored on the ~90% preclinical-attrition base rate
  (prior mean ~10%, the #14 number); model the human-stage likelihood with explicit right-CENSORING (only
  ~1 of 8 winners fairly tested at a hard endpoint -> the 0/8 is mostly censored, not observed failure);
  report the POSTERIOR mean + credible interval for "this mouse headline -> proven human benefit within a
  decade." Falsifiable prediction: the posterior stays near the prior (single-digit %, wide CI driven by the
  prior because the human data barely updates it) — i.e. the honest number is "~5-12%, low but NOT near
  zero, and your uncertainty is dominated by the prior." This (a) makes the title's "here's the arithmetic"
  literally true, (b) reconciles #14's 10% with #15's "near zero", (c) is the on-brand "science of better
  thinking" version: show the prior x likelihood -> posterior update instead of asserting the conclusion.

### One concrete reframe that raises the post's rigor
Replace the asserted "near zero / 0%" headline number with the two-line Bayesian update (FQ-B): **Prior**
~10% (the cross-biomedicine 90%-attrition base rate from the sister post). **Likelihood:** essentially
uninformative — the hard-endpoint human sample of fairly-tested candidates is ~1 (aspirin failed; PEARL was
safety-only), so 0/8 is censoring, not a measured failure rate. **Posterior:** stays low single-digit %,
wide CI, *dominated by the prior because the human evidence barely moves it.* Honest takeaway: "low
single-digit percent, and notice the data hardly updates the prior — which is itself the lesson." This is
stronger and more defensible than "near zero," it makes the title honest, and it reconciles the 10%-vs-0%
drift between the two sister posts. (Leaves the survival-test sim as the stage-1 mechanism, now linked into
the one funnel.)
