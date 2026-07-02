# Reddit draft for r/Rag — influence-gate (GATED: owner posts manually)

## Sub check (r/Rag, 2026-07-02)
- 72,803 subs · submission_type = **self (text posts)** · restrict_posting: True (possible automod low-karma hold — same caveat as LocalLLaMA)
- Rules: on-topic (RAG/related) ✓ our topic is dead-center · 10/90 self-promotion (disclose affiliation, finding-first) · **Cite Your Sources** (plays to us — we cite heavily) · be respectful.
- Karma-13 caveats still apply: post finding-first (not product), affiliation disclosed, and **edit into your own voice before posting** (don't let it read as LLM-generated). If it 404s/vanishes for others after posting, it's likely in the modqueue — message a mod or wait.

## Pre-post verification (green): numbers match probe receipts; PyPI agora-mnemo 0.4.0 live; Zenodo DOI 10.5281/zenodo.21128550 resolves; HF + post URLs 200; AgentPoison attributed to Chen et al.; attack framed as reproduction; small-n disclosed.

---

## TITLE (recommended, ~83 chars — fits the feed)
We tried to poison our own RAG store — the retrieval-time defenses didn't generalize

## TITLE alternates
- One plain sentence poisons RAG retrieval 88–100% — the fix wasn't a better retriever
- Retrieval-time defenses against RAG poisoning didn't generalize across embedders
- RAG poisoning: gating what a chunk can *act on* beat every retrieval-time defense I tried

## BODY

I maintain a small open-source memory/retrieval layer for agents (mnemo). I wanted to see how badly one poisoned document could hijack retrieval, so I ran an AgentPoison-style attack against it across three embedders, then tried to defend it at the retrieval layer. The defense result is the interesting part, and it's all runnable.

The attack is easy and it generalizes:

- One poisoned chunk whose trigger is a **plain English sentence** ("the old lighthouse still guides ships along the rocky coast") lands at **rank 1** for **88–100%** of trigger-bearing queries on all three retrievers I tried (all-MiniLM-L6-v2, BGE-small-en-v1.5, Contriever).
- It doesn't wash out with scale — padding the corpus to **10,000** chunks keeps the hijack ~flat (~94%).
- A perplexity filter is the wrong wall: natural-sentence triggers have natural perplexity (47–441) and pass straight through while still hijacking (this is the PoisonedRAG point — poisoned text can look clean).

Retrieval-time detection didn't hold up:

- Embedding-outlier detection → defeated by padding the poison with generic text so it isn't an outlier.
- A retrieval-set-coherence re-ranker (down-weight a hit that's topically alien to the query's other results) → works on MiniLM (hijack 100% → 19%) but **fails outright on BGE**, whose space is more anisotropic (unrelated texts already sit at high cosine), so the poison isn't separable by coherence there. A defense that lives in embedding geometry inherits the encoder's geometry.

What worked was moving off the embedding entirely. The store only "graduates" a chunk to trusted once it's earned corroboration (a credited good outcome, or ≥2 independent-source links — earned automatically through use). Reusing that as an **influence gate** — retrieve everything for context, but only let *corroborated* chunks drive an action — dropped the single-instance hijack to **0% on all three retrievers and every scale**, benign utility ~90–100%. It generalizes because corroboration is metadata, not vectors, so it doesn't care which embedder you use.

Caveats up front (where I'd want the scrutiny):

- **The attack isn't novel** — it reproduces AgentPoison (Chen et al., NeurIPS 2024) and PoisonedRAG (Zou et al., USENIX Security 2025). The new bit is the defense-side measurement on a store that *has* a trust stage, and the split between what a poison can *retrieve* (88–100%) vs *influence* (0% gated).
- **Small-scale**: 16 held-out queries, one synthetic 60-item corpus (padded to 10k), three small single-vector encoders. Existence result, not a benchmark.
- **Retrieval-hijack, not end-to-end** — no full agent loop with a downstream action.
- **The gate has a real cost**: it filters rare-but-true chunks that haven't earned corroboration yet (recall ~1.0 → ~0.08), so it's for adversarial/untrusted ingestion, not a default for a trusted store. It raises attacker cost (needs ≥3 coordinated records with ≥2 forged independent sources), it doesn't eliminate the attack.

Probes are deterministic on a local embedder — if a single-instance poison beats the gate on your setup, or the cost is worse than I found, I'd like to know.

Sources / writeup (method + numbers + falsifier): <POST_URL>
Runnable probes: https://github.com/DanceNitra/agora/tree/main/mnemo/probes
Prior art: AgentPoison https://arxiv.org/abs/2407.12784 · PoisonedRAG https://arxiv.org/abs/2402.07867

---
POST_URL = https://dancenitra.github.io/agora/public/posts/agent-memory-poisoning-influence-gate.html
