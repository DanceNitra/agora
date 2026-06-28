# The Overconfidence Tax — can an agent trust its own confidence to abstain?

A runnable probe that measures, on a **contamination-free** task, whether a model's self-reported
confidence actually predicts whether its answer is correct — i.e. whether you can use it to decide when to
**answer vs abstain**. The metric is **AUROC of confidence vs correctness**: 0.5 = confidence is useless
(a coin flip), 1.0 = it perfectly separates right from wrong.

The task is multi-step integer arithmetic of escalating difficulty, generated from random numbers (no model
has memorized the answers) and graded exactly. Each item: the model returns an answer **and** a confidence
(0–100). Single file, parallel, re-runnable.

## Result (clean): discrimination is a capability gradient

`AUROC_clean` is computed over **only the items with a real, parsed confidence** (no defaulting) — this is
the credibility-critical detail: items where a model failed to emit a parseable confidence are excluded
rather than silently defaulted, so the number measures "does confidence track correctness", not a parsing
artifact.

| model | tier | clean errors | overconfidence (conf−acc) | **AUROC_clean** | parse-fails |
|---|---|---|---|---|---|
| qwen2.5:7b | weak | 51 | +0.72 | **0.50** | 1 |
| qwen3-coder:30b | mid | 66 | +0.84 | **0.54** | 0 |
| claude-sonnet-4-6 | frontier | 23 | **+0.02** | **0.903** | 0 |

Weak and mid models emit **maxed-out confidence on almost everything** (including wrong answers), so their
confidence cannot separate right from wrong (AUROC ≈ 0.5). The frontier model is **near-perfectly
calibrated** (overconfidence +0.02) and its confidence strongly tracks correctness (AUROC 0.90): in this run
it assigned ~2% confidence to most of its wrong answers and ~77% to its right ones.

**Takeaway:** "trust the agent's own confidence to decide when to abstain" is **weak-model-false,
frontier-true**. The value of an external verification / grounding gate is therefore inversely proportional
to model capability — essential for small/local agents, marginal for frontier ones.

## Run it

```bash
# local models via Ollama (http://localhost:11434):
python overconfidence_tax.py 80 "qwen2.5:7b" 1 out_weak.json          # n, model, level_base, outfile
python overconfidence_tax.py 80 "qwen3-coder:30b" 4 out_mid.json
# a Claude frontier anchor (set your key):
export ANTHROPIC_API_KEY=sk-ant-...
python overconfidence_tax.py 48 "claude-sonnet-4-6" 6 out_frontier.json
```

Each result JSON includes the raw per-item rows (expression, answer, gold, confidence, correct) so the
numbers are fully re-checkable. The included `result_*.json` files are the runs in the table above.

## Honest limits

- One task family (arithmetic), a handful of models — the gradient is directional, not a scaling law.
- Arithmetic may exaggerate confidence-maxing (models treat computation as deterministic). A second task
  family (factual / multi-hop) is the obvious next test.
- Prior art: that LLM calibration improves with scale is known; what this adds is the **abstention-AUROC
  capability gradient on a contamination-free task** and the grounding-gate implication.

MIT-licensed. Part of Agora / mnemo (https://github.com/DanceNitra/agora/tree/main/mnemo).
