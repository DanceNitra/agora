# Agent-memory integrity benchmark (open, cross-system, run-it-yourself)

Recall benchmarks (LoCoMo, LongMemEval, MemoryAgentBench) ask *did the store retrieve the right fact*. This
one asks a different question the recall evals skip: **integrity** — which version of a fact wins, whether a
corrected value can be undone on command, whether a restatement resurrects a retired value. It runs the same
adversarial fixture through several memory systems in their **native config** and publishes the matrix
whichever way it falls. If a number here is wrong, the harness is right next to it — run it, or add your system.

This exists because a sharp r/RAG reviewer made the fair point that self-scoring on home fixtures is
unfalsifiable. So: native configs, a shared judge that never sees ground truth, and results published even
where mnemo does **not** win.

## Methodology (the same for every system)

- **Native config, no tuning in our favor.** mem0 runs on its recommended stack (gpt-4o-mini +
  text-embedding-3-small); Graphiti runs against a live neo4j with its own LLM pipeline; mnemo runs local.
- **Shared judge.** One OpenAI model reads each system's **full memory state** (`get_all` / all valid facts,
  not just top-k search) and extracts the current value. It never sees the ground truth beyond the two
  candidate tokens, so it can also answer "unclear". Feeding the full state isolates the *integrity* question
  (did the operation change the state) from *retrieval quality* (a different axis we do not test here).
- **Honest reading.** A store that keeps the corrected value when told "go back" is **not wrong** — it simply
  lacks that operation. We report a **capability** difference, never "system X is bad".
- Small n (OpenAI cost). Directional, not a leaderboard. Re-run with a larger `--n` if you want tighter CIs.

## Cell 1 — value-obscuring revert  (`integrity_bench_revert.py`)

Store a value, correct it, then issue an **unmarked** revert that names no value ("go back to what we had",
"roll back the change", "undo it"). Does the current answer return to the OLD value?

    add   "the {entity} is {A}."
    add   "correction: the {entity} is now {B}."
    revert "{unmarked revert, no value}"
    ask   "what is the current {entity}?"   ->   A = revert honored, B = revert ignored

| system | revert success (n=20) | what happens |
|---|---|---|
| **mnemo** (route/revert) | **1.00** | the intent router tags the utterance as a revert and restores the predecessor from the version ledger; no LLM in the path |
| mem0 2.0.11 (native) | 0.15 | no revert operation — the "go back" utterance mostly isn't even stored as a fact, so the corrected value is retained (3/20 incidental, 14 kept, 3 unclear) |
| Graphiti (native, live) | pending full run | one-case smoke: keeps the corrected value; bitemporal invalidation fires on named contradictions, not on an unnamed "go back" |

Reading: value-obscuring revert (undoing a correction from a natural-language command that names no value) is a
capability only mnemo exposes here. mem0 and Graphiti correctly retain the corrected value; they just have no
channel to undo it on command. This is the operation the storm's own converged finding says cannot be done from
text alone without an explicit revert channel.

The benchmark also improved mnemo: it surfaced that `route()` missed "roll back" (mnemo was 0.80) — fixed in
0.7.11.

## Run it / add your system

    # free, local only:
    python mnemo/probes/integrity_bench_revert.py --systems mnemo

    # includes paid backends (needs OPENAI_API_KEY in server/.env; Graphiti needs a neo4j at bolt://localhost:7687):
    python mnemo/probes/integrity_bench_revert.py --systems mnemo,mem0,graphiti --n 20

Adding a system = one adapter function with the interface `(reset, add(text), revert(text), full memory state
for the judge)`. PRs welcome; we publish whatever it shows.

## Planned cells (harness shape is the same)

- **echo-resistance** — correct a fact, restate the old value, does it resurrect? Honest expected shape: mnemo
  defends (echo_guard), Graphiti also defends (~0% in its real pipeline — a prior strawman of ours was
  corrected by our own audit), mem0 ~0.53 (earlier RAMR run). We do **not** sweep this one, which is the point.
- **conflict-consolidation** — the MemoryAgentBench-style task where every system is weak (best ~54% single-hop);
  a shared harness to compare on the same fixture.

Every number traces to a probe in this folder. Nothing here is a claim about recall quality — we have not
benchmarked mnemo's retrieval against mem0/Zep and assume they lead on that axis until we show otherwise.
