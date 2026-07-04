# Multi-hop full-evidence recall on LoCoMo — put the model in the retrieval loop

Receipts behind the post
[*Multi-hop recall on LoCoMo: put the model in the retrieval loop*](https://dancenitra.github.io/agora/public/posts/multihop-recall-model-in-the-loop.html).
The measured claim: applying a **known** iterative/agentic-retrieval recipe to LoCoMo multi-hop, **full-evidence
recall@50** (did *all* the gold supporting turns land in the top-50?) rises from a naive dense baseline to a
model-in-the-loop pipeline, at the same 50-passage *returned* budget. **Not a new method, not a SOTA claim.**

## The numbers (all in the result JSONs, re-checkable)

n = 276 LoCoMo multi-hop questions; mean gold-evidence size 3.17. Diagnostic first: the gold turns are mostly
**present but rank-buried** (recall@100 = 0.514, recall@150 = 0.641 — `locomo_headroom_result.json`), so this is a
**ranking** problem, not a coverage problem.

| stage | full-recall@50 | × naive | result file |
|---|---|---|---|
| naive flat dense top-50 (question only) | 0.145 | 1.0× | `locomo_iter_result.json` |
| + LLM-in-the-loop follow-up queries | **0.297** | 2.05× | `locomo_iter_result.json` |
| + RRF fusion over the follow-up queries (rrf_fonly) | 0.326 | 2.25× | `locomo_iter_fuse_result.json` |
| + LLM reranker over a top-100 pool | 0.482 | 3.3× | `locomo_rerank_result.json` (pool ceiling@100 = 0.514) |
| + adaptive multi-round rerank of a deeper pool | **0.565** | 3.9× | `locomo_rerank2_result.json` |

One or two sharp bridge follow-up queries are optimal; asking for more dilutes the RRF fusion (observed across
`exp_locomo_iter_fuse*` runs, not tabulated here).

## What is and isn't the contribution (honest)

- **The mechanism is 100% textbook**, not ours: read results → name the missing fact → follow-up query → retrieve
  again → fuse → rerank. That is **IRCoT** (Trivedi et al. 2022, ACL 2023), **Self-RAG** (Asai et al. 2023, ICLR
  2024), **FLARE/ITER-RETGEN**, and 2025 successors **PRISM** (Nahid & Rafiei, arXiv:2510.14278 — MuSiQue passage
  recall **57.1% [IRCoT] → 83.2%**), **FAIR-RAG** (arXiv:2510.22344), **FrugalRAG** (arXiv:2507.07634). Fusion is
  **RRF** (Cormack et al., SIGIR 2009); the reranker is LLM listwise (RankGPT-style). We claim **no** methodological
  novelty.
- **The baseline is deliberately naive** (single-shot dense top-50 by question similarity), so the 3.9× is "a known
  recipe fixes a weak baseline", **not** "we beat SOTA". A strong agentic baseline (IRCoT/PRISM-class) would start
  far higher — that comparison we did **not** run.
- **"Full-evidence recall" is a standard metric** (HotpotQA joint / supporting-fact recall — all gold facts
  retrieved; Yang et al. 2018), applied to LoCoMo, which is normally scored by end-task QA F1 / LLM-judge (Maharana
  et al. ACL 2024). The real, modest contribution is the **cloud-free reproducible harness + the delta** on a real,
  unsaturated frontier — not the metric.

## Honest limits

- **"Equal budget" = equal FINAL-CONTEXT budget** (every row returns 50 passages), NOT equal compute: stages 1/3/4
  spend extra per-query LLM calls and the rerankers inspect a top-100 / deeper pool. The lift buys "look at a deeper
  pool + spend more compute, then compress to 50", not a bigger returned context — a real cost/recall knob.
- **Recall is a PROXY, not the end task — and we did not measure the transfer function.** We never checked whether
  moving full-evidence recall 0.145 → 0.565 moves *answer accuracy*. Multi-hop questions are often answerable from
  partial evidence or parametric knowledge, so some of the recall gain may land on already-answered questions. A
  sibling result (supplying the gold facts caps multi-hop accuracy at ~0.66) suggests the end-task ceiling is well
  below full recall. The recall→accuracy return per point is the open question.
- **One dataset** (LoCoMo, 10 two-person conversations; the bridge entity is usually a *name*, relatively easy to
  surface with a follow-up query). Absolute recall is ~57%, **not** solved.

## Files

- `exp_locomo_headroom.py` — the recall@k diagnostic (present-but-buried).
- `exp_locomo_iter_C.py` — naive vs LLM-in-the-loop follow-up retrieval (0.145 → 0.297).
- `exp_locomo_iter_fuse.py` — RRF fusion variants over the follow-up queries (best rrf_fonly = 0.326).
- `exp_locomo_rerank_C.py` / `exp_locomo_rerank2_C.py` — LLM rerank of a top-100 / merged deeper pool (0.482 / 0.565).
- `*_result.json` — the raw numbers for each stage.

These are the original multi-phase harness (local Ollama embeddings + `qwen3-coder:30b`; they read LoCoMo data +
phase-A/B intermediates from the lab dir, so they document the method rather than run one-command). For a fully
self-contained, one-command LoCoMo retrieval diagnostic see
[`mnemo/probes/locomo_retrieval_map.py`](../locomo_retrieval_map.py).

MIT-licensed. Part of Agora / mnemo (https://github.com/DanceNitra/agora/tree/main/mnemo).
