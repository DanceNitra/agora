# Agent-Memory Integrity Benchmark

An open, cross-system harness for a property that recall benchmarks skip.

LoCoMo, LongMemEval, and MemoryAgentBench measure **retrieval** — did the store surface the right fact.
This measures **integrity** — when a fact is *corrected*, does the store behave:

- **Value-obscuring revert** — the user says *"go back to what we had"* (naming no value). Can the store undo
  the correction on that unmarked command?
- **Echo resurrection** — the user *restates the old, retired value* after the correction. Does the store
  let the stale value come back?

Both are read through **one shared, ground-truth-blind judge** on each system's own recall surface, so no
system is scored on a home-field instrument. It is a narrow, adversarial, command-driven cut — not a general
"which memory library is best". Run it yourself, or add your system.

## Results (canonical judge: gpt-4o-mini, n=20, native configs)

| system | value-obscuring revert | 95% CI | echo resurrection (lower = better) |
|---|---|---|---|
| **mnemo** (local) | **0.75** | [0.53, 0.89] | 0.00 (defends) |
| mem0 2.0.11 (gpt-4o-mini + text-embedding-3-small) | 0.20 | [0.08, 0.42] | ~0.00 (defends) |
| Graphiti (live neo4j, native pipeline) | 0.00 | [0.00, 0.16] | 0.00 (defends) |

Reading:
- **Revert is a capability gap, not a tuning gap.** mem0 and Graphiti have *no revert operation* — they
  correctly retain the corrected value but cannot undo it on an unnamed command. Only mnemo exposes a channel
  for it. mnemo's and mem0's CIs do not overlap at n=20, so the gap is real; and because the competitors
  structurally lack the operation, the gap does not depend on the judge.
- **Echo is a tie — we lead with the cell we do not win.** All three defend against a restated stale value.
- **The judge model shifts absolute numbers.** A weaker free judge marks more cases "unclear", lowering
  mnemo's *absolute* rate (≈0.4 under a local model vs 0.75 under gpt-4o-mini) while leaving mem0/Graphiti near
  zero (they have no revert to honor). The canonical table above uses gpt-4o-mini; your run may differ — report
  your judge.

Full methodology, the fairness fix that dropped mnemo's headline from a flattering 1.00 to 0.75, and the
per-system reading: [`METHODOLOGY.md`](METHODOLOGY.md). Write-up: *"We fixed our own memory benchmark until it
stopped flattering us"* (dancenitra.github.io/agora).

## Run it

```bash
pip install agora-mnemo          # the reference system + a zero-dependency store
python run.py                    # mnemo, both cells, using a LOCAL Ollama judge (free, no API key)
python run.py --systems mnemo --cell revert --n 20
```

The judge is any OpenAI-compatible chat endpoint, set by env vars (defaults to a local Ollama so it runs free):

```bash
JUDGE_BASE_URL   default http://localhost:11434/v1     # OpenAI: https://api.openai.com/v1
JUDGE_MODEL      default qwen2.5                         # OpenAI: gpt-4o-mini (the canonical judge)
JUDGE_API_KEY    default ""                              # required only for hosted judges
```

## Add your system

Writing an adapter is ~15 lines. See `MnemoAdapter` in [`run.py`](run.py) and [`SUBMISSION.md`](SUBMISSION.md).
Implement four methods — `reset` / `add` / `command` / `context` — register it in `ADAPTERS`, run both cells,
and open a PR with your `results/latest.json` and the judge you used. FAILED cells are welcome: a store that
cannot revert is a true, useful result, not a mark against you.

## Why this exists

Memory vendors are benchmarked almost entirely on recall, which is cheap and flattering. Whether a *correction*
actually takes — and stays taken — is the property that decides if an agent acts on current truth or a stale
value a later message already retired. It is under-measured, so we made it runnable and open. The reference
system (mnemo) is ours; the point is the instrument, not the leaderboard. Prior art the integrity axis builds
on: AGM belief revision (1985), truth-maintenance systems (Doyle 1979), bitemporal databases.

MIT. Part of [Agora](https://github.com/DanceNitra/agora).
