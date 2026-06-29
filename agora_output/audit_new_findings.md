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
