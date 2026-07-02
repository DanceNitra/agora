# Reddit draft — mnemo influence-gate (GATED: owner posts manually, never auto-post)

## Pre-post verification (done 2026-07-02, all green)
- Numbers match the receipts: influence-hijack 0% on MiniLM/BGE/Contriever; raw hijack 0.938/1.0/0.875; scale sweep raw 0.94/0.88/0.94/0.94 @ 60/500/2k/10k, influence 0% throughout; rare-cost 1.00 vs 0.083; attacker ladder (1 free = filtered / 3 records + 2 forged sources = passes); perplexity gibberish 30908 caught vs fluent 46.6 evades.
- PyPI agora-mnemo **0.4.0** LIVE · Zenodo DOI 10.5281/zenodo.21128550 resolves (302) · HF 200 · post URL 200 · probe URL 200.
- Author attribution corrected (AgentPoison = Chen et al., NeurIPS 2024). Attack framed as reproduction, not novel. Retrieval-only (not end-to-end) stated. Small-n stated.

## Recommended subreddit
**Primary: r/LocalLLaMA** (self-hosting / agent crowd, tolerant of an honest project post with runnable code).
Alt: **r/RAG** (on-topic, smaller). Avoid r/MachineLearning unless flaired **[P]** and even then it's strict on self-promo.
Posting notes: post the FINDING as text (link secondary, in a comment or at the end), reply to questions in your own voice, don't lead with the pip install. Check the account isn't brand-new/low-karma (spam filter). One sub first; cross-post only if it lands.

---

## TITLE
We tried to poison our own agent-memory library. The retrieval-time defenses didn't generalize — gating what memory is allowed to *act* did.

## BODY

I maintain a small open-source agent-memory layer (mnemo). I wanted to know how badly a single poisoned memory could hijack it, so I ran an AgentPoison-style attack against it across three embedders and then tried to defend it. Sharing because the *defense* result surprised me, and the whole thing is runnable if you want to check it.

First, the uncomfortable part: the attack is easy and it generalizes.

- One poisoned memory, with a trigger that's just a **plain English sentence** ("the old lighthouse still guides ships along the rocky coast"), lands at rank 1 for **88–100%** of trigger-bearing queries on all three retrievers (MiniLM, BGE-small, Contriever).
- It doesn't decay with scale — padding the store to **10,000** memories leaves the hijack basically flat (~94%).
- A perplexity/gibberish filter doesn't help: natural-sentence triggers have natural perplexity (47–441) and sail through, while still hijacking. (Gradient "gibberish" triggers get caught, but you don't need them.)

Then the retrieval-time defenses I tried didn't hold up:

- Embedding-outlier detection → defeated by padding the poison with generic text.
- A retrieval-set-coherence re-ranker → works on MiniLM (100% → 19%) but **fails outright on BGE**, because BGE's space is more anisotropic and the poison isn't separable there. A defense that lives in embedding geometry inherits the encoder's geometry.

What actually worked was moving the defense off the embedding entirely. mnemo already only "graduates" a memory to trusted once it's earned corroboration (a credited good outcome, or ≥2 independent-source links — earned automatically through use). I reused that as an **influence gate**: retrieve everything for context, but only let *corroborated* memory drive an action. A freshly injected poison has earned nothing, so it's filtered at the retrieve→act step. That dropped the single-instance hijack to **0% on all three retrievers and every scale**, with benign utility ~90–100%. It generalizes precisely because corroboration is metadata, not vectors.

Honest caveats, up front (this is where I'd want scrutiny):

- **The attack isn't novel** — it reproduces AgentPoison (Chen et al., NeurIPS 2024) and PoisonedRAG (Zou et al., USENIX Security 2025). The only new part is the defense-side measurement on a memory layer that *has* a trust stage, and the split between what a poison can *retrieve* vs *influence*.
- **It's small-scale**: 16 held-out queries, one synthetic 60-item corpus (padded to 10k), three small single-vector encoders. It's an existence result, not a benchmark.
- **It's retrieval-hijack, not end-to-end** — I didn't run a full agent loop with a downstream action.
- **The gate has a real cost**: it also filters rare-but-true memories that haven't earned corroboration yet (their recall drops from ~1.0 to ~0.08), so it's for adversarial/untrusted ingestion, not a default for a trusted single-user store. And it *raises* attacker cost rather than eliminating the attack — defeating it needs ≥3 coordinated records with ≥2 forged independent sources.

The probes are deterministic and run on a local embedder — if a single-instance poison beats the gate on your setup, or the utility cost is worse than I found, I'd genuinely like to know.

Writeup (numbers + method + falsifier): <POST_URL>
Runnable probes: https://github.com/DanceNitra/agora/tree/main/mnemo/probes
(It's shipped as `recall(influence_only=True)` in mnemo 0.4.0 if it's useful to anyone.)

---
POST_URL = https://dancenitra.github.io/agora/public/posts/agent-memory-poisoning-influence-gate.html
