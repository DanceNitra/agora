# GATED Reddit reply draft — r/Rag 1ujwwu6, reply to jacksonxly's composition question (comment ov3wrze)

Owner posts manually (Reddit = owner's voice, never auto-post). Numbers VALIDATED: probe built + run
this cycle (locomo_composed_soft_filters.py, self-check 0/1568 vs shipped path). STORM landscape run
(storm-reports/soft-filter-composition-retrieval-fusion-briefing.html). Citations verified vs primary sources: 10/10 checked, 0 fabricated, 3 corrected (BM25F CONFIRMED;
ES/Solr official docs CONFIRMED; Li&Croft + RRF CONFIRMED w/ caveats). Two-skeptic re-audit applied
(cap-artifact caveat in the bullet, citation-precision fixes, tone edits).

---

## DRAFT BODY (reddit-friendly)

Ran the composition arm. Both-signals subset (temporal expression + exactly one resolvable name, n=183 of 1385 signal-bearing), recall@20:

- plain hybrid 0.466
- time-soft only 0.755, alias-soft only 0.697
- one capped weighted term per dimension: 0.702 (−0.053 vs time-soft, CI crosses zero — artifact of my cap parameterization, see below)
- uncapped sum: 0.817 (+0.062 vs time-soft, CI[+0.020,+0.106])
- **multiplied: 0.865 (+0.110 over the best single arm, CI[+0.063,+0.160])**

So they compose — +0.399 over the floor when both fire — but the interesting part is *why the capped version looked like crowd-out*. I almost reported that as crowd-out; checking the first run showed it's arithmetic, not retrieval: with trust 0.9 per dimension and the cap at 1.0, a double-match scores 1+1.0×3 = 4.0 vs a single match's 3.7 — the cap flattens exactly the joint evidence the composition exists to use. Uncapped, addition composes fine; multiplication just composes a bit more (0.865 vs 0.817 — I didn't compute that direct contrast's CI, so "came out on top", not "significantly better").

Which turns out to be a 20-year-old lesson I re-derived the hard way: BM25F (Robertson/Zaragoza/Taylor, CIKM 2004) — combining evidence outside the model's saturating form breaks it; Elasticsearch function_score defaults score_mode to multiply and caps via max_boost on the combined score; Solr's dismax docs officially call additive bf "a poor way to boost". So the rule for a memory store: compose neutral-at-1.0 multiplicative factors, one per dimension; if you cap, cap the product.

Honest scope: one benchmark, one embedder; off the both-subset the composed terms are identity by construction (inert factor = 1), so this says nothing about correlated signal pairs — speaker×time is the friendly near-orthogonal case (on 85% of the both-subset the gold turn genuinely satisfies both conditions; 15% partial/misleading, and recall held anyway). A correlated pair (speaker×topic) is where the product should double-count — that's the arm I'd run next.

Receipt: locomo_composed_soft_filters.py in https://github.com/DanceNitra/agora/tree/main/mnemo/probes (self-check built in: the reconstruction has to reproduce the shipped single-arm path exactly, 0/1568 diverged).

---
(sign-off in owner's voice; keep it plain)
