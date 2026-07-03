# B-001 (Preference Application) as a memory-substrate instrument — CLAIM MEMO (pre-audit)

**For:** gated GitHub comment on deepseek-ai/DeepSeek-V3#1462 (+ offer to plug into #1466).
**Status:** measured, pre-stress-claim / pre-verify-claims. Nothing posted.
**Probe:** `mnemo/probes/bseries_b001_preference_recall.py` (real nomic-embed-text; MIT; runnable).
**Raw result:** `mnemo/probes/bseries_b001_result.txt`.

## The core claim (one sentence)
B-001 preference-application failure is a **retrieval-objective mismatch, not a storage loss**: a user
preference is causally load-bearing for the *answer's style* but topically *orthogonal* to a new
session's *query content*, so a similarity ranker structurally buries it beneath on-topic episodic
memory — which is why the substrate fix is a **separate type/profile channel injected unconditionally**,
not similarity retrieval.

## What we measured (substrate only — not the agent's generated answer)
Store: 3 preferences (session 1: concise answers; dislikes numbered lists; direct question over summary)
+ 20 topically-varied episodic memories (sessions 2–4). 6 new-session queries on unrelated engineering
topics, no mention of preferences. Retrieval = mnemo hybrid (lexical + semantic RRF over real
nomic-embed-text) — a strong baseline, not a rigged weak one.

| substrate | pref_recall | note |
|---|---|---|
| similarity_only (hybrid RRF) | mean @5 = **0.333**; per-query [0.0, 1.0, 0.0, 0.33, 0.0, 0.67] | **3/6 queries surface 0 of 3 preferences**; raising k 5→20 doesn't help (recall returns only nonzero-relevance items, so an orthogonal preference is filtered out, not merely ranked low) |
| recency_window (W=3/5/10) | **0.000** | preferences are the oldest memories → aged out |
| typed_profile (retrieve by type) | **1.000** | query-independent; all 3 every query; fixed inject budget |

**Structural reason:** mean cosine(query, preference) = **0.401** vs mean cosine(query, best on-topic
memory) = **0.789** (gap 0.39). With nomic's high anisotropic baseline, 0.40 is a *low* score — a
topical match outranks the preference whenever one exists. Precision cost: to reach the first
preference, similarity must go to ~rank 3, dragging in ~2 non-preference memories first.

## The honest framing (NOT a discovery claim)
This is what production profile memory already does — always-in-context "core memory" (MemGPT/Letta) vs
similarity-searched archival memory; mem0's user/profile track. **We did not invent profile injection.**
The contribution is the *measured substrate instrument* for the B-series: it quantifies the cost of the
naive "one vector store, recall on the query" path and localizes B-001 failure to the retrieval
objective, complementary to the cognitive-trace instruments in the thread (Cophy causal_density / TAT
divergence / HeartFlow field), which read the reasoning, not the store.

## Caveats (state plainly)
- Substrate only: recall is the *necessary precondition* for preference application, not proof the model
  then applied the preference.
- Single fixture set, one embedder (nomic), 6 queries — directional, not a benchmark.
- typed_profile's 1.0 is trivial by construction; its real-world cost is the fixed inject budget every
  turn + a write-time "this is a preference" classification, and it doesn't generalize to arbitrary memory.
- The B-001 spec label is "Preference Application Without Explicit Prompt" (identity-drift-in-roleplay is
  B-002); luoxuejian000's request conflated the two — we run B-001 as specified and say so.

## Prior-art to verify before posting (agent running)
1. MemGPT/Letta "core memory" = always-in-context, NOT similarity-retrieved (arXiv 2310.08560).
2. mem0 user/profile memory as a distinct track.
3. Whether the "profile channel vs similarity archival" split is textbook (→ frame as measuring known
   design) or underdiscussed.
