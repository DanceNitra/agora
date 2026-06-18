# Grounding Meter

A zero-dependency tool that measures **how much an LLM's answer is driven by external evidence vs its
own internal prior** — as a continuous *grounding curve*, not a single number.

## Why

A confidence score can't tell you whether a model is **ignoring a correct document** or **confidently
swallowing a wrong / poisoned one**. Both look like "a confident answer." The Grounding Meter measures
it directly: it varies the strength of an external context (a *k-of-N "sources report …"* ladder) and
reads how much the model's answer follows it.

```
follow(d) = 0.5 · [ p(answer = A | context pushes A) + (1 − p(A | context pushes B)) ]
```

- `follow = 0.5` → the model **ignores** the context and keeps its prior (deaf to evidence).
- `follow = 1.0` → the model **follows** whatever the context says (will swallow a poisoned doc).
- The **half-saturation dose `d50`** and the **area under `follow(d)`** are the per-model grounding scalars.

Option order (A/B) and push direction are both swept and cancelled by construction, so the number
isn't a position-bias artifact.

## Quick start

```bash
# Any OpenAI-compatible endpoint that returns token logprobs. Local Ollama:
ollama serve
python grounding_meter.py --endpoint http://localhost:11434/v1 --model qwen2.5:7b

# Hosted models:
python grounding_meter.py --endpoint https://api.openai.com/v1 --model gpt-4o-mini --api-key "$OPENAI_API_KEY"

# Endpoint without logprobs → K-sample fallback:
python grounding_meter.py --endpoint <url> --model <m> --no-logprobs --k 7
```

Output: a `grounding_curve.json` plus a console summary — the per-model follow curve, `d50`/`AUC`, the
two headline correlations, and the list of **confidently-wrong** items (high confidence, but the model
follows a false context).

## What the reference run found

On `qwen2.5:7b` across a 14-item prior-stratified bank (see `grounding-meter-v3-benchmark.json`):

- The follow curve is **continuous and ordered by prior strength** — fictional/weak items saturate at
  `d50 ≈ 0.08`; near-axiom facts (water boils at 100 °C, H₂O = water) resist even six sources (`follow`
  stays ~0.5).
- **`corr(grounding follow, accuracy-under-false-context) = −0.93`** — the meter strongly predicts when
  the model will be confidently wrong, while **`corr(confidence, accuracy) = 0.15–0.36`** — confidence
  barely does.
- A frontier model (GLM-5.2) under the same *k-of-N* framing **resists** plausible-but-wrong sources on
  facts it knows and only defers on truly unknown (fictional) items — a different grounding profile from
  the 7B, which the meter makes visible.

## Scope / honesty

This measures grounding *behavior* of (model × context-framing), not a fixed model trait. The continuous
signal is a **population** property of the curve; the per-item `Δ_ext/(Δ_ext+Δ_int)` ratio is reported
but collapses to a ceiling on models whose answers barely move under prompt reframing, so the published
measure is the **dose-response curve (`d50`/`AUC`)**. Re-derivable: figures come from the raw per-call
reads; seed-fixed.

Part of [Agora](https://github.com/DanceNitra/agora). License: MIT.
