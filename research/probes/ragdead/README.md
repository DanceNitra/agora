# Does long context kill RAG? — a judge-free needle-vs-aggregation probe

Receipts behind the Crucible entry
[*Does long context kill RAG?*](https://dancenitra.github.io/agora/public/posts/does-long-context-kill-rag.html).
On the *same* synthetic structured log at four growing lengths (~5k → ~110k tokens), two task families:
**NEEDLE** (single-record lookup) vs **SYNTH** (read-everything aggregation). Exact gold, **no LLM judge**.

## Result (`ragdead_result.json`)

| context | tokens | NEEDLE (lookup) | SYNTH (aggregation) |
|---|---|---|---|
| ~5k | 4877 | **1.00** | 0.75 |
| ~25k | 25050 | **1.00** | 0.375 |
| ~60k | 61874 | **1.00** | 0.25 |
| ~110k | ~110k | **1.00** | 0.375 |

**Needle stays perfect at every length; aggregation collapses to ~0.25–0.38 by 25k and stays there** (no
length-driven recovery — 110k is no better than 60k). `audit_ragdead.py` re-derives the gold *independently* from
each haystack and recomputes accuracy: **0 gold-vs-published mismatches**, needle 1.00, synth 0.25/0.375. The
per-question structure (3 counts C, 3 max M, 2 filters F) shows the mechanism: the **max** questions survive at
110k (one pass), while **count/filter** collapse (exhaustive tally).

## Honest reading (verdict FAILED, for CAG on synthesis)

- **It's the task, not the length.** Long context handles find-the-fact fine; it does *not* replace retrieval for
  combine-the-facts. This **replicates a known effect** — lost-in-the-middle (Liu et al. 2023 / TACL 2024), RULER
  (Hsieh et al./NVIDIA 2024), NoLiMa (Modarressi et al. 2025, arXiv:2502.05167), and Chroma's "context rot" (2025,
  an industry report, not peer-reviewed). The position being tested is **CAG** (Chan et al. 2024,
  arXiv:2412.15605), which itself scopes replacement to small constrained KBs — the *viral* version drops that.
- **Underpowered on its own.** Only **n=8 synthesis questions per length**; the 0.75→~0.3 drop is Fisher's-exact
  ≈ 0.13 (not significant) — it is credible mainly because it reproduces the heavily-replicated literature, not
  because n=8 licenses it. The contribution is the neutral, runnable, judge-free **adjudication**, not the effect.
- **Partly length-independent.** Even at 5k, SYNTH is 0.75 (not 1.00): exhaustive count/filter is arithmetic the
  model can't do reliably at *any* length — long context makes it worse, it doesn't cause it. The real fix for
  count/filter aggregation is a **tool** (a code interpreter / query), not long context or retrieval.
- **Reproducibility gaps:** the exact reader model + date for this run were **not logged**; one model, synthetic
  haystacks, lengths ≤ ~110k. Regenerate and run your own.

## Run it

```bash
# generates haystacks/questions/gold into $RAGDEAD_OUT (defaults to ./ragdead_out); wire your own reader model:
python exp_ragdead_A.py       # generate the length-swept structured logs + gold
# ...feed each haystack to your long-context reader, save answers alongside...
python audit_ragdead.py       # independent gold re-derivation + judge-free scoring
```

`ragdead_result.json` and `gold.json` are the original run's receipts (the full ~467 KB haystacks regenerate from
the generator, so they are not shipped). `audit_ragdead.py` is the credibility core: it re-parses each haystack
and re-derives the needle+synth gold from scratch, so the published accuracies are checkable against a second,
independent implementation.

MIT-licensed. Part of Agora / inspeximus (https://github.com/DanceNitra/agora/tree/main/inspeximus).
