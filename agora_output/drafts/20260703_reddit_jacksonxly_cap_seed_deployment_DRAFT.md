# GATED DRAFT v2 (Reddit r/Rag, thread 1ujwwu6) — reply to u/jacksonxly's cap/seed follow-up.
# OWNER POSTS MANUALLY, own voice (ML crowd hates AI prose; trim/re-voice freely).
# He made two correct methodological points; we CONCEDE both and isolate the regime he actually asked about.
#
# VALIDATED this cycle: mnemo/probes/locomo_composed_soft_filters.py re-run, self-check 1568/0,
#   single-cue invariant TRUE (comp_mult==comp_sum==comp_capped on single-cue subset -> seed=1.0 no-veto proven).
# NUMBERS (all from the re-run result JSON):
#   both-fire subset n=183: hybrid .466, time_soft .755, alias_soft .697, comp_capped .702, comp_mult .865
#     comp_mult vs time_soft (best single cue) = +0.110 CI[+0.063,+0.160]
#     comp_capped vs time_soft = -0.053 CI[-0.107,+0.002]  (capped BELOW best single cue)
#     joint truthfulness 156/183 = 85.2%
#   single-cue-only n=1202: hybrid .603, comp_mult .753 (== comp_sum == comp_capped) -> +0.151 CI[+0.129,+0.173]
#   coverage-weighted (>=1 cue fires) n=1385: comp_mult .768 vs hybrid .585, +0.183 CI[+0.162,+0.206]
#     (but ~85% of these rows fire only ONE cue -> mostly single cue, NOT composition)
#
# AUDIT applied (3-lens stress-claim): method+skeptic -> pooled 0.768 dilutes his single-cue regime, so
#   isolate single-cue-only (+0.151, invariant proves no-veto) + headline composition on both-subset vs best
#   single cue; overclaim -> "decorrelating cleaner" softened to his-hunch-untested, "deployment number"
#   reframed to coverage-weighted mix, "a hair below" -> "below", single-corpus caveat added.
# NO external citations. STATUS: NOT POSTED -- owner-gated, owner posts.

Both land, thanks — and the seed is the sharper of the two, so let me isolate it properly.

On the cap: agreed, null by construction here. I'd logged the joint truthfulness and 156/183 (85%) of that subset have the gold turn genuinely in *both* filters, so there's almost no spurious over-count for a cap to remove — it mostly clips real joint evidence, which is why capped lands below the strongest single cue (0.702 vs 0.755) instead of helping. So it's "cap barely tested here," not "cap unnecessary." Your point that a genuinely correlated pair is where it'd bite, and that decorrelating first (resolve the entity conditioned on the time bucket so the second factor carries only its residual) beats clamping — I think you're right, but I haven't run it; speaker×topic is the pair that'd actually exercise it, worth a run.

On the seed you're right the both-fire number says nothing about the regime where one cue carries it, which is exactly where the missing-dim multiplier bites. Isolated: single-cue-only questions (n=1202), missing dim at 1.0 — comp_mult 0.753 vs 0.603 floor, +0.151 (CI [0.129, 0.173]), and there comp_mult == comp_sum == comp_capped to the digit, i.e. the lone strong cue is preserved exactly, no veto. That's the "1.0 keeps it graceful" property measured; a sub-1.0 seed would drag those down.

So it's three separate numbers, not one:
- composition synergy (both fire, n=183): comp_mult 0.865 vs 0.755 best single cue, +0.11 (CI [0.063, 0.160]) — the real "do two cues stack" number.
- single-cue regime (n=1202): +0.151 over floor, lone cue preserved (above).
- coverage-weighted, at-least-one-fires (n=1385): 0.768 vs 0.585 — but ~85% of those rows fire only one cue, so that's mostly the single cue, not composition.

All on one corpus (LoCoMo) / one embedder (nomic) / one retriever, so read it as within-benchmark, not a law. Same probe if you want to pull it apart: mnemo/probes/locomo_composed_soft_filters.py.

---
# SHORTER alt (~4 sentences):
Both land. On the cap you're right it's null by construction — 156/183 (85%) of that subset have the gold turn genuinely in both filters, so there's almost no over-count for a cap to remove (capped 0.702 is below the best single cue 0.755); it'd only bite on a real correlated pair like speaker×topic, and I think your decorrelate-first instinct beats clamping though I haven't run it. On the seed you nailed the regime that matters: isolated to single-cue-only questions (n=1202, missing dim at 1.0), comp_mult 0.753 vs 0.603 floor (+0.151), and comp_mult == comp_sum == comp_capped to the digit — the lone cue is preserved exactly, no veto, which is the "1.0 keeps it graceful" property measured. So three numbers, not one: composition synergy 0.865 vs 0.755 best-single-cue on both-fire (n=183); single-cue +0.151; and a coverage-weighted 0.768 vs 0.585 across ">=1 cue fires" that's ~85% single-cue anyway. One corpus/embedder/retriever, so within-benchmark not a law.
