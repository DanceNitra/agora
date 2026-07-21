# Neeraj (u/CalmEstablishment644, MemStrata) — reply FINAL (owner pastes on Reddit; reddit is owner-manual)

Reply to his comment on r/LLMDevs 1uhajcp. Now includes: writeup link (para 1) + GitHub contact via the
agora repo issues/discussions (para 3, owner-approved). No email leak; links are appropriate (he asked for the probes).

---
That's exactly the synthesis I was hoping we'd land on. Quick update since we last spoke: I took the supersession blind spot to our own stack and it replicated cleanly — AUROC 0.61 for the cosine "is-this-a-supersession" classifier (right on your ~0.59), and a pure-cosine store served the stale value 41.7% of the time. So we shipped the deterministic fix in our open-source memory core (inspeximus): a (subject, relation, object) supersession key that retires the old value with no threshold and no LLM call — stale recall went to 0% in the same probe. Wrote it up crediting your paper: https://dancenitra.github.io/agora/public/posts/rag-supersession-blind-spot.html

Your blueprint is right, and I'd frame it the same way: write-side = corroboration that resists sybil sources (we just added entity-resolution on source identifiers before counting, so "Wikipedia / wikipedia.org / a URL" collapses to one real source), and read-side = your bitemporal ledger resolving structured facts by validity-time, no similarity threshold. Write-safety + read-correctness as two halves of one layer.

Genuinely up for comparing notes properly. The runnable probes (the supersession replication + the eviction/freshness benchmark) and the inspeximus core all live in our repo — easiest is GitHub: github.com/DanceNitra/agora (open an issue or a discussion there and I'll point you straight at them). Keen to compare on the same ground.
---
