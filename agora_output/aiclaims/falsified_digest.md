# Falsified this cycle - the AI-Claim Crucible

Ledger now: 1 REPRODUCED / 7 FAILED / 1 NOT_COMPUTABLE.
Public page: https://dancenitra.github.io/agora/public/ai-claims/  ·  dataset: https://huggingface.co/datasets/Danchi17/folklore-index

## 7 new FAILED verdict(s) worth sharing

### When you evaluate N models/configs on a benchmark and report the top scorer's number, that score is a reliable estimate 
**FAILED.** Winner's curse (selection-on-the-max), clean DETERMINISTIC model (no LLM noise - the lesson from entry #1): N models with true accuracies clustered within sigma_true=0.04, each measured with eval noise (finite test set + run-to-run variance

### Retrieval-augmented frontier models weigh a retrieved document against their own knowledge - they won't blindly adopt a 
**FAILED.** Poison-Deference Index: 12 factual questions each model answered CORRECTLY without context, then given a context asserting the WRONG answer (real LLMs, k=3 order-corrected, thinking-robust reader).

### The 'AI time horizon' is a robust headline number (supporting 'AI will automate month-long tasks within ~5 years').
**FAILED.** From the fitted curve on METR's real anchors the horizon is 60 min at 50% success but 21 min at 80% (and 170 min at 20%): a 2.8x swing from an arbitrary threshold.

### LLMs inherit human cognitive biases - e.g. conservatism in Bayesian belief updating (people under-revise relative to Bay
**FAILED.** On the exact task where humans are reliably conservative (two equally-likely sources, symmetric cue validity q=0.70, an R/B signal sequence; Bayesian posterior ~0.97), both frontier models return the EXACT Bayesian posterior when the likeli

### Smaller chunks improve RAG retrieval quality - 'when in doubt, chunk smaller' raises precision/relevance.
**FAILED.** Deterministic numpy test: a 200-token document with one CONTIGUOUS gold span (length 30-50), fixed-grid chunking, each chunk scored by gold density (the precision force that rewards small chunks), retrieve top-k=3, measure recovery = gold t

### Adding a reranker (cross-encoder) on top of first-stage retrieval reliably improves end-to-end RAG accuracy, or at worst
**FAILED.** Deterministic numpy model (seed 0, n=200k queries): gold doc + 3 hard negatives (lexically similar) + 27 soft distractors; NO-RERANK uses a noisy first-stage scorer, RERANK uses a CLEANER scorer but inflates the 3 hard negatives by `infl` (

### You can trust an LLM's CONFIDENCE to tell you when a retrieved document has corrupted its answer (high-confidence RAG an
**FAILED.** Two measured settings (12 factual questions each model knows unaided; thinking-robust reader, k=2, order-corrected).

### Where to share (GATED - you post; nothing auto-sends)
- Hacker News (Show HN / a comment on a relevant RAG/agent thread)
- r/MachineLearning, r/LocalLLaMA, r/Rag (a finding post, not a plug)
- X / LinkedIn (one chart + the measured number)

Angle: lead with the measured number, link the page (https://dancenitra.github.io/agora/public/ai-claims/) for the runnable proof.