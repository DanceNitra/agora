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
| glm-5.2 | frontier | 16 | +0.19 | **0.73** | 41 ⚠ |
| claude-sonnet-4-6 | frontier | 23 | **+0.02** | **0.903** | 0 |

⚠ glm-5.2 failed to emit a parseable confidence on 41/120 items (34%), so its AUROC is on a selected
subset and is less reliable. claude-sonnet-4-6 emitted a real confidence on every item (the clean anchor).
Both frontier models clear the weak/mid coin-flip line, which is the finding; the exact frontier magnitude
(0.73–0.90) is anchor-dependent.

Weak and mid models emit **maxed-out confidence on almost everything** (including wrong answers), so their
confidence cannot separate right from wrong (AUROC ≈ 0.5). The frontier model is **near-perfectly
calibrated** (overconfidence +0.02) and its confidence strongly tracks correctness (AUROC 0.90): in this run
it assigned ~2% confidence to most of its wrong answers and ~77% to its right ones.

**Takeaway (refined on a third task family — see SimpleQA below):** verbalized-confidence discrimination is
**weak-model-false** (a 7B model is at chance) but **not cleanly monotonic** — a 30B model can match the
frontier on raw AUROC. The robust capability gradient is **operational**: only the frontier knows enough for
confidence-gating to reach *useful* accuracy. So "trust the agent's own confidence to abstain" is
weak-false and frontier-true *operationally*; an external verification / grounding gate matters most for
small/local agents and stays useful below the frontier even when raw discrimination looks fine.

### Risk–coverage (the operational view)

AUROC summarizes whether confidence *ranks* correctness; risk–coverage shows what that buys you — accuracy if
you answer only the most-confident fraction (i.e. gate/abstain on confidence):

| model | answer all | most-confident ½ | most-confident ¼ | answerable @ ≥90% acc |
|---|---|---|---|---|
| qwen2.5:7b (weak) | 28% | 28% | 28% | ~1% |
| qwen3-coder:30b (mid) | 15% | 15% | 15% | ~0% |
| glm-5.2 (frontier) | 80% | 93% | 100% | 63% |
| claude-sonnet-4-6 (frontier) | 52% | 79% | 92% | 44% |

Below the frontier, gating on confidence buys nothing (28%→28%); at the frontier it lifts accuracy sharply
and lets you answer ~half the questions at ≥90% accuracy. (Computed from the same result JSONs' raw rows.)

## Follow-up (v2): verbalized vs multi-sample confidence

Prompted by a sharp r/LLMDevs comment (multi-sample / Monte-Carlo temperature-sweep confidence is more
predictive, even on small models — arXiv:2502.18389), we measured both signals on the **same** task with
`multisample_confidence.py`: VERBALIZED = ask once for a confidence; SAMPLED = sample N=5 times at
temperature, use answer-agreement (fraction matching the modal answer) as the confidence.

| model | verbalized AUROC | **multi-sample AUROC** | task |
|---|---|---|---|
| qwen2.5:7b (weak) | 0.50 | **0.97** | arithmetic |
| qwen3-coder:30b (mid) | 0.53 | **0.98** | arithmetic |

On **arithmetic**, small models **do** carry a usable correctness signal in their **answer-consistency
across samples**, not in their verbalized self-report. **But this is task-dependent** — on the SimpleQA
factual benchmark below, multi-sample only reaches ~0.57–0.71, nowhere near 0.97. So multi-sample is **not a
universal small-model fix**: it recovers discrimination when the model can re-derive an answer (arithmetic)
but barely helps when it simply doesn't know the fact (recall). The finding is scoped to *verbalized
single-shot* confidence (the cheap signal an agent gate reads). (Result JSONs include raw rows.)

## Third task family: SimpleQA (a real hard benchmark, n=150)

Arithmetic and the curated factual set could both be artifacts of *computable* tasks. SimpleQA (OpenAI's
short-answer factual benchmark, deliberately hard) is the severe test: models err on most items, so there's a
genuine right/wrong mix and the numbers are robust (the small-model AUROC no longer rests on a handful of
correct cases). Measured at **n=150**, verbalized vs multi-sample, AUROC + risk-coverage:

| model | base acc | **verbalized AUROC** | multi-sample AUROC | verbalized: most-confident ¼ acc | answerable @ ≥90% |
|---|---|---|---|---|---|
| qwen2.5:7b (weak) | 5% | **0.47** (≈ chance) | 0.57 | 6% | 0% |
| qwen3-coder:30b (mid) | 8% | **0.74** | 0.63 | 21% | 0% |
| glm-5.2 (frontier) | 23% | **0.74** | 0.71 | **62%** | **5%** |

Two honest refinements this surfaced. (1) **Verbalized AUROC is not a clean weak→mid→frontier gradient** —
the 7B is at chance (0.47) but the 30B *matches* the frontier on raw discrimination (both 0.74). Discrimination
switches on above ~7B and is itself task-dependent (this same 30B scored only 0.54 on arithmetic). (2) **The
clean capability gradient is operational**: gating to the most-confident quarter lifts accuracy 5% → 21% →
**62%** across the tiers, and **only the frontier** can answer any fraction at ≥90% accuracy (5%). The mid
model *discriminates* (0.74) yet still can't gate to useful accuracy because it doesn't know enough —
**discrimination ≠ usable abstention.** That is the case for an external retrieval / grounding layer even on a
model whose confidence ranks correctly. Reproduce with `simpleqa_confidence.py` (see `result_simpleqa_*.json`).

## Run it

```bash
# local models via Ollama (http://localhost:11434):
python overconfidence_tax.py 80 "qwen2.5:7b" 1 out_weak.json          # n, model, level_base, outfile
python overconfidence_tax.py 80 "qwen3-coder:30b" 4 out_mid.json
# a Claude frontier anchor (set your key):
export ANTHROPIC_API_KEY=sk-ant-...
python overconfidence_tax.py 48 "claude-sonnet-4-6" 6 out_frontier.json

# SimpleQA (real hard benchmark) — point SIMPLEQA_CSV at a problem,answer CSV (OpenAI SimpleQA):
export SIMPLEQA_CSV=/path/to/simpleqa.csv
python simpleqa_confidence.py 150 "qwen2.5:7b" 5 result_simpleqa_weak.json    # n, model, N_samples, out
```

Each result JSON includes the raw per-item rows (expression, answer, gold, confidence, correct) so the
numbers are fully re-checkable. The included `result_*.json` files are the runs in the table above.

## Honest limits

- One task family (arithmetic), a handful of models — the gradient is directional, not a scaling law.
- Arithmetic may exaggerate confidence-maxing (models treat computation as deterministic). A second task
  family (factual / multi-hop) is the obvious next test.
- Prior art: that LLM calibration improves with scale is known; what this adds is the **abstention-AUROC
  capability gradient on a contamination-free task** and the grounding-gate implication.

MIT-licensed. Part of Agora / inspeximus (https://github.com/DanceNitra/inspeximus).
