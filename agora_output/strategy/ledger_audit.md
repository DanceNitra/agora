# Ledger Audit — re-verify every FAILED claim holds on serious models at adequate n

**Why:** owner steer 2026-06-20 — "we can't claim on 6 FAILED docs that might not even be true." Before any
"go loud," every FAILED verdict must be confirmed robust (not a small-n / weak-model / buggy artifact). We
have a history of artifacts (+144%, the Collective-Intelligence-Law). One re-verification per loop cycle,
paced to NOT starve the dungeon (don't run deepseek-heavy audits while the dungeon needs full pace).

**Standard for "robust":** adequate n (>=~40 where applicable) + serious model (glm-5.2 / deepseek, never
qwen-7b) + a CI or clear computational proof + a stated falsifier. Outcome per entry: CONFIRMED (verdict
holds) | DOWNGRADE (verdict not supported -> honestly revise) | EMBED (computational, already solid).

## AI-Claims ledger (agora_output/aiclaims/aiclaims.json)
- [x] **Multi-agent outperforms single** — CONFIRMED FAILED (n=48 MuSiQue, both models, CIs exclude 0). 2026-06-20.
- [x] **Trust confidence to detect poisoned RAG** — CONFIRMED FAILED (n=101, Wilson <=3.7%, both models). 2026-06-20.
- [ ] **Best-of-many selection inflates FDR / BH barely helps** — check sim robustness (links to selection-aware FDR lab 3a90ab). PRIORITY: med.
- [ ] **RAG frontier models weigh retrieved doc over priors** — re-verify n + model. PRIORITY: med.
- [ ] **'AI time horizon' is a robust headline number** — re-verify. PRIORITY: low.
- [ ] **LLMs inherit human cognitive biases (conservatism)** — re-verify on serious model + n. PRIORITY: med.
- [ ] **Smaller chunks improve RAG retrieval** — re-verify n + retrieval setup. PRIORITY: med.
- [ ] **Reranker on top of first-stage retrieval helps** — re-verify. PRIORITY: med.

## Crucible ledger (public/crucible/crucible.json)
- [x] **Emergent abilities are genuine sharp transitions** — CONFIRMED FAILED (audited 2026-06-20). Original reproduces (6.7x sharper from the exact-match metric alone, onset drifts -0.07->+5.58 with no skill change); parameter sweep: metric-induced sharpening holds in 9/9 combos (always >1x, >2x in the majority), magnitude scales with answer length + skill smoothness -> robust, not cherry-picked. Verdict unchanged, nothing to republish. (lab 20260619-185500)
- [ ] **Real-world networks are scale-free** — note says n=20,000 CSN fit; likely solid, confirm. PRIORITY: low.
- [ ] **Metcalfe's Law n^2** — computational; confirm model. PRIORITY: low.
- [ ] **Diversity trumps ability (Hong-Page)** — computational; confirm. PRIORITY: low.
- [ ] **Dunning-Kruger is an artifact** — confirm the autocorrelation/noise model. PRIORITY: med.
- [ ] **Hot-hand fallacy (Gilovich) reversed (Miller-Sanjurjo)** — computational; confirm. PRIORITY: low.

**Next target:** the remaining COMPUTATIONAL FAILED entries (Dunning-Kruger artifact, best-of-many FDR,
Metcalfe, scale-free, hot-hand, diversity) — no LLM, so zero dungeon contention; audit these first. DEFER
the LLM-needing RAG ones (chunk-size, reranker, doc-weighing) to paced slots when the dungeon is idle, so
they don't starve the agents' model.

**Audit log:** 2026-06-20 emergent-abilities -> CONFIRMED FAILED (robust under param sweep).
