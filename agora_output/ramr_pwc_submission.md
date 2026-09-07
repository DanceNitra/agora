# paperswithcode submission — RAMR (owner action, copy-paste ready)

**URL:** https://paperswithcode.com → "Submit" (needs your GitHub login; the repo must
have a README with a citation block — it does, plus CITATION.cff)

| field | value |
|---|---|
| **Title** | RAMR — Retrieval-Augmented Memory Reliability |
| **Abstract (short)** | A contamination-resistant synthetic benchmark for agentic-RAG and memory systems. Items are generated from random synthetic tokens, so closed-book accuracy is ~0 by construction — the benchmark isolates retrieval/memory mechanisms instead of parametric knowledge. Ships 12 metrics (CHAIN-FRAGILITY, OUTCOME-RANKED-RECALL, FORGET-PRECISION, ECHO-RESISTANCE, INTEGRITY-CONDITIONED RECALL, ...), a self-audit shortcut-floor tool (`memaudit.py`) with a permuted-label chance control, pre-registered falsifiers, bootstrap CIs, and a verification ledger (`verify_numbers.py`) that recomputes every cited number from its persisted source. |
| **Code link** | https://github.com/DanceNitra/ramr |
| **Paper (DOI)** | https://doi.org/10.5281/zenodo.20818291 (concept DOI, always latest) |
| **Task categories** | Retrieval-Augmented Generation · Evaluation · Memory (agentic) |
| **License** | MIT |
| **Datasets** | `ramr_chains_v0.1.0.jsonl` (300 synthetic 3-hop fact-chains, sha256-pinned manifest) + Hugging Face mirror: https://huggingface.co/datasets/Danchi17/ramr |

**Suggested PwC task tags:** `Question Answering (Multi-Hop)` · `Retrieval-Augmented Generation` ·
`Evaluation Benchmarks`

**Notes for the submitter:**
- PwC prefers linking the DOI landing page or an arXiv page; a Zenodo DOI works as "paper".
- If PwC asks for a results table, point it at `VERIFIED_NUMBERS.md` (the ledger recomputes every
  headline from stored arrays) — do NOT hand-enter numbers on PwC; keep the ledger as the source.
- After submission, add the PwC badge to the README top (next to DOI + MIT) — one line, keep
  the badge block sorted: DOI · License · PwC.
