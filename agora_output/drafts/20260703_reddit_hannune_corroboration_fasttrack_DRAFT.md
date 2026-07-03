# GATED DRAFT (Reddit r/LangChain, thread 1ulss3t, reply to u/hannune's comment ov8lvww).
# OWNER POSTS MANUALLY, own voice. hannune said: corroboration gate generalizes because it's metadata not
# geometry; the 1.0->~0.08 recall cost is the real production tradeoff; the untrusted ingestion path needs a
# fast-track corroboration signal beyond use-frequency -- e.g. source-provenance linking at ingest rather
# than waiting for downstream outcomes.
# VALIDATED in code this cycle (mnemo/mnemo.py _is_corroborated): corroboration = earned credit() OR >=2
# DISTINCT-canonical-source links. Live test: 2-distinct-source ingest -> corroborated=True (no credit needed);
# 2 same-origin links -> False (sybil canonicalized to one); credit() path -> True. So hannune's fast-track is
# already the intended path; the frontier is real source-independence. The 0.08 = uncorroborated-true-memory
# recall (prior post's honest cost). NO new external citations.
# STATUS: NOT POSTED -- owner-gated, owner posts.

Exactly — metadata not geometry is the whole reason it survives an embedder swap, that's the part that matters most. And the 1.0→0.08 is the honest cost: it's specifically the single-source, never-corroborated tail — a legit-but-rare memory gets taxed while it waits to earn corroboration.

Your fast-track instinct is right, and it's already the intended path: the gate graduates a memory on *either* an earned downstream outcome *or* ≥2 distinct-source provenance links at ingest — so a fact that two independent sources assert corroborates immediately, no waiting for outcomes. (Just checked it: two-distinct-source ingest → corroborated, single-source → not.)

The catch your suggestion opens: "distinct source" has to mean *genuinely independent*, or an attacker just asserts the poison from two "sources" of their own. We canonicalize the source ids before counting, so Wikipedia, wikipedia.org and a www.wikipedia.org URL all collapse to one key — re-asserting the same poison under three spellings earns you nothing. But that only catches variants of one origin; two genuinely different fake domains still pass the count. The linking is the easy part; provable source-independence is the hard one.
