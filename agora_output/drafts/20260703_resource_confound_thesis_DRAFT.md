# DRAFT (NOT PUBLISHED) — "The resource confound: four cognitive-method wins that weren't"
# Honest-negative, Crucible-style credibility piece. Gated: needs the full validate->storm->audit->verify
# pass + owner approval + bilingual EN/SK + SEO before any publish. Runnable receipts already public.

## Thesis
In LLM cognition and agent memory, an apparent win from a "cognitive method" — decomposing a judgment,
gating a memory, ensembling judges, re-ranking by a clever feature — is, more often than practitioners
assume, a **resource confound**: the method quietly spends more compute/tokens, or leans on a simpler proxy,
or reduces to a known impossibility result. Before you credit the method, control for the resource and cite
the prior art. We measured four instances of this in a single day, each with a runnable receipt.

## The four (each a public probe you can re-run or break)
1. **"Decomposed judging beats holistic, and the gap grows with claim complexity."** Looked strongly true:
   on composite arithmetic claims, a per-sub-claim binary judge beat a one-shot holistic judge by a margin
   that grew to +0.73 (deepseek-flash) / +1.00 (deepseek-pro) at 8 sub-claims. **Confound: the decomposed
   judge makes K calls = K× the token budget, while the holistic judge got one tightly-capped call.** Give
   the holistic judge equal tokens and the gap is **0.00 at every complexity**, across deepseek-v4-flash,
   deepseek-v4-pro, kimi-k2.6 (two model families), and Claude. It also disappears on chained
   affirming-the-consequent fallacies (hint-free, with distractors): a well-resourced holistic pass catches
   them. Receipts: `mnemo/probes/atomic_decomposition_calibration_law.py`, `_crossfamily`, `_subtle_errors`.
2. **"An embedding-norm re-ranker recovers recall that cosine throws away."** True that norm-aware re-rank
   beat cosine (+0.043 recall@10 on LoCoMo, CI excludes 0). **Confound: the raw norm is a length proxy**
   (corr(|d|,token-length) = −0.71); a pure length prior does identically well (norm−length = −0.0001, CI
   crosses 0). No specificity signal beyond length. Receipt: `mnemo/probes/norm_specificity_reranker.py`.
3. **"A stateful burst monitor closes the corroboration-gate poisoning hole."** It withholds all-fresh-source
   burst corroboration — but **it can't tell a Sybil burst from two genuine new sources reporting at once**
   (TPR = FPR = 1 in the fresh-burst regime), and it's bypassed by dripping or pre-aging domains. Not a
   detector, a false-positive surface. Receipt: `mnemo/probes/bseries_forged_provenance_stateful_monitor.py`.
4. **"Blast-radius-scaled authority defends poisoned agent memory."** It recovers the recall tail — but it
   **reduces to Douceur's 2002 Sybil impossibility** (the high-stakes tier still rests on an unforgeable
   independence test), it gates who *authorizes* an action rather than what its *context* says (the low-blast
   read it opens is the carrier), and its numbers are hand-constant artifacts. Prior art: NIST RAdAC, Biba
   integrity, CaMeL. Receipt: `mnemo/probes/bseries_blast_radius_soft_authority.py`.

## The discipline that follows
- **Match the compute.** If a method makes N sub-calls, give the baseline N× the budget before comparing.
- **Find the cheap proxy.** Add a length arm, a recency arm, a "spend more tokens" arm; if it matches, the
  method is that proxy.
- **Name the impossibility.** Provenance/corroboration defenses bottom out on Sybil (Douceur 2002) unless
  identity has a mint-cost; risk-scaling is Biba/RAdAC. Cite it and scope the claim.
- **A refutation deserves a confirmation's rigor** — cross-family + an independent judge before you kill it.

## What is genuinely open (not a confound, not settled)
Whether decomposition helps on *informal* reasoning with genuinely hidden premises (Theoria reports 90.6% vs
62.5% for a holistic judge). Our clean-ground-truth probes can't reach that regime; it needs harder,
harder-to-score material. And the forward door for provenance defenses: a real **cost to mint an identity**
(attestable/signed source credentials, or earned-and-verified standing) — the one path Douceur doesn't block.

## Provenance
All receipts MIT, public at github.com/DanceNitra/agora/tree/main/mnemo/probes, re-runnable. Numbers measured
2026-07-03 on deepseek-v4-flash/pro (ollama.com), kimi-k2.6:cloud, nomic-embed-text (local), LoCoMo.
