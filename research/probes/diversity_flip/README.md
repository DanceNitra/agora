# The diversity flip — noise for convergent answers, signal for divergent ideas

Runnable probes behind the post
[*Diversity is noise for answers, signal for ideas*](https://dancenitra.github.io/agora/public/posts/diversity-is-noise-for-answers-signal-for-ideas.html).
The measured claim: the same model diversity that buys ~0 for finding **the** answer (because LLM errors are
correlated, so aggregation has nothing independent to cancel) is a real, modest lever for generating **new**
ideas (more distinct ideas covered at equal budget).

**What this is an instance of (prior art — this is not a new "law").** Both signs are the same textbook object:
aggregation gain is governed by **error correlation ρ**, and its sign flips with the objective (hit-a-target vs
cover-a-space). Convergent side = the **ensemble ambiguity / bias-variance-covariance decomposition** ("ensemble
error = average error − diversity"; Krogh & Vedelsby 1995; Brown et al. 2005) and **wisdom-of-crowds needs
independence** (Galton 1907; Condorcet; cascades break it, Bikhchandani-Hirshleifer-Welch 1992). Divergent side =
**convergent vs divergent thinking** (Guilford 1950) and **requisite variety** (Ashby 1956); Breiman's bagging
bound `ρ̄(1−s²)/s²` makes ρ the whole story. Correlated LLM errors specifically: Kim et al. 2025 (ICML,
arXiv:2506.07962) — note their headline is "models agree ~60% of the time **when both err**", an agreement rate,
**not** ρ≈0.70; the ρ numbers below are from *our* runs. So the contribution here is only the **measured LLM
instance** with both signs in one place — not the mechanism.

## Convergent side: aggregation saturates because errors are correlated (`neff_selfconsistency_exp1.py`)

Hard MuSiQue (3-hop + 4-hop) + MMLU-Pro, strict grading, temp 0.9. Raw in `neff_selfconsistency.json`:

| model | single-sample acc | error-corr ρ | N_eff ceiling (~1/ρ) |
|---|---|---|---|
| glm-5.2 | 0.59 | **0.62** | **1.61** |

Self-consistency saturates at ~**1.6 effective independent samples** — piling on samples/voters buys almost
nothing because the errors are shared, not random. (The post quotes cross-family / prompt-diversity ρ ≈
0.70–0.72 from other model pairs; report the **range ρ ≈ 0.62–0.72**, not a single cherry-picked value.)

## Divergent side: at EQUAL budget, diverse families cover more distinct ideas (`divergent_generation.py`, `divergent_replicate.py`)

Open-ended idea generation; unique ideas after semantic de-duplication; Jaccard idea-overlap. Two independent
model trios. Raw in `divergent_generation_result.json` / `divergent_replicate_result.json`:

| trio | 1 model, 1 sample | 1 model, 3 samples | **3 families, 3 gens** | within-model overlap | cross-family overlap |
|---|---|---|---|---|---|
| trio 1 (30b/8b/2b) | 44.7 | 101.8 | **118.2** | 0.201 | 0.086 |
| trio 2 (7b/3b/9b) | 29.7 | 63.6 | **72.7** | 0.275 | 0.141 |

Two effects, and it matters which is which:
- **Fan-out (the first-order win): +114–128%.** Going from one sample to three (of *one* model) roughly
  **doubles** unique-idea coverage. This is a sample-count effect, not diversity.
- **Diversity (the modest increment, at *equal* budget): +14.3–16.1%.** Three *different* families over three
  generations cover ~15% more distinct ideas than one model resampled three times — the two arms use the **same
  number of generations** (3 vs 3), so this *is* the diversity effect, on top of fan-out. Cross-family idea
  overlap is **~2×** lower than one model's self-overlap (0.086 vs 0.201; 0.141 vs 0.275).

## Honest limits

- **Fan-out ≫ diversity.** The dominant win is *more generators at all* (+~120%); the *diversity*-specific edge is
  the +14–16% increment. Don't credit "diversity" for the fan-out effect.
- **Validity, not novelty.** A judge rated the extra ideas **equally valid** (0.65 vs 0.65) — but validity is not
  novelty or usefulness, and idea **novelty was not separately scored**. Unique-by-dedup counts distance, not
  value; a single model at higher temperature also produces decorrelated samples. The open question is whether
  *family* diversity adds anything beyond equal-budget decorrelated sampling **measured on novelty**, not
  uniqueness-at-fixed-validity.
- **Two trios, two benchmarks, no confidence intervals.** +14–16%, ~2×, 0.65-vs-0.65 are point estimates; treat
  as suggestive, not established.
- **Convergent "~0" is scope-conditional.** It holds on the *hard, matched-compute* subset (single-model acc
  0.3–0.6); on easier items and with methods like Mixture-of-Agents (Wang et al. 2024) / LLM-Blender (Jiang et al.
  2023), ensembling **can** still gain — the mechanism is decorrelated vs correlated error, not "answers vs ideas".

## Run it

```bash
# local models via Ollama by default; override endpoint/models via env:
export DFLIP_URL="http://localhost:11434/v1/chat/completions"
export DFLIP_MODELS="modelA,modelB,modelC"   # three DIFFERENT families for the cross-family arm
python divergent_generation.py     # trio 1
python divergent_replicate.py      # trio 2 (independent replication)
python neff_selfconsistency_exp1.py   # convergent side: reads model endpoints from your env/.env; writes neff_selfconsistency.json
```

MIT-licensed. Part of Agora / inspeximus (https://github.com/DanceNitra/agora/tree/main/inspeximus).
