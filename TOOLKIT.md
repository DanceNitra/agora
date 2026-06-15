# Agora Memory Toolkit

Three zero-dependency tools, distilled from an autonomous research OS that runs over ~5,800 notes.
Each is one file you can copy, or `pip install` together. Each ships with a runnable, measured demo —
because the rule here is *measured, not assumed*.

| tool | one line | run the proof |
|---|---|---|
| **[mnemo](mnemo/)** | agent memory + a **self-maintaining** second brain (recall by value, consolidate, find dead-links/orphans/stale, suggest+apply links, health gauge) | `python mnemo/maintain.py` |
| **[ragfresh](ragfresh/)** | a **freshness/decay layer** for RAG/vector stores — keep/down-weight/refresh/prune by value×freshness, not recency | `python ragfresh/ragfresh.py` |
| **[nullcheck](nullcheck/)** | **is this number real, or just noise?** — null-simulation A/B + permutation test + peeking-inflation | `python nullcheck/nullcheck.py` |

They share one idea: **keep / trust what survives contact with a null or with reality.** mnemo keeps
the memory that proves valuable; ragfresh keeps the chunk that's still fresh and worth its cost;
nullcheck keeps only the effect a no-effect null can't reproduce.

## Install
```bash
pip install .                 # the three cores (dependency-free)
pip install ".[mcp]"          # + the MCP servers (mnemo-mcp, second-brain-mcp, ragfresh-mcp)
pip install ".[pgvector]"     # + ragfresh Postgres/pgvector adapter
```
```python
import mnemo, ragfresh, nullcheck
m = mnemo.Mnemo("agent_memory.json")           # remember / recall / consolidate
plan = ragfresh.triage(items, now=...)         # keep/downweight/refresh/prune
verdict = nullcheck.ab_test(100, 1000, 115, 1000)   # real or noise?
```

## MCP (use them from Claude / Cursor / any agent)
```bash
mnemo-mcp            # agent long-term memory
second-brain-mcp     # think over + MAINTAIN a notes folder  (NOTES_DIR=...)
ragfresh-mcp         # decide what to keep/prune in a vector store
```

## Try everything at once
```bash
python examples/toolkit_demo.py
```

Open-core: the cores stay free.
