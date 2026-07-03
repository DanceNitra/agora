DRAFT — gated GitHub comment for deepseek-ai/DeepSeek-V3#1462 (reply to @luoxuejian000's B-001 request).
NOT POSTED. Owner approves before anything goes out. Tag @luoxuejian000 @qingkong66.

---

@luoxuejian000 — ran B-001 the same substrate way as B-003, and it turned into something more useful than a single trace, so I'll share the shape rather than one number.

First, a scope note: the spec's B-001 is *Preference Application Without Explicit Prompt* (identity-drift-in-roleplay is B-002). I ran B-001 as written — a preference set from prior sessions, a new session on an unrelated topic. And to be upfront: the fix here (a preference/profile channel that's injected unconditionally, not retrieved by query similarity) is **not mine** — it's the working-context vs archival split from MemGPT (Packer et al., 2023, arXiv:2310.08560; "core memory" is Letta's later term for it). So instead of re-deriving that, I measured **where the two channels cross over**, which is the part I couldn't find quantified.

**1) The query-overlap crossover.** A preference is load-bearing for answer *style* but topically orthogonal to a new session's *content*, so similarity retrieval only surfaces it when the query itself is about style. Swept over an independently-written query set (off-topic / mid / explicitly-about-style), pref_recall@5:

| similarity channel | off-topic (the B-001 case) | mid | about-style |
|---|---|---|---|
| nomic-embed-text | 0.29 | 0.67 | 1.00 |
| mxbai-embed-large | 0.17 | 0.67 | 1.00 |
| tf-idf (lexical) | 0.04 | 0.00 | 0.58 |

Same shape on three independent mechanisms, so it's not an embedder artifact: on an off-topic query, similarity is an unreliable way to surface a preference (cosine query↔pref ≈0.42 vs query↔on-topic-memory ≈0.75–0.79 for the neural channels).

**2) The scale crossover — this is the part I think is actually open.** "Inject all preferences unconditionally" is free *only while the set fits the inject budget*. With 3 turn-relevant preferences hidden in a growing set at budget B=12, recall of the relevant ones:

| N preferences | inject-all | recency-cap | random-B |
|---|---|---|---|
| 3, 10 | 1.00 | 1.00 | 1.00 |
| 30 | (>B) | 0.40 | 0.38 |
| 100 | (>B) | 0.14 | 0.14 |
| 300 | (>B) | 0.03 | 0.05 |

Past the budget you have to *select* which preferences to inject (≈B/N survive under a generic selector) — i.e. the profile channel becomes its own retrieval problem, and ranking preferences by similarity to the query walks right back into crossover #1.

**3) Which fuses B-001 with B-003.** A preference changes across sessions (concise → detailed). A naive append profile keeps both values active, so the stale one is still injectable; keyed supersession retires the old (stale active = 0, current = 1). So maintaining a *bounded, current* profile is the same supersession machinery as B-003 — B-001-at-scale and B-003 look like one problem, not two.

Honest caveats: this is substrate only (retrieval is the precondition for preference application, not proof the model then applied it); one fixture, small query set — treat the crossover *shapes* as the signal, not the exact rates. mem0, for contrast, is user-scoped but still similarity-retrieved (filtered by user_id), so it doesn't remove the orthogonality dependence.

Runnable receipt (zero extra deps beyond numpy + a local embedder, MIT — re-run or break it): https://github.com/DanceNitra/agora/blob/main/mnemo/probes/bseries_b001_crossover.py

Frontier question if it's useful for #1466's matrix: *at what preference-set size / query-overlap does the profile channel stop being "inject-all" and become its own retrieval+supersession problem — and is that crossover, more than the channel itself, what governs cross-framework identity persistence?* Happy to fold the substrate rows into the unified matrix there.
