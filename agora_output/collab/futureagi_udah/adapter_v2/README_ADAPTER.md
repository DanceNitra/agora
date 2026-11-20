# traceAI adapter for the V10 engine

`traceai_adapter.py` reads a traceAI trace export and scores each conversation turn once.
It does no scoring itself: it imports `trajectory_v3_ultra.py` unchanged and calls the
engine's own `iter_case_rows` on each session.

## Run it

```bash
python traceai_adapter.py examples/v2_06_circular_logic.json --out turn_scores.csv
python -m unittest test_traceai_adapter
```

## What it does

- Reads OTLP JSON, a JSON list of spans, or JSONL, with messages as JSON, as a JSON string, or as
  flattened `gen_ai.input.messages.N.message.content` keys.
- Groups spans by `session.id` (then `gen_ai.conversation.id`, then the trace id).
- Removes the history each request resends, so each turn is scored once.
- Skips a span only when its output repeats an output already scored. A reply with no new user
  message, such as an assistant answering twice in a row, is a new turn and is scored.
- Copies `gen_ai.usage.*` from the span; it does not estimate token counts.

## Reproducible example: V2-06

`examples/v2_06_circular_logic.json` is case 6 of `万象渊鉴·场域诊断测试集.txt` as a traceAI
trace. `examples/v2_06_control.json` is the same conversation with a sound second answer.

| trace | turn 1 H | turn 2 H |
|---|---|---|
| circular logic | 0.5759 | 0.1559 |
| control | 0.5759 | 0.4962 |

The adapter's scores equal the engine's scores on the same conversation given as text; a test
checks this.

## Definitions

V10, as implemented in `trajectory_v3_ultra.py`:

- U (Unity): for each of the turn's top key terms, the mean character 3-gram cosine similarity of
  the sentences that contain it (1.0 for a term that appears once); U is the mean over terms.
- D (Development): the spread of the key terms' first positions in the text, 2.5 times their
  standard deviation, capped at 1.0.
- A (Adversarial): 0.6 times the share of sentences with an adversarial marker, plus 0.4 times
  min(1, 0.3 times the number of matched contradiction phrase pairs).
- H (Harmony) = 0.4U + 0.4D - 0.2A.

Each turn is scored on its own text (the new user message and the reply). Diagnostics only.
