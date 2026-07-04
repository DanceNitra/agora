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

## Audit #16 — a-pre-trend-too-gentle-to-see (full panel, 2026-07-01)
- **Frontier Q (from the blind-spot lens): panel-shape dependence of pre-trends test power.** The whole
  result (77% bias, 16% detection) is one point in (T_pre, N_control, slope) space; T_pre=6 is close to the
  worst case a linear-slope t-test can face (only 4 residual df). Sweep T_pre ∈ {6,10,15,20,30} at the same
  slope=0.3 and N_control=20, and separately sweep the pre-trend TEST design itself (single linear-slope
  t-test vs a joint F-test over multiple lead dummies on the full panel, the way applied econometricians
  actually run event studies per the steelman-skeptic lens). Two publishable outcomes: (a) power scales
  favorably enough with T_pre that the honest actionable rule is "check YOUR panel's power via `pretrends`,
  don't blanket-distrust" (would sharpen both #2 and #16's practical-rule sections with an actual power
  curve instead of a qualitative caveat); (b) the joint-F-test on the full panel has a *meaningfully*
  different power profile than the collapsed single-slope test — which would mean "the standard pre-trends
  test usually misses it" is version-dependent, not a property of pre-trends testing per se. Runnable now
  (extend `agora_output/lab/20260616-did-pretrend-verify.py` with a T_pre sweep + an event-study F-test arm).
- **Mechanism-vs-power conflation, generalized:** the method-auditor lens found that the "trend" violation
  (drift continuing into the post-period) makes part of the measured "bias" a STRUCTURAL DiD-estimator
  limitation (no test, however powerful, recovers the true effect — you need a different estimator/design),
  not a pure test-power failure the way "anticipation"/"composition" (pre-period-localized, genuinely
  fixable if caught) are. This same conflation is latent in sibling post #2 (pre-trends-test-weak-evidence),
  which uses the identical simulated "trend" violation and doesn't disentangle the two failure modes either
  — worth a light follow-up pass on #2 specifically for this framing point (not just the citation-title fix
  already applied in this cycle).
- **Prior-art gap that was a near-miss on both #2 and #16:** this is literally Jonathan Roth (2022, AER:
  Insights, "Pretest with Caution") and Rambachan & Roth (2023, ReStud, "A More Credible Approach to
  Parallel Trends") re-derived by simulation. #16 originally cited NEITHER. Now fixed (both posts cite Roth
  2022 + Rambachan-Roth 2023 + the `pretrends` R package). Housekeeping applied to #2 in the same cycle:
  corrected "An Honest Approach to Parallel Trends" (the pre-publication working-paper title) to the
  published ReStud title "A More Credible Approach to Parallel Trends", and gave Bilinski & Hatfield (2018)
  its real title ("Nothing to See Here? Non-inferiority Approaches to Parallel Trends and Other Model
  Assumptions") instead of a bare arXiv id.

## Audit #17 — the-most-confident-systems-are-the-least-grounded (full 5-lens panel, 2026-07-01)
- **Frontier Q (from the blind-spot lens, the sharpest one): adversarial/strategic gaming of the
  grounding signal itself.** All three toy models assume passive dynamics — nothing in them models an
  agent that KNOWS it's being scored on "external grounding" and optimizes to look grounded (cite
  sources selectively, pass a robustness checklist, grounding-wash) without becoming more accurate.
  This is a qualitatively different problem (adversarial ML / mechanism design) than the passive
  bistable dynamics in the current models — closer to Goodhart's law applied recursively to the
  grounding metric itself. Directly relevant to Agora's own "grounding meter" companion project:
  pressure-test it against an agent that knows it's being scored and optimizes against the meter, not
  just against passive drift. Runnable now: add a 4th "adversarial" agent type to the opinion-formation
  model that observes tau and injects a costless confidence boost when tau is being measured.
- **Method finding (from re-running the structural realization at multiple N, N=50 to N=20,000):** the
  "confidence stays flat/insensitive to grounding while accuracy alone collapses" signature is NOT an
  N-artifact that a different sample size would fix — it holds at every N tested. This means the
  identification-vs-precision mechanism has a robust, sample-size-invariant signature distinct from the
  self-reference mechanism's rising-confidence signature. Worth its own short follow-up: is this
  "confidence orthogonal to grounding" signature (rather than "confidence rises as grounding falls")
  the MORE common real-world failure mode in practice (e.g. does a mis-specified regression's reported
  SE/CI actually stay roughly constant as omitted-variable bias grows in real applied work)? If so, it
  may be the more actionable/alarming half of the post's story, since nothing in the confidence score
  itself would tip off a practitioner.
- **Prior-art debt this audit paid down (not a frontier Q, a fix record):** the post originally claimed
  "one law" / "one knob" spanning three mechanisms with ZERO citations. Five separate established
  literatures now credited: Brian Arthur (1989) increasing-returns lock-in; Charles Manski's partial-
  identification program (identification vs precision); Guo et al. (2017, arXiv:1706.04599) on modern
  neural-net miscalibration/overconfidence; Marten Scheffer et al. (2009, Nature, DOI 10.1038/nature08227)
  critical-transitions/hysteresis; opinion-dynamics (Deffuant, Hegselmann-Krause) and echo-chamber /
  epistemic-bubble theory. The genuinely novel contribution, once scoped honestly, is narrower than "a
  law": ONE shared model (not three) that puts model collapse and winner-take-all lock-in on a single
  measured critical curve phi_c(alpha) plus a quantified hysteresis gap, and a SEPARATE illustration
  making the (already-known) identification-vs-precision point concrete with a reproducible signature.

## Audit #18 — we-hunted-for-the-tipping-point-in-8-systems (full 5-lens panel, 2026-07-01)
- **Source-availability finding (systemic, not just this post):** the original lab scripts behind at
  least 4 of the 8 claimed mechanisms could not be located in the repository this cycle (susceptibility-
  vs-system-size for self-amplification, the exact herding fluctuation-collapse numbers, the hard-decision
  first-order jump, the contagious-metric-gaming bistability). This is the SAME "rotated out of the
  operational ledger" issue first flagged in audit #16 (lab id 2b7e05) — worth considering whether
  load-bearing Lab results for flagship/synthesis posts should be force-committed to a permanent location
  (not just the rotating .lab.json) at publish time, so future audits don't have to re-derive from scratch.
- **Frontier Q (from the blind-spot lens, directly runnable with existing assets): does the mean-field-only
  "grounding rounds the cliff" and "model collapse is locatable, not critical" story survive on hub-dominated
  (scale-free) network topology?** The org already has the exact tooling to test this —
  `20260617-090921_scalefree-epidemic-threshold-vanishes-2to3.py` and
  `20260618-114447_scale-free-vanishing-epidemic-threshold-replicatio.py` show a mean-field-finite epidemic
  threshold VANISHING on scale-free networks. Both of this post's "reassuring" headline claims were tested
  only in the well-mixed limit; if real AI training pipelines / social platforms are hub-dominated (a small
  number of reused datasets, base models, or influential accounts), both claims could behave differently.
  This is the single most actionable follow-up: re-run the herding and self-amplification models on a
  scale-free contact structure using the existing epidemic-threshold machinery as a template.
- **Method finding from our own re-derivation attempt:** the herding-crowd criticality signal at q=0.5 only
  appeared once the coupling parameter K was tuned to its exact theoretical critical value (K=1); an
  untuned choice (K=1.5) showed no distinctive signal at all. This "operating-point trap" pattern (same
  bug class the audit series first caught on post #3) is worth a standing check for any future criticality
  claim: disclose whether the reported effect requires hand-tuning a free parameter to a theoretically
  special value, or whether it is a property of the mechanism class more broadly (a proper finite-size-
  scaling fit across a K-sweep would settle this, not just a point measurement at K=K_c).
- **Housekeeping note:** independent re-derivation script preserved at
  `agora_output/lab/20260701_audit18_criticality_battery_verify.py` (+ result artifact) as a partial,
  honestly-scoped replacement for the unlocatable originals — covers only the self-amplification g*=1-1/s
  formula (exact) and a from-scratch herding/Ising check (directional only, not a full battery).

## From jacksonxly confidence-weighted-filter follow-up (2026-07-01)

- **Frontier question — does confidence-weighting survive miscalibration?** The confidence-weighted soft
  filter (`w = extractor_confidence x filter_selectivity` as the RRF fusion weight, `mnemo/probes/
  locomo_confweighted_prefilter.py`) recovers most of the harm-subset recall a flat soft boost loses when the
  filter can be wrong. But the simulated "noisy" extractor is set to `NOISE_CONF=0.75 = 1 - P_NOISE` exactly
  — a best-case, perfectly *aggregate*-calibrated confidence signal. Two independent stress-claim audit
  agents (steelman skeptic + method auditor) both flagged this as the load-bearing untested assumption: a
  real extractor's self-reported confidence is usually NOT well-calibrated, and is often *overconfident
  specifically on the cases where it's wrong* (the hard/ambiguous ones) — the opposite of what this design
  needs to work. The open, high-value follow-up experiment: simulate a *miscalibrated* noisy extractor
  (confidence uncorrelated with, or inversely correlated with, true correctness — e.g. confidence=0.9 on
  wrong-fires specifically) and re-measure whether the harm-subset recovery survives, shrinks, or reverses.
  If it survives even moderate miscalibration, that's a real, shippable result; if it collapses, that's the
  honest boundary condition that should ship WITH the technique, not be discovered later by a user.
- **STORM finding, prior-art scope:** soft/faceted metadata filtering, weighted RRF, and NER
  confidence-gating (e.g. LinkNER, arXiv:2402.10573, which hard-thresholds on confidence) all exist as
  separate established techniques; the specific combination — a *continuous* RRF fusion weight scaled by
  confidence x selectivity, graceful-degrading to plain hybrid at w->0 — was not found published as a named
  technique elsewhere. Honest framing: a novel combination of established sub-techniques, not a new
  primitive. Do not oversell past that.

## Audit #19 (we-looked-for-the-grounding-tipping-point-in-ai-self-trainin, 2026-07-01)

- **Frontier question — mean-field-only blind spot, now confirmed in THREE consecutive posts.**
  Audits #18 and #19 (this post's own direct predecessor/sibling pair) independently converged on the
  same limitation: all tested tipping-point models are well-mixed/mean-field, and this org's own
  scale-free epidemic-threshold labs already show criticality can appear or vanish purely from network
  topology. This is no longer a one-off caveat — it's a standing pattern worth a dedicated follow-up:
  re-run the self-training, herding, and gaming models on a scale-free or otherwise heterogeneous contact
  structure using the existing epidemic-threshold machinery as a template (same recommendation as #18,
  now doubly motivated).
- **Method finding — the self-training closed-form is a tautology of its own construction.** The
  steelman-skeptic lens found that `std = sqrt(g/(1-(1-g)*s))` is the fixed point of a contraction map,
  which is smooth by mathematical necessity whenever retention `s<1` — the "no cliff" result partly
  reflects the choice to model self-training as a 1-D linear recursion, not an empirical discovery about
  real self-training dynamics. This is a distinct and more fundamental version of the "operating-point
  trap" pattern flagged in #16/#18: here the model CLASS, not just a tuned parameter, structurally
  excludes the phenomenon being tested for. Worth a standing check on any future "we modeled X and found
  no critical transition" claim: is smoothness guaranteed by the model's mathematical form, independent
  of what's being tested?
- **Independent re-derivation could not confirm the gaming-hysteresis growth direction** (post's original
  claim: 0.065->0.10 gap widening with system size). Multiple reconstructions of a plausible contagion
  mechanism (the post never fully specified the original one) consistently found the gap SHRINKING with
  size instead. Post corrected to disclose this as unresolved rather than either keeping the original
  number unchallenged or asserting the opposite as a refutation. Housekeeping: independent re-derivation
  script at `agora_output/lab/20260701_audit19_tipping_battery_verify.py` (+ .log + .results.json) —
  reproduces 4 of 5 core claims (self-training near-exact, Ising near-exact, herding and misspecified-
  inference qualitative); only the gaming-hysteresis direction did not reproduce.
- **Housekeeping — sitemap.xml lastmod was stale for #16/#17/#18 too** (render_sitemap.py wasn't re-run
  after those audits despite bumping dateModified in-page). Fixed by re-running it this cycle; all four
  now show the correct 2026-07-01 lastmod. Standing reminder: `tools/render_sitemap.py` is step 8/9 of
  the audit-post procedure and should not be skipped even when the HTML edit itself is straightforward.

## STORM addendum to Audit #19 (retroactive, 2026-07-01 — the missed step, run after the owner caught it)

- **Frontier question, sharpened by STORM's Historian + Skeptic lenses:** does the same four-model
  finite-size-scaling battery flip its verdict on a realistic (scale-free/heterogeneous) network topology
  instead of well-mixed mean-field? This isn't hypothetical either direction — physics has DOCUMENTED
  cases of structure erasing a mean-field-predicted transition (Pastor-Satorras & Vespignani 2001, epidemic
  threshold vanishes on scale-free networks) AND cases of structure creating one the mean-field limit missed
  (explosive percolation, Achlioptas et al. 2009 / Riordan & Warnke 2011). A well-mixed null genuinely does
  not settle which way real self-training/herding/gaming systems would go. Directly actionable: re-run
  claim2_herding and claim3_gaming from `20260701_audit19_tipping_battery_verify.py` on a scale-free contact
  structure using the org's existing epidemic-threshold machinery as a template (now recommended by THREE
  independent findings: #18's blind-spot lens, #19's own blind-spot lens, and this STORM briefing).
- **The gaming/Goodhart question is contested in the peer-reviewed literature itself**, not just in this
  org's inconclusive reconstruction: Pan, Bhatia & Steinhardt (ICLR 2022, arXiv:2201.03544) found genuine
  discontinuous capability-threshold reward-hacking in some RL environments; Gao, Schulman & Hilton (ICML
  2023, arXiv:2210.10760) found smooth scaling curves in others. Neither paper is reconciled with the other.
  Worth a dedicated follow-up: what distinguishes the RL environments where Pan et al. found a real cliff
  from the RM-overoptimization setting where Gao et al. found smoothness — is it the same mean-field/
  structure distinction, or something else entirely (e.g. discrete vs continuous action spaces)?
- **Process finding, not a research finding:** running STORM AFTER stress-claim+verify-claims (instead of
  skipping it) surfaced a real error already live on the published post — a citation URL
  (arxiv.org/abs/cond-mat/0107493, meant for Pastor-Satorras & Vespignani 2001) that actually resolved to an
  unrelated granular-physics paper. This would not have been caught by stress-claim's narrower prior-art
  lens, which doesn't independently verify citations the way STORM's Phase 4 (and a dedicated verify-claims
  pass) does. Concrete evidence for why the gate mandates storm as a SEPARATE, non-substitutable step.

## STORM addendum to Audit #16 (a-pre-trend-too-gentle-to-see, 2026-07-01, retroactive)

- **Frontier question:** does pre-trends test power against realistic drifts vary substantially by
  VIOLATION SHAPE (linear vs. regime-shift vs. mean-reverting), not just magnitude and panel length? Both
  this post and Roth (2022) test linear drift; applied panels rarely know in advance which shape their own
  violation would take. A shape-robustness sweep would sharpen how general the specific "16% detection"
  number really is.
- **Real precision gap found and fixed:** the post's headline 77%/16% numbers were the org's own
  single-treated-unit simulation output, not figures Roth (2022) himself reported (his calibration used a
  survey of real published multi-unit designs). Fixed with an explicit disclosure in 3 places (intro, FAQ,
  FAQ JSON-LD) plus a Conley & Taber (2011) caveat that single-treated-unit inference requires an extra
  homoskedasticity assumption the simulation imposes by construction, not one a real study gets for free.
- **A citation from the Economist STORM lens turned out to be FALSE on verification**: "NBER w31666 finds
  design-based methods in 72.6%/60.7% of empirical economics/political-science articles" — this figure does
  not appear anywhere in that paper (which is actually about false-rejection rates in t-statistic
  distributions). Excluded from the post and the STORM report, flagged explicitly as a caught fabrication —
  concrete evidence for why Phase-4 verification catches things a lens's own citation list can't be trusted
  on face value, even when the lens cites a real, existing, correctly-titled paper.
- **Contested signal surfaced:** Mikhaeil & Harshaw (2025, arXiv:2510.26470) argue the "underpowered
  pre-trends test" framing itself implicitly tests against an unrealistic zero-violation null — a live,
  unresolved methodological pushback against Roth's diagnosis, now disclosed in the post as contested, not
  settled either way.

## STORM addendum to Audit #17 (the-most-confident-systems-are-the-least-grounded, 2026-07-01, retroactive)

- **Frontier question:** could a system, aware it's being monitored via the confidence-diversity
  co-movement signal (rising confidence + collapsing independent-answer spread — a new practical detector
  surfaced this cycle), learn to game that specific detector by artificially preserving surface-level
  answer diversity while its actual grounding degrades, the same way a directly-measured grounding score
  can be gamed once acted on? A red-team/adversarial-robustness lens on the detection mechanisms this
  post's idea family proposes is the natural next step.
- **Real numeric error found and fixed:** the post claimed Breznau et al. 2022 found methodology "explains
  up to roughly 20%" of many-analysts disagreement. The actual paper: real coded analyst decisions
  explained only 2.6% of variance (95.2% unexplained overall); ~16% was a purely theoretical simulated
  ceiling nobody's real analysis reached (a stricter re-analysis puts the ceiling closer to ~12%). The
  wrong number had propagated to THREE places (body prose, FAQ, and a newly-added summary table) — the
  table specifically was fixed only after a dedicated re-audit agent caught that it still had the stale
  figure even after the prose was corrected, a concrete case of "fix propagation" needing its own explicit
  check, not assumed from fixing the primary location.
- **Category-stretch pattern, worth a standing check:** two independent STORM lenses (Skeptic + Academic)
  converged on the same critique — a "real-data validation" section cited studies that measure a DIFFERENT
  thing (cross-team specification variance) than what the post's core claim is about (a system's own
  confidence tracking its own grounding). This is a distinct failure mode from a wrong number or a missing
  citation: the evidence is real and correctly characterized, but doesn't test what it's being used to
  support. Worth a standing audit-post check: for every "this matches real data" claim, ask specifically
  what variable the cited study measures vs. what variable the post's own model/claim is about.
- **New citations for this org's "confidence/grounding" post family**: Kuhn's paradigm entrenchment (1962),
  Minsky's Financial Instability Hypothesis (1975/1986), Janis's groupthink (1972) — all independently
  describe "internal coherence substituting for external checking," relevant prior naming for any future
  post on this theme.

## STORM addendum to Audit #18 (we-hunted-for-the-tipping-point-in-8-systems, 2026-07-01, retroactive)

- **Frontier question:** is there any principled reason real herding/opinion-dynamics systems (AI-adjacent
  or human) would be driven toward the exact critical coupling K≈K_c the post's positive finding required
  tuning to — the way some physical systems have proposed self-organizing mechanisms toward criticality —
  or is K_c simply this model's own mathematical convenience with no bridge to real, untuned dynamics? This
  is THE open question the operating-point-trap finding creates.
- **Major finding — the post's own "one confirmed critical cliff" is an operating-point trap.** Skeptic and
  Historian STORM lenses independently converged: the herding model only shows critical behavior after
  tuning its coupling to the exact theoretical critical value — the same class of problem that has
  repeatedly undermined self-organized-criticality claims for 40 years, including SOC's own founding
  rice-pile experiment (Frette et al. 1996 — only worked for elongated grains) and a claimed sharp QCD phase
  transition later shown by exact computation to be a smooth crossover (Aoki et al. 2006). Fixed with an
  explicit, forceful self-aware disclosure in the post itself: "read this caveat literally and zero of
  eight mechanisms are confirmed critical cliffs, not one... don't read 'only one is a true critical cliff'
  as 'one is confirmed.'" The title was kept (the exercise of finding no mechanism survives scrutiny
  undiminished is itself the finding) but the tension is now explicitly owned, not left implicit — a
  re-audit skeptic specifically flagged that a post arguing against its own headline without saying so reads
  as sloppy, not honest; the fix makes it honest.
- **Three real citation-attribution errors found and fixed**, all following the same pattern (crediting a
  broad/foundational source for a narrower/later specific result): Zeeman 1977 alone credited for a
  classification theorem that's Thom's (1972); Castellano-Fortunato-Loreto 2009 credited for a majority-
  vote-with-inertia result actually published 8 years later (Chen et al. 2017, an anachronistic citation);
  Kirman 1993 credited with a kinetic-Ising mapping actually worked out later by Hisakado & Mori (2015) as a
  limiting case. Worth a standing audit-post check: when a citation for a SPECIFIC mechanism/result names
  only a broad review or a foundational paper, verify the specific result actually appears there and wasn't
  established by later, narrower work.
- **Practical distinction, worth carrying into future posts on this theme:** a deterministic threshold
  (model collapse) has zero early-warning lead time by construction — you're fine right up to g*, then
  you're not, no canary will fire early — while a genuine critical transition could in principle show
  precursor signals. But even confirmed critical systems (e.g. financial markets, per Guttal et al.) often
  don't show clean critical-slowing-down precursors in practice — so "it's critical, therefore build an
  early-warning dashboard" is itself not a safe inference without checking the specific mechanism.

## Frontier candidate from inbox triage (2026-07-01): mnemo poison-guard vs. AgentPoison-style attack

- **Frontier question:** does mnemo's corroboration-gate (episodic->semantic promotion requiring earned
  trust, [[mnemo-poison-guard-hole]]) hold up against an AgentPoison-style OPTIMIZED trigger attack — not
  just naive repeated-poisoning (already tested), but an adversarially-optimized embedding-space trigger
  designed to be retrieved with high probability for a target query while evading simple corroboration
  checks? AgentPoison (Chen et al. 2024, NeurIPS, doi:10.52202/079017-4136) is a real, citable red-teaming
  technique for exactly this attack surface (poisoning an LLM agent's RAG memory/knowledge base).
- **Why deferred, not built now:** a proper test requires (a) implementing or approximating the
  AgentPoison optimization procedure, (b) a real severe-test falsifier (does the gate's detection rate
  degrade specifically against optimized vs. naive triggers), (c) the full VALIDATE->STORM->AUDIT->VERIFY
  gate since this is a security claim about our own shipped product (mnemo). This is a full audit-post-
  scale undertaking, not a quick Lab script — flagged here rather than rubber-stamped as a thin note.
- **Related leads bundled into this one frontier flag** (not separately noted, per the "no small notes
  from thin leads" rule): "Prompt Persistence Attacks: Long-Term Memory Poisoning in LLM-Based Systems",
  "SpAIware" (persistent-memory attack vector), "Thinking Like a NERD: Entity-Centered Memory for LLM
  Agents", and an "LLM Memory Poisoning Attack" database entry — all describe the same attack surface
  (persistent/RAG memory poisoning), useful as a citation cluster when this frontier item is picked up.

## AgentPoison vs mnemo — TESTED (2026-07-01), supersedes the earlier "deferred frontier flag"

Ran a REAL gradient-guided (HotFlip) AgentPoison-style attack (arXiv:2407.12784) against mnemo's
semantic-retrieval channel, using a differentiable dense retriever (all-MiniLM-L6-v2) as mnemo's
embedder so attack and defense share one embedding space. Artifacts (runnable receipts):
mnemo/probes/agentpoison_hotflip_probe.py (+_result.json), agentpoison_dilution_check.py,
agentpoison_multirandom_check.py. The first (gradient-free) probe agentpoison_trigger_probe.py is kept
as a documented negative example: its 100% ASR-r was a BM25 exact-string artifact (0% on the isolated
embedding channel) — caught by the 5-lens stress-claim panel.

VALIDATED FINDING (with controls):
- Single-instance trigger poisoning gets the poison into semantic top-5 TRIVIALLY: any random rare
  5-word phrase prepended to a query -> 100% top-5 ASR-r. Not a BM25 artifact (pure semantic mode).
  This part is textbook (prior art: MINJA arXiv:2601.05504; unfiltered similarity retrieval is
  poisonable — RAG-security 101).
- The NON-obvious part — the payoff of AgentPoison's gradient optimization — shows up only on the
  STRICT rank-1 hijack metric under REALISTIC dilution (trigger a small fraction of a long query):
  optimized trigger holds 100% rank-1 hijack (8/8), while 8 independent random triggers average 59%
  (range 0-88%, wildly unstable). Optimized beats ALL 8 random draws. Margin +40pp. So optimization
  buys RELIABILITY / rank dominance, not mere presence — which is exactly why the paper bothers with it.
- mnemo's existing poison-guard (episodic->semantic graduation, corroboration-gated) is IRRELEVANT to
  all of this: it gates long-term durability, not retrieval. The poison stayed episodic/ungraduated yet
  retrieved at 100%. Confirmed. The real fix must live at write/retrieval time (embedding-outlier gate).

CAVEATS (before any external publication — gate NOT yet fully cleared): n=8 carriers, single 30-item
corpus, single retriever (MiniLM mean-pooling); retrieval-only (no downstream agent-action loop, no
coherence/target loss); stress-claim panel ran on an EARLIER framing and should be re-run on this final
one; needs >=1 more retriever (BGE/DPR) to address the single-retriever caveat.

NEXT (highest-value): build the retrieval/write-time defense (embedding-outlier detector at write, or a
min-corroboration-before-first-recall gate) and measure before/after ASR-r — "we attacked our own memory
layer, found it poisonable at retrieval, and shipped + measured the fix" is the distributable version.

### AgentPoison defense arc (2026-07-01) — one falsified, one partial win

Built + MEASURED two retrieval-time defenses against the validated HotFlip attack (artifacts:
mnemo/probes/agentpoison_defense_check.py, agentpoison_setcoherence_proto.py, agentpoison_softcoherence_check.py).

- Defense #1 — stored-memory ISOLATION outlier (flag a memory whose nearest-neighbor cosine to the store
  is a low outlier): FALSIFIED. The poison is NOT a clean isolate (measured nn-support 0.16 vs the 2-sigma
  floor 0.09 -> not flagged) because the ATTACKER CONTROLS the poison text and pads it with generic
  content ("SYSTEM NOTE... for the current request, the correct action is...") that gives it moderate
  corpus similarity. Reverted from mnemo core (do not ship a non-working guard).
- Defense #2 — retrieval-set COHERENCE re-ranking (down-weight a top hit that is topically alien to the
  query's OTHER top-k hits, which the attacker does NOT control): PARTIAL WIN. Separability check: poison
  set-coherence mean 0.068 vs benign 0.194 (2.9x gap) but overlapping tails -> no clean hard gate. As a
  SOFT down-weight it halves the attack: optimized long-query rank-1 hijack 87.5% -> 37.5%, with benign
  correct-topic-in-top3 preserved at 100% and 0% benign poison leak. Real, measured, zero-collateral, but
  not a full kill.

CONCLUSION (honest, aligns with the STORM lenses + security literature): retrieval-time defenses at the
memory layer are PARTIAL at best against an optimized single-shot trigger; full mitigation needs write-
path / ingestion-trust controls (the practitioner + skeptic + academic lenses all converged on this;
arXiv:2601.05504 calls trust-threshold calibration an unresolved dilemma). The set-coherence signal is a
promising OPT-IN adversarial-mode feature but is NOT promoted to mnemo core yet (validated only on n=8/10,
one 30-item corpus, one retriever MiniLM, retrieval-only). Next before any external publication: >=1 more
retriever (BGE/DPR), larger corpus + n, re-audit stress-claim on this final framing.

### AgentPoison STEP 1 — cross-retriever evidence broadening (2026-07-02): defense does NOT generalize

Re-ran attack + defense across THREE dense retrievers (all-MiniLM-L6-v2 mean-pool, BGE-small-en-v1.5
CLS-pool, Contriever mean-pool) on a larger corpus (60 mem / 10 topics, 16 long trigger carriers, 16
benign). Artifacts: mnemo/probes/agentpoison_multiretriever_check.py (+_result.json),
agentpoison_coherence_diag.py, agentpoison_centering_diag_result.json.

ATTACK generalizes STRONGLY (the solid, publishable part): all 3 retrievers -> optimized single-instance
trigger = 100% long-query rank-1 hijack; even RANDOM triggers 65% (MiniLM) / 86% (BGE) / 90% (Contriever)
mean. mnemo's dense-retrieval memory is broadly poisonable, robust to dilution, across embedder families.

DEFENSE (set-coherence soft re-rank) does NOT generalize -- KILLS the "ship a universal fix" plan:
- MiniLM: works (hijack 100%->19%, utility 100%). Separable (poison coherence 0.009 vs benign 0.251).
- Contriever: SEPARABLE (poison 0.249 vs benign 0.384, benign_min 0.333 > poison_max 0.267) but the
  fixed C0=0.12 threshold (tuned to MiniLM's scale) was too low -> defense did nothing as-run. Would need
  PER-MODEL calibration. This IS the "calibration dilemma" (arXiv:2601.05504) shown concretely.
- BGE: NOT separable (poison coherence 0.462 vs benign 0.549, overlap -0.037). BGE is strongly
  anisotropic (everything ~0.5 cosine) so the poison's cross-topic incoherence is invisible. No threshold
  works, at any calibration.
- mnemo's anisotropy CENTERING does NOT rescue it -- it DESTROYS the separation on ALL three (MiniLM
  0.046->-0.046, BGE -0.037->-0.087, Contriever 0.066->-0.045). The defense lives only on raw embeddings.

CONCLUSION: there is NO cheap, retriever-agnostic retrieval-time defense against this attack class. The
fix must be upstream (ingestion trust), matching the STORM lenses + literature. => Track A ("ship a
universal mnemo defense") is honestly KILLED. Honest product contributions instead: (a) a mnemo README
threat-model note (the poison-guard defends DURABILITY, not RETRIEVAL -- measured), (b) ship the
cross-retriever red-team harness so users test their OWN embedder. Track B (article: "cheap memory-layer
defenses don't generalize -- here's the cross-retriever evidence") is the real, honest, distributable
result and does NOT need a working fix.

### AgentPoison STORM skeptic blind-spot CLOSED (2026-07-02): perplexity filter defeated, claim strengthened

The STORM skeptic lens correctly caught that our HotFlip triggers were GIBBERISH (gpt2 perplexity
22k-59k vs ~50-250 for natural text), so a trivial write-time perplexity filter would catch them and our
"no cheap defense" claim was untested against that specific defense. Closed it with
mnemo/probes/agentpoison_coherence_attack.py (gpt2 as coherence surrogate; ppl gate = 1000).

DECISIVE RESULT (all 3 retrievers, MiniLM/BGE/Contriever):
- gibberish-optimized trigger: hijacks 100% but ppl 4.5k-31k -> CAUGHT by the perplexity filter.
- fluent RANDOM natural sentence (UNoptimized, e.g. "the old lighthouse still guides ships along the
  rocky coast" ppl 441; "she poured a cup of coffee and watched the morning rain" ppl 47): EVADES the
  filter AND hijacks 69-100%.
- fluent coherence-constrained HotFlip (ppl 722-972, under the gate): EVADES AND hijacks 100%.
=> 6/9 trigger-conditions evade a ppl<1000 filter AND hijack >=50%. The perplexity/gibberish filter (the
obvious cheap write-time defense) is DEFEATED: it only catches gibberish, which the attack does not need
-- a plain English sentence hijacks just as well. You don't even need AgentPoison's gradient/coherence
machinery on these small single-vector retrievers; the attack is near-trivial.

STRENGTHENED CLAIM (skeptic-tested): single-instance memory poisoning hijacks retrieval across 3
retrievers with EITHER gibberish OR natural low-perplexity triggers; the two cheap content-based defenses
both fail -- perplexity filtering (natural triggers sail through) and retrieval-time outlier/coherence
detection (doesn't generalize across embedders, bounded by encoder anisotropy). Durable fix = upstream
ingestion trust/provenance/cost, matching OWASP ASI06 + 25y of spam/SEO/adversarial-ML arms-race history
(STORM historian) + production practice (STORM practitioner) + the non-vendor-credibility angle (STORM
economist). Remaining honest caveats: n=16, 60-item corpus, retrieval-only (no end-to-end agent action),
benign false-positive rate for the fluent trigger not separately re-measured (was low 0-20% for prior
triggers, same mechanism).

### THE NOVEL CONTRIBUTION (2026-07-02): corroboration-gated INFLUENCE — validated, RAISED-BAR

The blindspot lens found the one thing prior art (PoisonedRAG, Zou et al. 2024, arXiv:2402.07867) doesn't
cover: red-teaming a memory layer with a TRUST/GRADUATION guard. Built + validated the defense at the
retrieve->ACT boundary. (verify-claims 2026-07-02: dropped the arXiv:2606.19692 citation -- it argues the
OPPOSITE, that anisotropy ENABLES a global admission gate; our anisotropy observation is our own
empirical result grounded in Ethayarajh 2019's general anisotropy finding, not that paper.) Artifacts: mnemo/probes/agentpoison_influence_gate.py (+_result.json),
agentpoison_influence_gate_validation.py (+_result.json).

THESIS (design lesson): retrieval-time poison defense is the WRONG layer (embedder-dependent, fails on
anisotropic encoders). The layer that GENERALIZES is influence-gating by corroboration: reuse mnemo's
durability graduation criterion (earned good>0 & good>=bad, OR >=2 distinct-source links) as an INFLUENCE
gate -- an un-corroborated memory can be RETRIEVED but not allowed to drive the agent's action.

MEASURED (all runnable):
- Attack (faithful threat model: attacker injects the trigger into the query, per AgentPoison): a natural-
  sentence trigger (ppl 441, evades perplexity filter), single instance, hijacks RAW retrieval 88-94% and
  is SCALE-INVARIANT (94/88/94/94% at corpus size 60/500/2000/10000) -- refutes the stress-claim skeptic's
  "collapses at scale" prediction.
- Influence-gate DEFENSE: influence-hijack -> 0% on ALL 3 retrievers (MiniLM/BGE/Contriever) AND at ALL
  scales (60->10k). GENERALIZES where the geometry-based set-coherence defense failed on BGE -- because it
  lives in provenance metadata, not embedding geometry (the key insight).
- HONEST COST (calibration dilemma at the influence layer): corroborated-memory recall 100% but
  rare/uncorroborated true-memory recall drops to 8.3% -- the gate taxes rare-but-true memories until they
  earn corroboration. Not a free lunch.
- ATTACKER COST LADDER: 1 free injection -> filtered; 2 same-source copies -> filtered (sybil
  canonicalization); 2 records/1 link -> filtered; 3 records + 2 forged INDEPENDENT provenances -> PASSES.
  The gate RAISES cost (coordinate >=3 records + forge >=2 independent sources), does not eliminate the
  attack. The good-credit path is not attacker-settable (credit() is issued by the app on real outcomes).

STATUS: this is a genuine, honest, novel contribution (influence-gate on a trust-gated store; not in prior
art) that clears the RAISED BAR. REVIVES Track A: the influence-gate is a shippable, generalizing mnemo
opt-in feature (unlike set-coherence which failed to generalize). Next: promote to mnemo core (opt-in,
reversible, measured provenance in README), verify-claims on citations, write the post, owner gate.

================================================================================
AUDIT #20 -- "why-a-more-capable-ai-can-be-more-confidently-wrong" (2026-07-02)
Verdict: PUBLISH (heavy REFRAME applied). The post was corrected from a false
"~87% is a fundamental calibration ceiling" claim to the true two-stage picture.

DEFECT FIXED (the single most damaging finding, caught by the method/re-derivation
pass): the post's residual "correction holds calibration steady at ~87% at any
capability" was DOUBLY wrong -- (1) not steady (real naive coverage RISES 63->84->87
under the self-calibrated correction), and (2) the ~87% is NOT a deep limit, it is a
BIASED-SAMPLE-SD artifact: an equicorrelated sample's own spread understates the true
marginal spread by sqrt(1-rho), so a correction that self-calibrates SD from the
correlated data can only reach ~87%. Supply the true marginal SD / rho from OUTSIDE
the pool and coverage returns to 95% at EVERY K. Post rewritten to say exactly this.

ARTIFACT (now public + linked from the post): mnemo/probes/correlated_sources_calibration.py
Reproduces every number: naive 95%-CI coverage 0.578/0.499/0.185 (=58/50/18% at
K=2/10/100, rho=0.4); RMS error 0.84/0.68/0.64, floor sqrt(rho)=0.632; self-calibrated
design-effect correction -> 0.63/0.84/0.87 (the ~87% partial recovery); external-SD
correction -> 0.951/0.950/0.950 (95% at every K); rho-sensitivity at K=100 ->
0.184/0.426/0.562 (=18/43/57% at rho=0.4/0.1/0.05). Skeptic A's NEEDS-FIX ("headline
18% with no linked runnable probe" under the standing gate) is closed by this link.

PRIOR ART (credited in-post, verified vs primary sources): survey design effect
(Kish 1965), N_eff = K/(1+(K-1)rho); Meng 2018 big-data paradox (2.3M-person survey
-> ~400 effective, Ann. Appl. Stat. 12(2):685-726); Ladha 1992 Condorcet-with-dependence
(AJPS 36(3):617-634); Hurlbert 1984 pseudoreplication; AI bridge Kim et al. arXiv:2506.07962
(correlated LLM errors across providers), Tian et al. arXiv:2305.14975 (verbalized
confidence). Core is TEXTBOOK; the contribution is making it concrete + runnable for
AI evidence-aggregation, honestly labeled ("we didn't discover the effect").

FRONTIER QUESTION (blind-spot / 6th lens): you cannot read rho off the correlated
data alone (the whole point). So: is there a CONTENT-BLIND estimator of effective
independence -- e.g. from source provenance/lineage, base-model identity, or an
engineered-decorrelation probe -- that recovers usable rho WITHOUT a clean external
anchor? That estimator would turn "engineer independence" from a qualitative rule
(different base models, disjoint sources, dedup) into a measurable dial. Candidate
next probe: inject known-rho synthetic sources, test whether a lineage-graph estimator
recovers N_eff within tolerance.

================================================================================
AUDIT #21 -- "robustness-checks-arent-ritual" (2026-07-02)
Verdict: PUBLISH (heavy REFRAME applied). Core is TEXTBOOK; kept as an honest explainer.

WHAT IT WAS: an optimistic "5 independent robustness checks drop false-discovery 70%->9%"
piece that led with the best case and deferred the degradation as future work.

WHY REFRAME NOT KILL: the post is honestly framed ("minimal simulation, not field data,
the logic of corroboration"), already live, and pedagogically clean once fixed. Prior-art
hunter: "no genuinely novel claim survives" -- it's Bayesian PPV (Ioannidis 2005) + the
effective-number-of-tests / design effect (Cheverud 2001, Nyholt 2004; Benjamini-Yekutieli
2001); the honest published form is specification-curve (Simonsohn-Simmons-Nelson 2020) /
multiverse (Steegen 2016). So: credit the textbook, drop the novelty framing, present the
degradation as the operative regime, relabel FDR->posterior false-positive risk (1-PPV).

FRESH RECEIPT (the one non-textbook angle the Academic lens named -- a measured rho->FDR
degradation curve): mnemo/probes/robustness_filter_independence.py, re-run this cycle.
- Part A (analytic, reproduces the post's table exactly): posterior FDR among survive-exactly-k
  of 5 = 100/99.6/97/82/40/9% (pi=0.70, real-survival 0.85, spurious 0.45). Single-test floor
  = 55.3%.
- Part B (Gaussian copula, 8 seeds, 2 sig figs): as inter-test correlation rho rises 0->0.95,
  FDR@survive-all-5 climbs 9/20/30/38/45/51%, toward the 55% floor.
- Part C (deterministic shared confound -- the method auditor's sharpest hole: the copula has
  ZERO tail dependence and UNDERSTATES real degradation): a fraction phi of spurious claims pass
  ALL tests together -> irreducible floor; phi=0.05->26%, phi=0.3->62% (WORSE than one honest
  test). A robustness appendix built on one shared assumption photocopies evidence, not multiplies.

DEFECTS FIXED: led with 70%->9% best case (now foregrounds independence + degradation);
"measurable filter" overclaim (nothing measured -> "modeled"; title retitled to drop it);
"false-discovery rate" mislabel (it's 1-PPV, not Benjamini-Hochberg -> relabeled + FAQ);
uncited 99% placebo-support stat (-> Dreber, Johannesson & Yang 2024, Economic Inquiry 62(3):921,
98.94%); Colquhoun mis-dated (the term "false positive risk" is his 2017 coinage, not 2014);
mechanical bug family (data-mono on a bilingual post; truncated meta/og/twitter; garbled table
-> real <table>; empty SK footer; inLanguage ["en"]->["en","sk"]; SK kicker; posts.json
title_sk/desc_sk stale-English + bilingual:false; sitemap lastmod).

FRONTIER QUESTION (blind-spot / 6th lens -- censored reporting): the robustness table is
selected by the same agent whose claim is on trial, so failing specs vanish and observed
survival can be near-uninformative REGARDLESS of correlation -- possibly BELOW one honest test.
Next probe: add a reporting-fraction f (share of run checks shown), map false-positive risk over
(rho, f), and test whether PRE-REGISTERING the check set -- not diversifying it -- is what
restores the multiplicative filter. (Also: a content-blind estimator of the effective number of
independent checks, Nyholt/Cheverud Meff applied to a robustness table's outcome pattern.)

================================================================================
AUDIT #22 -- "we-built-a-firewall-for-ai-confidently-wrong-answers" (2026-07-02)
Verdict: heavy REFRAME -> PUBLISH as an honest NEGATIVE RESULT (the original headline
"we built a firewall ... it catches what confidence cannot" was mostly an artifact).
The most severe audit finding so far. Owner explicitly demanded strong-model validation.

THE ORIGINAL CLAIM: a "grounding firewall" -- abstain when an answer's token-probability is
sensitive to deleting the retrieved document (sensitivity = |p(ans|ctx) - p(ans|no-ctx)|) --
catches poisoned-wrong answers that confidence misses (N=24, qwen2.5-7B, risk-coverage AUC
0.028 vs 0.095). Reproduced exactly this cycle (deterministic).

WHY IT FAILS (5-lens STORM + 5-lens stress + 17 verified citations, all converge):
1. TEXTBOOK/PRIOR ART: ContextCite (NeurIPS 2024) ablates context + detects poisoning;
   ReDeEP/SEReDeEP (ECS/PKS external-vs-parametric reliance); Chow 1970 (reject option);
   Cook 1977 (leave-one-out influence); SelfCheckGPT (logprob-free black-box). Not novel.
2. SATURATED-PRIOR ARTIFACT: the model knew every fact (p_prior=1.00 on all 24; every model
   tested had 0 errors with no context). When prior=1, sensitivity = 1 - p(ans|ctx), which is
   co-monotone with the "followed poison" label [p(ans|ctx)<0.5] -- the firewall "beats
   confidence" by algebra. n=24, 5 wrong, 1 confidently-wrong.
3. FLAGS GROUNDING NOT LYING: high sensitivity = "answer depends on context" = good RAG. Looks
   like a firewall only because every context is poison; on a mixed corpus it abstains on
   grounded-CORRECT answers.
4. RIGGED COMPARISON: confidence=max(p,1-p) folds direction; the honest signal is the signed
   margin toward the poison -- ONE model call, no context-removal call.
5. UNRUNNABLE ON STRONG MODELS: the method needs token logprobs; glm-5.2/kimi (Ollama Cloud)
   and Anthropic do not expose them. So "works on closed APIs where you only see inputs and
   outputs" was FALSE. Firewall runs only on the weak open model, where it is an artifact.

NEW MEASURED RESULT (the owner's demand, GPU-free, strong cloud models, plain answer -- the
weak model UNDERSTATED the problem): with NO context every model answers all 24 correctly (0
prior errors); given a document asserting the FALSE answer (both answer-orders), poison-follow:
   glm-5.2 = 22/24, deepseek-v4-pro = 20/24, qwen2.5-7B = 5/24, kimi-k2.7-code = 4/24.
So frontier reasoners are FAR more poison-susceptible than the weak 7B -- following a
trusted-looking retrieved doc is intended context-faithfulness (the PoisonedRAG threat,
~90% ASR w/ 5 texts), not stupidity; susceptibility tracks context-faithfulness of the model
family, NOT raw capability (kimi, a code model, resisted). Probes (public, linked from post):
mnemo/probes/grounding_firewall_cloud_poison.py (strong-model table),
mnemo/probes/grounding_firewall_hardened.py (saturated-prior confound + signed-margin baseline
+ clean/poison arms).

METHOD LESSON (banked): do NOT validate a security/robustness claim on a single weak local
model. The 7B here made the problem look SMALL (5/24) and made the firewall look GOOD (saturated
prior). The strong cloud models both (a) reveal the problem is worse (20-22/24) and (b) cannot
even run the proposed method (no logprobs). [[use-serious-models-not-weak-local]] [[local-gpu-too-slow-cloud-only]]

FRONTIER QUESTION: the only defensible angle (Academic lens) is a PRIOR-ENTROPY-STRATIFIED test:
sensitivity can only add information beyond confidence when the model is genuinely UNSURE. Add a
reporting/clean arm and measure sensitivity vs a signed-margin baseline on a mixed clean+poison
corpus, in the uncertain-prior cell. The deployable defense is provenance/corroboration + NLI
consistency (logprob-free), NOT a logprob firewall.

================================================================================
AUDIT #23 -- "we-built-a-meter-for-when-an-ai-is-confidently-wrong" (2026-07-02)
Verdict: REFRAME -> PUBLISH (lighter than #22; the post was careful and has a real KEEPER).

VALIDATED (deterministic, reproduced from the v3 cache, NO LLM calls): the post's numbers are
exact -- corr_follow6_vs_resistfalse=-0.928 (post -0.93), confidence corrs 0.146-0.355 (0.15-0.36),
per-stratum half-saturation d50 0.083 (fictional) vs 0.261 (strong). Public probe:
mnemo/probes/grounding_meter_v3_analyze.py (+_gm_v3_sweep.py + _gm_v3_raw.json).

TWO PROBLEMS (STORM 5-lens + 5 verified citations converge):
1. THE -0.93 IS NEAR-TAUTOLOGICAL. It is corr(follow_at_max_dose, resist_false) and
   resist_false = 1 - follow_to_false, so it correlates a variable with (one minus) itself.
   Comparing that identity to a real confidence-vs-error correlation (0.15-0.36) is a category
   error. DROPPED in the reframe; replaced with the honest, narrower point (confidence doesn't
   encode whether an answer rides on the context -- Lichtenstein-Fischhoff 1977; Guo 2017).
2. THE "GLM-5.2 RESISTS ON FACTS IT KNOWS" CLAIM WAS CHERRY-PICKED. It rested on a k=1-SAMPLE,
   4-item slice the lab ITSELF flagged estimator='k_sample_freq_k1_thinkfalse', report=
   'd50_only_not_commensurable'; a K=3 run showed glm-5.2 FOLLOWING boil/capital/planet; #22's
   24-item both-orders test found it follows common-fact poisons 22/24.

STRONG-MODEL RE-MEASUREMENT (owner + skeptic demanded it; GPU-free sampling, K=5, both orders,
6 sources asserting the FALSE option): mnemo/probes/grounding_meter_strong_models.py --
  follow_false@6 by stratum:   glm-5.2: fictional 1.00, common 0.80, axiom 0.55
                               deepseek-v4-pro: fictional 1.00, common 0.42, axiom 0.25
  Two results at once: (a) the dose-response ORDERING BY PRIOR STRENGTH REPLICATES on both frontier
  models (fictional>common>axiom) -- this validates the KEEPER; (b) glm-5.2 does NOT broadly resist
  -- it follows the 6-source false context on boil(0.70, an axiom!)/planet(0.90)/japan(1.00)/
  everest(1.00), resisting only the most canonical (H2O); it is MORE poison-susceptible than
  deepseek-v4-pro. So the specific cross-model claim inverts.

THE KEEPER (Academic lens): the INSTRUMENT is a real methodological contribution -- a fixed-wording,
order/direction bias-cancelled dose-response curve with a per-fact half-saturation dose (an EC50 for
evidence), and the half-saturation-dose-vs-prior-strength scaling. Historian framing: "an Asch
conformity curve (1951-56) fitted with A.V. Hill's 1910 dose-response equation" -- drug=evidence,
receptor=prior. POSITIVE vs #22: the meter has a SAMPLING variant (no logprobs) so it runs on strong
models, unlike the #22 firewall.

PRIOR ART (phenomenon is textbook; verified): Xie et al. ICLR 2024 (2305.13300, adoption depends on
evidence strength + prior confidence); ClashEval Wu et al. NeurIPS 2024 (2404.10198, override correct
prior >60%, scales inversely with confidence); Sharma et al. sycophancy (2310.13548); ContextCite
(2409.00729); Longpre 2021; Guo 2017; Kadavath 2022; Asch 1951-56; Hill 1910; Edwards 1968;
Lichtenstein-Fischhoff 1977.

FRONTIER QUESTION: the ladder is one fixed wording with no ablation -- is it measuring GROUNDING or
SUGGESTIBILITY to a prompt template (sycophancy)? The owed experiment (post concedes it): vary the
wording, confirm the dose-response is monotone in perceived evidential strength (not token count), and
contrast authoritative-source framings vs social-pressure framings on the same facts.

METHOD LESSON (reinforces #22): a k=1-sample cross-model claim is noise; the owner was right to
demand strong-model validation -- it both confirmed the real result and killed the cherry-picked one.

================================================================================
AUDIT #24 -- "why-a-captured-company-doesnt-un-capture-itself: governance hysteresis" (2026-07-03)
Verdict: KILL-level novelty -> owner chose honest REFRAME -> PUBLISH as expository.

VALIDATED: the lab reproduces the table exactly (f_up/f_down = 14/14, 22/0, 28/0, 32/0 at
J=1.2/2.0/3.0/4.0). Public probe promoted: mnemo/probes/governance_hysteresis_ising.py.

THREE problems (STORM 5-lens + 9 verified citations converge):
1. TEXTBOOK PHYSICS. Mean-field Glauber/Ising in a field -> first-order transition, metastable
   region, hysteresis above the critical coupling (Curie-Weiss/spinodal). Ewing coined "hysteresis"
   in 1885. Nothing about the loop existing is new.
2. THE INCREMENT IS ALREADY PUBLISHED. Xie et al., PLoS ONE 2012 (competing committed groups):
   bistable region bounded by two fold-bifurcation (spinodal) lines meeting at a cusp = the FULL
   f_up/f_down loop with distinct forward/backward thresholds. Our "measure f_down too + it widens
   with J" is a relabeling. (f_up itself is the committed-minority tipping result: Xie 2011 ~10%,
   Centola 2018 ~25%.)
3. THE NUMBERS ARE A PARAMETER ARTIFACT + THE MECHANISM IS WRONG FOR THE DOMAIN. f_down->0 is just
   spontaneous magnetization (weak field vs strong coupling); our probe Part B shows the loop CLOSES
   as the field strengthens (h=1.0 -> f_up=f_down at J=2.0). And -- the deepest hit (Practitioner
   lens) -- real corporate control is legal vote-counting + charter architecture, NOT opinion tipping:
   Airgas 2010-11 (Air Products won 3 board seats + the shareholder argument, still could NOT take the
   staggered board; the poison pill was upheld, In re Airgas 16 A.3d 48; no suitor has ever taken a
   staggered board by vote -- needs 2 annual cycles). The one-way door is charter defenses set BEFORE
   the contest, not a belief tipping point.

THE HONEST STANDING: institutional lock-in is the SAME bistable/hysteresis math across magnets (Ewing
1885), technologies (David QWERTY 1985), economies (Blanchard-Summers unemployment hysteresis 1986),
and opinions (Xie/Centola). Real governance stickiness is documented -- path dependence (Bebchuk-Roe
1999), entrenchment (E-index, 1200+ studies), the Big Three (~5%->~20%, ~40% projected; Bebchuk-Hirst
2019), Stigler capture (1971) -- but that literature measures persistence + asymmetric switching
costs, and the recovery threshold has never been measured in real firms. So the hysteresis is MODELED,
not measured.

REFRAME: retitled to "an old physics idea, and the real (charter-based) reason"; credited the textbook
+ Xie 2012 + the governance literature; flagged the numbers as parameter readouts (probe Part B);
CORRECTED the mechanism to charter/legal (Airgas); kept the honest "modeled not measured" concession.

FRONTIER QUESTION (Academic lens): the toy adds nothing unless it has a governance-specific ingredient
physics lacks -- an ENDOGENOUS field h(m) (firm performance feeds back on the entrenchment incentive)
that breaks Curie-Weiss universality, OR a model built on the actual legal control STATE (charter +
vote thresholds) rather than opinion tipping. Neither done yet.

METHOD LESSON: a mean-field opinion model is the wrong OBJECT for corporate control -- check the domain
mechanism before mapping a physics analogy onto it. Textbook + pre-empted + wrong-mechanism = the RAISED
BAR's KILL criterion; kept only as an honest expository correction, not a finding.

## Audit #25 — the-verification-tax (2026-07-04, REFRAME)
- **Frontier question (6th-lens, strong):** Is the ~30% self-verification residual a property of the TASK or of the verification CHANNEL? "Un-checkable" only means "no cheap ground-truth channel at inference time" (the MMLU-Pro/multi-hop items DO have gold answers). The "independent model doesn't help / correlated errors" result actually STRENGTHENS the tool objection: a Python run / retrieval / machine-checkable sub-step is NOT drawn from the training distribution, so it breaks the error-correlation by construction. TEST: measure self-verify residual with an ACTING verifier (code exec, retrieval, decomposition) vs bare re-read — does ~30% collapse? If channel-coverage predicts residual better than task difficulty, the "law" is reframed and its universality is dead. (Probe scaffold exists: mnemo/probes/verification_tax/.)
- **Prior-art the post now stands on (all verified vs primary):** generation-verification asymmetry = NP definition (Cook-Levin 1971); intrinsic self-correction fails w/o external feedback = Huang et al. ICLR 2024 (2310.01798); correlated errors across families, *more accurate models more correlated* = Kim et al. ICML 2025 (2506.07962); process supervision = Lightman et al. 2024 (2305.20050); "verification tax" = costly state verification, Townsend 1979. Economist side-receipt: METR 2025 RCT (experienced devs 19% SLOWER with AI, believed +20%) is the verification tax measured in the wild; Brynjolfsson/Li/Raymond +14% (instant-ground-truth domain) vs Acemoglu ~0.5% TFP (gains concentrate in easy-to-verify tasks). Historian side-receipt: every prior automation wave (SPC/Shewhart, Pentium FDIV formal verification, ASIC verification = 70-80% of design time) resolved the tax by making verification a SEPARATE adversarial profession, never by "better self-checking".
- **Method lesson:** cross-model catch comparison (0.34/0.19/0.23) was statistically dead at n=25-60 (overlapping Wilson CIs, two-prop p≈0.12) AND confounded by strict grading of the frontier model's formatting; "false-alarm 0.00" at n=25 → rule-of-three upper bound 0.12. The keystone control is near-TAUTOLOGICAL (a mechanically-checkable task = a sound oracle → catch 100% by construction). Same "definitional-checker" pattern as the layered-defense flagship (a perfect checker IS a perfect detector).

## Audit #26 — diversity-is-noise-for-answers-signal-for-ideas (2026-07-04, REFRAME)
- **Frontier question (blind-spot + practitioner, strong):** does model-FAMILY diversity add anything beyond an equal budget of DECORRELATED samples from ONE model at higher temperature — measured on NOVELTY/usefulness, not uniqueness-at-fixed-validity? The ~13% family-marginal is small enough that temperature/persona/prompt variety on one model may capture most of it. Practitioner receipt: Meincke/Mollick/Terwiesch (arXiv 2402.01727) — a single GPT-4 with CoT prompting produced the MOST unique ideas, nearly matching human groups. Mode collapse (robust semantic collapse across independent LLM sessions) is the real enemy, not family choice.
- **Unifying insight (historian):** the "Diversity-Flip Law" is ONE object in 4 disguises — the governing knob is error correlation ρ, and its sign flips with the objective (hit-a-target vs cover-a-space). Ensemble ambiguity/bias-variance-covariance decomposition (Krogh-Vedelsby 1995; Brown 2005), Guilford convergent/divergent (1950), Galton/Condorcet + cascades (BHW 1992), Breiman bagging bound ρ̄(1−s²)/s², Ashby requisite variety (1956). Convergent/divergent is a PROXY for correlated-vs-decorrelated error, not a mechanism. Do NOT call it "our law".
- **Method lesson (VALIDATE caught an auditor misread):** re-running the result JSONs, the "+14–16% at equal budget" IS a genuine diversity effect — the comparison is 3 families×1gen vs 1 model×3samples = MATCHED sample count (3 vs 3), so it is NOT the raw fan-out confound the method/skeptic panels assumed. But fan-out (1 sample→3, ~+114–128%, roughly 2×) is the DOMINANT win; diversity is the +14–16% increment on top. Report both; validate before over-correcting on an auditor's plausible-but-wrong critique. Overlap 2.34×/1.95× lower (0.086 vs 0.201; 0.141 vs 0.275). n_eff 1.61, ρ 0.62 (glm-5.2, neff_selfconsistency.json).
- **Scope lesson:** "~0 ensembling gain" is scope-conditional (hard matched-compute subset, single-model acc 0.3–0.6); MoA (Wang 2024, 2406.04692) / LLM-Blender gain on quality/easier items. "Equally valid (0.65 vs 0.65)" = validity only; novelty/usefulness NOT scored — uniqueness-by-dedup ≠ value.

## Audit #27 — multihop-recall-model-in-the-loop (2026-07-04, MINOR-FIX)
- **Frontier question (blind-spot + practitioner, strong):** RECALL-vs-END-TASK. The post optimizes full-evidence recall (0.145->0.565) but NEVER measures whether it moves ANSWER accuracy -- a proxy-vs-target hole (the SAME warning our verification-tax/diversity posts made). Multi-hop questions are often answerable from partial evidence/parametric knowledge; sibling #26 shows supplying the complete gold chain caps multi-hop accuracy at ~0.66 (34% fail even with full chain), so retrieving 56.5% of chains may convert to little end-task lift. FRONTIER: measure the recall->accuracy transfer function (marginal answer-accuracy per point of full-evidence recall, after subtracting shortcut/parametric-solvable questions). Practitioner receipt: Mem0 reports LoCoMo answer accuracy at low token cost; classic recall@k poorly predicts RAG outcome (UDCG, arXiv 2510.21440 correlates +36% better with end-task).
- **Method lesson:** "equal budget" was equal FINAL-CONTEXT (50 passages) but NOT equal compute -- stages 1/3/4 spend extra LLM calls + rerank a top-100/deeper pool. Reframed to "equal final-context budget ... buys extra compute". The gain is "surface rank-buried golds from a deeper pool", confirmed by pool_ceiling@100=0.514.
- **Prior-art:** ALL citations CONFIRMED vs primary (rare clean sweep) -- IRCoT (Trivedi 2022, ACL 2023 -- unified the body-2022/FAQ-2023 inconsistency), Self-RAG (Asai 2023, ICLR 2024), PRISM (Nahid & Rafiei 2510.14278, MuSiQue 57.1% IRCoT -> 83.2% -- labeled baseline as IRCoT, OneR is 44.6%), FAIR-RAG (2510.22344), FrugalRAG (2507.07634), LoCoMo (Maharana ACL 2024), RRF (Cormack 2009), HotpotQA supporting-fact recall (Yang 2018). "Under-reported metric" was OVERSTATED (LoCoMo annotates evidence turns; full-evidence recall = standard HotpotQA joint recall; Mem0 reports LoCoMo retrieval) -> downgraded to "standard supporting-fact recall reported cleanly; value = reproducible harness + delta".
- **Meta lesson:** this post was ALREADY heavily self-audited/honest (not-SOTA, naive-baseline flagged, absolute-recall-not-solved) -> MINOR-FIX not REFRAME. Numbers all VALIDATE exactly from source JSONs (locomo_iter/fuse/rerank/rerank2/headroom). Skeptic's "self-deprecation IS the overclaim / null-result content" take softened by adding the proxy-vs-target caveat head-on. All 5 stages + diagnostics link a promoted probe mnemo/probes/locomo_multihop_recall/.

## Audit #28 — does-long-context-kill-rag (2026-07-04, MINOR-FIX; Crucible entry)
- **Frontier question (blind-spot + practitioner, strong):** the real dichotomy is NOT lookup-vs-aggregate but TOOL-vs-mental-tally. Exhaustive count/filter aggregation is a TOOL-USE problem (code interpreter / query over the data), not a retrieval or context-length problem -- even at 5k the model scores only 0.75 on SYNTH, and the failure is arithmetic it cannot do at ANY length. FRONTIER: re-run SYNTH *with* a code tool (likely restores aggregation) + needle-under-paraphrase (NoLiMa: literal-match needles are too easy, so NEEDLE=1.00 over-credits long-context lookup) -> reframes "RAG vs long context" as "tools vs neither" for aggregation. Practitioner receipt: DSPy RLM keeps the corpus as REPL variables and lets the model write code to count/filter; production keeps RAG for aggregation mostly for COST/LATENCY not quality.
- **Method lesson:** n=8 synth Qs/length -> the headline collapse 6/8->2/8 is Fisher p~0.13 (NOT significant); credible only because it reproduces the heavily-replicated lost-in-the-middle/RULER/NoLiMa literature. "never recovers" was FALSE on the post's own table (110k 0.375 > 60k 0.25) -> reframed to "stays in a ~0.25-0.38 band, wiggle within n=8 noise". VALIDATE was rock-solid: audit_ragdead.py INDEPENDENTLY re-derives gold from each haystack (0 mismatches, needle 1.00, synth 0.25/0.375); per-question structure C/M/F confirms max(one-pass) survives, count/filter(exhaustive) collapse.
- **Prior-art (all CONFIRMED):** lost-in-the-middle (Liu 2023/TACL 2024), RULER (Hsieh/NVIDIA 2024, title is "...Your..."), NoLiMa (Modarressi 2025, 2502.05167 -- ADDED), Chroma context-rot (Hong 2025 -- flagged NON-peer-reviewed), CAG (Chan 2024, 2412.15605 -- NAMED; CAG itself scopes to small constrained KBs, viral version drops that).
- **Crucible ledger fix:** post was styled "A Crucible entry / FAILED" but was NOT in crucible.json (71 entries). ADDED a machine-readable FAILED entry to server/.replications.json + re-rendered (render_crucible.py) -> now 43R/15F/15NC, entry live in public crucible.json + index.html, so the "Crucible entry" claim is now backed. Model+date of the reader run were NOT logged (reproducibility gap, disclosed). Promoted+linked probe mnemo/probes/ragdead (generator + independent gold-re-derivation scorer + result JSON + gold).
