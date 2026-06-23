---
license: mit
language:
  - en
tags:
  - benchmark
  - agent-memory
  - retrieval-augmented-generation
  - llm
  - evaluation
  - memory
pretty_name: "RAMR — Retrieval-Augmented Memory Reliability"
size_categories:
  - n<1K
---

# RAMR — Retrieval-Augmented Memory Reliability

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20818291.svg)](https://doi.org/10.5281/zenodo.20818291)

A **contamination-resistant synthetic benchmark** for agentic-RAG / memory systems. This dataset is the frozen
fact-chain set used by the benchmark; the full harness, metrics, baselines and verification ledger live in the
code repository.

- **Code + metrics + runners:** https://github.com/DanceNitra/ramr
- **Citable archive (concept DOI, always latest):** https://doi.org/10.5281/zenodo.20818291

## What this is — and is not

A *findings + method* release, **not** a definitive large-scale leaderboard. Items are generated from **random
synthetic tokens**, so a model cannot have memorized the answers — closed-book accuracy is ~0 by construction
(contamination-resistant). The trade-off: it isolates retrieval/memory **mechanisms**, it does not predict
real-corpus accuracy. Treat small-n magnitudes as directional; the orderings are the signal.

## The dataset

`ramr_chains_v0.1.0.jsonl` — 300 synthetic 3-hop fact-chains (sha256-pinned in `manifest.json`). Each row:

| field | meaning |
|---|---|
| `id` | chain id |
| `question` | the 3-hop question (currency of the country where the company a person works at is HQ'd) |
| `gold_facts` | the complete chain (CONVERSION uses all) |
| `answer` | the gold answer token |
| `drop_index` | which hop to drop for the PARTIAL condition (CHAIN-FRAGILITY) |
| `distractor_pool` | fixed irrelevant facts; take first *k* for DISTRACTION |

## The six metrics (measured in the code repo)

CONVERSION (does complete retrieval convert to a correct answer), **CHAIN-FRAGILITY** (cost of one missing hop —
near-total collapse across 7 models / 6 families), DISTRACTION (cost of noisy context — model-specific),
FACT-RETENTION (compaction lossy under a fixed budget), OUTCOME-RANKED-RECALL (was-it-right vs was-it-recalled),
and FORGET-PRECISION (after a fact is updated, does recall return the current value or the stale one).

## Cite

Agora (2026). *RAMR — Retrieval-Augmented Memory Reliability*. https://doi.org/10.5281/zenodo.20818291

MIT-licensed.
