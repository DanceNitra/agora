# Agent-Memory Integrity Index — cadence & edition template (internal)

Turns the one-off hub (public/integrity/) into a compounding SERIES. Each edition is fill-in-the-blank so it
costs ~10 minutes, not a flagship post. This is the Phase-3 mechanism from the 2026-07-12 "up" plan.

## When an edition triggers (event-driven, NOT a forced calendar)

Publish a new edition when ONE of these is true — never publish filler:
1. A tracked system (mnemo, mem0, Graphiti, or any added) ships a version that MOVES a benchmark cell.
2. A new system is added (by us or via an external PR to github.com/DanceNitra/agent-memory-integrity).
3. A new cell is added (a new integrity property is measured — e.g. laundered-lineage recovery, staleness).
4. An external submission arrives (the highest-value trigger — someone else populated the leaderboard).

If none of these is true, there is no edition. A living index earns trust by only moving when the data moves.

## What an edition IS (small, not a post)

- One dated line in the hub's "Editions" section: what changed + the delta (old cell number -> new).
- If numbers changed: update the benchmark table in public/integrity/ AND the canonical results in the
  benchmark repo (results/canonical.json) so the page and the source agree.
- Only write a full storefront post / Reddit note if the change is genuinely news (a FAILED cell, a new
  system with a surprising result). Most editions are just the one line.

## Fill-in template (copy into the hub's Editions section, newest first)

```
<p class="note"><b>Edition N · YYYY-MM-DD</b> — {one sentence: what changed}. {system} {cell}
{old} -> {new} (95% CI [lo, hi]). {one clause on why, honest}. {link to the run if external}.</p>
```

## Hard rules (same gate as everything)

- Every number re-run this cycle before it goes on the page (validate).
- Cite the source (which probe / which submission) so it stays re-runnable.
- Lead with the honest cell — if we lose or tie a cell, that edition says so first.
- Competitor numbers: never on the page unless their SDK ran 0-error, or they self-submitted (then they own it).
- OpenAI is dead: WE only grow mnemo cells for free (local/Ollama judge); competitors self-submit their own.

## Current state (Edition 1, 2026-07-12)

- Systems: mnemo 0.7.19, mem0 2.0.11, Graphiti. Cells: value-obscuring revert, echo resurrection.
- Numbers (gpt-4o-mini judge, n=20): revert mnemo 0.75 [0.53,0.89] / mem0 0.20 / Graphiti 0.00; echo = tie.
- Source: benchmark repo canonical.json; harness mnemo/probes/integrity_bench_{revert,echo}.py.
- Hub: https://dancenitra.github.io/agora/public/integrity/
