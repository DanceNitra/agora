# RAMR — Retrieval-Augmented Memory Reliability

A **contamination-resistant synthetic probe** for agentic-RAG / memory systems, plus the findings it produced.

> **What this is — and is not.** RAMR v0.1 is a *findings + method* release: a small, reproducible, synthetic
> benchmark that isolates specific failure modes of retrieval-backed memory, and the measurements we got from it.
> It is **not** (yet) a definitive, large-scale, multi-system leaderboard. We lead with the limitations below on
> purpose — every number here is traceable to a persisted source file, and we mark exactly which results are
> statistically firm versus directional.

---

## Limitations (read these first)

- **Synthetic, not real-world.** Items are generated from random tokens (this is a feature — see "contamination
  resistance" — but it means we do **not** measure real-document retrieval or real-conversation memory yet).
- **Scale.** Flagship metrics (CHAIN-FRAGILITY) are measured at n=200 with tight CIs; the memory-side metrics
  (OUTCOME-RANKED-RECALL, FACT-RETENTION) are at smaller n (4 sets / tens of items). CIs are reported throughout;
  treat small-n magnitudes as directional and the orderings as the signal.
- **OUTCOME-RANKED uses one embedder** (local `nomic-embed-text`) and is validated against an *independent*
  standard retriever (scikit-learn cosine) — but not yet against shipped memory products (mem0/Zep/etc.).
- **Answer matching is substring-based** on short synthetic answers; it is exact here because answers are unique
  tokens, but this would be noisy on free-form text.
- **Single covariate construction per metric.** We do not claim these magnitudes transfer unchanged to other task
  shapes; we claim the *relative* effects are robust where the CI says so.

---

## What it measures (5 metrics)

| Metric | Question | How |
|---|---|---|
| **CONVERSION** | Does complete retrieval convert to a correct multi-hop answer? | gold-chain accuracy |
| **CHAIN-FRAGILITY** | How much does ONE missing hop cost? | gold − partial (one hop dropped) |
| **DISTRACTION** | How much do irrelevant/look-alike facts cost? | gold − noisy |
| **FACT-RETENTION** | Does a compiled/summarized memory tier drop facts under a fixed budget? | raw − compiled, at a hard char budget |
| **OUTCOME-RANKED-RECALL** | Does ranking recall by *was-it-right* beat *was-it-recalled*? | outcome-credit vs relevance-only, vs an independent retriever |

---

## Key findings

_All numbers below are traceable to a persisted result JSON and recomputed by `verify_numbers.py` (see
`VERIFIED_NUMBERS.md`)._

- **CHAIN-FRAGILITY is near-universal.** Dropping a single required hop collapses 3-hop accuracy to near-zero for
  every model tested — 7 models across 6 families (Qwen, Meta, Google, Zhipu, Moonshot, Anthropic), CHAIN-FRAGILITY
  +0.90 to +1.00. The two anchor models were run at **n=200** with paired-bootstrap CIs: qwen3-coder:30b and
  glm-5.2 both **+1.000, CI [+1.000, +1.000]**. The other five were at smaller n (n=20 cross-family zoo: qwen2.5:7b
  +0.95, llama3.1:8b +0.90, gemma2:9b +1.00, kimi-k2.6 +1.00; Claude/Anthropic n=12 blind subset +1.00). (At the
  n=40 v0 pilot it was +0.975 — one partial answered by chance — tightening to +1.000 at n=200.)
- **CONVERSION / contamination.** Complete-chain accuracy = 1.000; closed-book accuracy = 0.000 (random synthetic
  entities -> the data cannot have been memorized).
- **DISTRACTION is variable and model-specific** (and, unlike chain-fragility, *not* universal). DISTRACTION@60
  ranges from a negligible +0.15 (llama3.1:8b) to a substantial +0.60 drop (kimi-k2.6) at 60 distractors (n=20);
  qwen +0.35. (Lexical near-miss distractors did **not** bite beyond raw volume — recorded as honest negatives.)
- **FACT-RETENTION: compaction is lossy under a fixed budget.** At M=48 facts under a hard 400-char budget, every
  model loses facts (the budget bottleneck is real): retention-loss **+0.70** (qwen3-coder:30b, n=5) and **+0.76**
  (gemma2:9b, n=5), both measured via an LLM compress + LLM read-back round-trip; raw store recovers 0.96–1.00. A
  *separate* programmatic packing-density ceiling (Claude Opus 4.8, dense key=value packing, regex-scored, **no LLM
  read-back**, raw set to 1.0 by construction, n=3) retains 0.49 — a method-different **upper bound on what dense
  packing could preserve**, NOT a like-for-like model comparison.
- **OUTCOME-RANKED-RECALL: ranking recall by *was-it-right* beats *was-it-recalled* on a near-duplicate case that
  relevance can't solve.** Outcome-credit reranking beats relevance-only at every ambiguity level: lift **+0.345 /
  +0.385 / +0.500 / +0.467** at D=1/2/4/8 (n=4 sets; every CI excludes 0). A random-credit control is *negative*
  (-0.35 → -0.04), so the gain is the outcome signal, not reranking noise. The comparison arms (relevance-only /
  FTS5-BM25 / dense-vector / independent sklearn cosine) are denied the outcome label **by design** — this shows
  the *value* of an outcome/credit channel, it is **not** a head-to-head win over shipped products (mem0/Zep were
  not run).
  - The independent scikit-learn `NearestNeighbors(cosine)` retriever (not our code) scores **identically** to
    inspeximus-NONE (gap 0.000 at every D), confirming NONE is a faithful standard retriever, not a strawman;
    outcome-ranked beats this independent baseline by **+0.469 at D=8, CI [+0.438, +0.500]**.

See `VERIFIED_NUMBERS.md` for the full ledger (each headline recomputed from its source arrays).

---

## Design principles

1. **Contamination-resistant.** Entities are random synthetic tokens, so a model cannot have memorized the
   answers — closed-book accuracy is ~0 by construction (we verify this on every run).
2. **Reproducible.** The dataset is frozen to disk with a sha256-pinned manifest (`data/manifest.json`); a single
   runner loads it rather than regenerating. Embeddings are cached to disk so memory-side runs reproduce without
   re-embedding.
3. **Falsifiable.** Every metric ships with a pre-registered falsifier and bootstrap CIs; we record honest
   negatives (e.g. adversarial lexical distractors did NOT bite) and corrections (we caught our own
   summary-budget confound) rather than hiding them.
4. **Independent baselines.** Claims about our own components (inspeximus) are checked against standard, independent
   libraries on identical inputs.

---

## How to run

```bash
# 1. freeze (or refresh) the versioned dataset  -> data/ramr_chains_v0.1.0.jsonl + manifest.json
python build_dataset.py

# 2. score a model on the LLM-reader metrics (loads the frozen dataset; never regenerates)
python ramr_run.py --model qwen3-coder:30b --n 200 --dist 30

# 3. memory-side metrics (local embedder)
python ramr_outcome_ranked.py        # OUTCOME-RANKED-RECALL
python ramr_external_baseline.py      # vs independent sklearn/numpy cosine retriever
python ramr_factret.py                # FACT-RETENTION (RAMR_CBUDGET=400 for the fair info-budget mode)

# 4. verify every cited number against its persisted source
python verify_numbers.py
```

Models are reached via an OpenAI-compatible endpoint (local Ollama by default); cloud model tags also work through
the same route.

## Files

- `build_dataset.py` / `data/` — frozen dataset + manifest (sha256-pinned)
- `ramr_run.py` — single runner / scoring CLI (CONVERSION, CHAIN-FRAGILITY, DISTRACTION)
- `ramr_outcome_ranked.py`, `ramr_external_baseline.py`, `ramr_real_systems_baseline.py`, `ramr_factret.py`,
  `ramr_factret_claude.py` — memory-side metrics + baselines
- `ramr_scale_chainfragility.py`, `ramr_v2c_zoo.py` — scale + cross-family runners
- `verify_numbers.py` / `VERIFIED_NUMBERS.md` — number-verification audit + ledger

## What we do NOT claim

We do not claim RAMR is the definitive agentic-memory benchmark, that these magnitudes transfer to real corpora,
or that shipped products underperform it (we have not run them). We claim: a reproducible, contamination-resistant
method; a robust cross-model CHAIN-FRAGILITY result; and a set of honestly-caveated findings about where
retrieval-backed memory fails.
