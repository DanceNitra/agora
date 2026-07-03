# GATED DRAFT (Reddit r/Rag, thread 1ujwwu6) — reply to u/jacksonxly's metadata-extraction comment.
# OWNER POSTS MANUALLY, in his own voice (Reddit ML crowd hates AI prose; trim/re-voice as you like).
# VALIDATED this cycle: mnemo/probes/locomo_composed_soft_filters.py re-run, self-check PASSED (1568/0 mismatch).
# Numbers verified from result JSON (both-subset n=183): hybrid recall@20 0.466 -> comp_mult 0.865 (+0.399,
# CI [0.327,0.472], excludes 0); comp_capped 0.702 is BELOW time_soft 0.755 (comp_capped_vs_time_soft = -0.053)
# -> capping is a tradeoff, NOT a win; do not claim the cap helps. Probe public on origin/main; LoCoMo is a
# public benchmark (data file itself gitignored on our side).
# STATUS: NOT POSTED — owner-gated, owner posts.

Yeah, this is basically what we measured, and the soft-not-hard part especially. Soft-preferring the rule-parsed time window + the entity turns as *multiplicative* rerank priors (not filters) took our recall@20 from 0.47 (plain hybrid) to 0.87 on the LoCoMo subset where both cues actually apply — big, but honestly only ~180 of ~1.5k queries; on the rest one cue carries it.

The gotcha that matches your instinct: time and entity are correlated, so a raw *product* of the two boosts double-counts. In our run the naive product still won; a capped/veto version (to guard the double-count) came out about level with the strongest single cue — a hair below, but within noise (the CI crosses zero) — so capping didn't buy anything here. The correlation is real, I just wouldn't oversell the penalty.

And +1 on closed-vocab entity *linking* + a schema-constrained slot filler — open NER was the piece we cut too.

(probe's public, mnemo/probes/locomo_composed_soft_filters.py; you'd supply the LoCoMo data yourself — it's a public benchmark, ours is gitignored. One corpus, so treat the shape as the signal, not the exact number.)

---
# SHORTER alt (if you want ~3 sentences):
Matches what we measured. Soft-preferring the parsed time window + entity turns as multiplicative rerank priors (your soft-not-hard point) took our LoCoMo recall@20 from 0.47 to 0.87 on the subset where both cues apply (~180 of ~1.5k queries). One gotcha: time and entity are correlated, so a raw product double-counts — a capped version to guard that came out about level with the single strongest cue (within noise), so capping didn't buy anything here. +1 on closed-vocab entity linking over open NER.
