DRAFT — gated r/Rag reply to u/jacksonxly (metadata-filter point). Owner posts manually. NOT posted.
Every number verified: our deltas vs mnemo/probes/locomo_metadata_prefilter.py result; prior-art vs storm verifiers.

---

Went and actually measured your metadata point on LoCoMo — you were right. A cheap speaker pre-filter (exact-match the name the question mentions, applied before the BM25+vector hybrid) added **+0.146 recall@20** (0.583 → 0.729, 10/10 conversations, conversation-level bootstrap CI [+0.124, +0.173]) — bigger than the whole hybrid-over-BM25 win from the original post (+0.057). An oracle time/session filter (ceiling) was +0.345.

Two caveats so I don't oversell it:
- It's close to *best case*. LoCoMo has 2 speakers and the question names one ~89% of the time, so the filter halves the pool using a label the benchmark hands you. On many-entity data with noisy extraction — where a wrong filter hard-deletes the answer — it'll shrink and can go negative (I saw the harm mode on the ~6% where the gold turn is the other speaker).
- I ran brute-force retrieval. On an HNSW index a filter that correlates with embedding clusters (exactly the speaker/topic case) can *crater* recall unless the DB does filtered-ANN — so "add a filter" isn't free at scale.

So honestly it's less a new finding than a clean isolated number on the 60-year "filter before you rank" lever — mem0/self-query already bake it in, and Multi-Meta-RAG isolated it on news QA. The part I'd actually chase, and where your production experience beats a benchmark: does it still beat retriever choice at *low selectivity* with *predicted* (not gold) filters?

Script if you want to break it: https://github.com/DanceNitra/agora/blob/main/mnemo/probes/locomo_metadata_prefilter.py
