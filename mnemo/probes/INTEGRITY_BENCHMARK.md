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
| mem0 2.0.11 (native) | 0.15 | no revert operation — the "go back" utterance mostly isn't even stored as a fact, so the corrected value is retained (A=3 incidental, B=14 kept, 3 unclear) |
| Graphiti (native, live) | 0.00 | no revert operation — keeps the corrected value; bitemporal invalidation fires on named contradictions, not on an unnamed "go back" (A=0, B=11, 9 unclear) |

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

## Cell 2 — echo resistance  (`integrity_bench_echo.py`)

Store a value, correct it, then **restate the retired value** (an echo — benign repetition or an injected
restatement). Does the current answer stay corrected, or does the stale value come back?

    add   "the {entity} is {A}."
    add   "correction: the {entity} is now {B}."
    echo  "the {entity} is {A}."             # restate the retired value
    ask   "what is the current {entity}?"    ->   B = echo resisted (good), A = resurrected (bad)

**Two honest metrics, and the naive one flatters us — so we don't use it.** Counting "did the system return the
corrected value" would show mnemo 1.00 / mem0 0.85 / Graphiti 0.45 and imply Graphiti fails echo. It does not.
Measured this way (n=20):

| system | resurrection rate (the attack, lower=better) | clean current-truth rate (answer clarity) |
|---|---|---|
| **mnemo** (echo_guard) | **0.00** | 1.00 |
| mem0 2.0.11 (native) | **0.00** | 0.85 |
| Graphiti (native, live) | **0.00** | 0.45 |

The real finding: **no modern system resurrected the stale value** — the echo-resurrection failure mode is
handled across the board (a correction from an earlier probe of ours over-stated it; corrected here). Where
they differ is *answer clarity*: mnemo and mem0 hand back a single current value; Graphiti, by bitemporal
design, surfaces both the invalidated old edge and the valid new one, so a naive reader (our judge, 11/20)
sees ambiguity — that is a different retrieval contract, **not** a resurrection. If your consumer resolves
validity itself, Graphiti's behaviour is correct; if it just reads the top facts, the ambiguity can bite.

This cell is the honest counterweight to the revert cell: on the attack that actually matters (resurrection),
mnemo does **not** win — everyone ties at 0.00. Publishing that is the whole point.

## Planned cells (harness shape is the same)

- **conflict-consolidation** — the MemoryAgentBench-style task where every system is weak (best ~54% single-hop);
  a shared harness to compare on the same fixture.

Every number traces to a probe in this folder. Nothing here is a claim about recall quality — we have not
benchmarked mnemo's retrieval against mem0/Zep and assume they lead on that axis until we show otherwise.
