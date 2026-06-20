---
license: cc-by-4.0
language:
  - en
pretty_name: The Folklore Index
size_categories:
  - n<1K
tags:
  - ai
  - llm
  - evaluation
  - replication
  - reproducibility
  - benchmark
  - rag
  - agents
  - folklore
  - verification
configs:
  - config_name: default
    data_files: folklore_index.jsonl
---

# The Folklore Index

A standing, machine-readable benchmark of widely-repeated AI / data-science claims, each rebuilt as the smallest runnable test and ruled REPRODUCED / FAILED / NOT_COMPUTABLE. Honest, citable receipts for the field's folklore.

**v0.1.0** - 58 claims
(32 REPRODUCED / 11 FAILED / 15 NOT_COMPUTABLE).
Each row has a permanent `key` (FI-NNNN) for stable citation. Load: `datasets.load_dataset("<user>/folklore-index")`.
Fields: key, domain, claim, source, verdict, note, lab_file, code_url, code_resolves, date. Source repo: https://github.com/DanceNitra/agora. Data CC-BY-4.0, code MIT.
