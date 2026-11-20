# U/D/A/H adapter for traceAI (proof of concept)

This folder reads a traceAI trace export and scores each conversation turn with
the U/D/A/H metrics from Li Guanghao's *Mirror Abyss*, chapter 13. The output is
diagnostics only: numbers and booleans, never advice or generated text.

Authors: Li Guanghao (metric definitions, test dialogues) and Rastislav Drahoš
(adapter code). AI use: the code, tests and translations were written with
Claude Code (Claude Opus 5.5) and reviewed by the authors.

## Files

| file | what it holds |
|---|---|
| `udah_adapter.py` | Parser, turn deduplication, U/D/A/H, flip points, and the optional self-contradiction module. Python 3.9 or later, standard library only. |
| `test_udah_adapter.py` | 34 unit tests. |
| `make_refund_trace.py`, `synthetic_refund_trace.json` | The 3-turn refund dialogue as traceAI spans. |
| `benchmark_20.py` | The 20 test dialogues, translated from Chinese, with the original labels and our second reading of four of them. |
| `run_benchmark.py` | Scores the 20 dialogues with U/D/A/H, the self-contradiction module, and, with `--judge`, the `conversation_coherence` and `conversation_resolution` rubrics as an LLM judge. |
| `benchmark_results.json` | The results of one run, judge `claude-opus-5-5`, 3 repeats per rubric and dialogue. |

## Run it

```bash
python -m unittest test_udah_adapter
python udah_adapter.py synthetic_refund_trace.json
python udah_adapter.py synthetic_refund_trace.json --self-contradiction
python run_benchmark.py              # deterministic part only, no model calls
python run_benchmark.py --judge      # also the two rubrics; needs ANTHROPIC_API_KEY
```

`run_benchmark.py --judge` reads the rubric files from
`futureagi/model_hub/system_evals/agent/` in this repository, or from the folder
in `RUBRIC_DIR`. It caches each judge call in `benchmark_judge_cache.json`.

## What it does

- Input: OTLP JSON, a JSON list of spans, or JSONL. Messages are read from
  `gen_ai.input.messages` and `gen_ai.output.messages`, as JSON, as a JSON string,
  or as flattened `gen_ai.input.messages.N.message.content` keys.
- Spans are grouped by `session.id` (then `gen_ai.conversation.id`, then the trace
  id). Each request's repeated history is removed, so each turn is scored once.
- U/D/A/H run over 256-character windows with step 128. A turn reports the mean of
  its windows and is a flip point if any window meets dU > 0.15, dD < -0.10 and
  dH < -0.08. Weights, windows and thresholds are in `UDAHConfig`.
- The self-contradiction module is off by default (`--self-contradiction`). It
  compares the assistant's numeric limits next to policy words, and whether a
  policy subject is offered or refused, with its most recent earlier statement.

## Limits

- The word lists are English. Chinese text needs translation first.
- The self-contradiction module is a small rule set. On the 10 dialogues without
  a planted contradiction it raised no alarm. Of the 10 with one, it flagged case 1
  (30 days to 14 days) and case 3, and it does not detect role, promise, feature or
  fee changes.
- The judge numbers use the repository's rubric text with `claude-opus-5-5`, not
  the platform's own judge setup.
