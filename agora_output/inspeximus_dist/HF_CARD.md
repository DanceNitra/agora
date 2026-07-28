---
license: mit
library_name: inspeximus
tags:
  - llm
  - agent-memory
  - rag
  - mcp
  - memory-poisoning
  - agent-security
---

# inspeximus — a zero-dependency memory layer for AI agents

`pip install inspeximus` · [PyPI](https://pypi.org/project/inspeximus/) · [GitHub](https://github.com/DanceNitra/inspeximus) · MIT

inspeximus is the recall + consolidation core of an autonomous research system, distilled to a **single
dependency-free Python file** plus an MCP server so any Claude / Cursor / agent can use it as memory.
Its design rules are **measured, not assumed** (provenance + runnable probes in the repo).

- **Value-ranked recall** — top-k by relevance × accrued value, not cosine alone.
- **Per-type decay + capacity-aware consolidation** — the "dream" pass links near-duplicates and marks
  stale/superseded, never rewriting the raw note.
- **Lexical + semantic auto-mode** — BM25 + embeddings fused by Reciprocal Rank Fusion.
- **Contradiction flagging** — mutually-incompatible memories surface for review, never auto-deleted.
- **Corroboration-gated influence (0.4.0)** — `recall(influence_only=True)` restricts the memories
  allowed to *drive an action* to those that earned corroboration (a credited good outcome, or ≥2
  distinct-source links).

## Why 0.4.0 matters: poison-resistant recall

We red-teamed inspeximus with a real AgentPoison-style single-instance memory-poisoning attack (Chen et al.,
NeurIPS 2024; PoisonedRAG, Zou et al., USENIX Security 2025). Findings, all with runnable receipts:

- A **plain-English trigger sentence** in one poisoned memory hijacks raw top-1 retrieval **88–100%**,
  is **scale-invariant** (60→10 000 memories), and **evades a perplexity filter**.
- Retrieval-time / embedding-geometry defenses **do not generalize** across encoders.
- `recall(influence_only=True)` drops the single-instance poison's rank-1 hijack to **0%** on
  MiniLM / BGE / Contriever and every scale — because it lives in **provenance metadata, not embedding
  geometry**. Honest cost: a rare-but-true memory that hasn't earned corroboration is filtered too
  (recall 1.00 corroborated vs 0.08 uncorroborated), so this mode is for adversarial / untrusted
  ingestion. It **raises** attacker cost (≥3 coordinated records + ≥2 forged independent provenances),
  it does not make poisoning impossible.

```python
from inspeximus import Inspeximus
m = Inspeximus("memory.json")                      # or Inspeximus(..., embed=my_embedder)
m.remember("Pre-trend tests catch only ~31% of fatal DiD bias.", tags=["causal"], value=3)
m.recall("difference in differences", k=5)
m.recall("difference in differences", k=5, influence_only=True)   # only corroborated memory drives actions
```

Part of [Agora](https://github.com/DanceNitra/agora). MIT-licensed.
