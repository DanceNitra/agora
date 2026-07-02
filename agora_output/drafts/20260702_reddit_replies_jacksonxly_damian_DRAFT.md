# GATED reply drafts — r/Rag thread 1ujwwu6 (owner posts manually; edit into your own voice)

Both replies are on r/Rag "For multi-session agent memory, a single vector index doesn't beat BM25"
(https://reddit.com/r/Rag/comments/1ujwwu6). Both are the LAST word in their sub-thread (unanswered by us).
Watcher missed them because 1ujwwu6 wasn't in the reply-watch list — fixed now.

---

## REPLY 1 — to u/jacksonxly (comment ov2i75k)
His point (paraphrase): don't use the extractor's OWN softmax as the trust weight — in the overconfident-
on-wrong failure mode it's the corrupted signal, so weighting by it rebuilds the hard filter on exactly the
worst cases. Use an ORTHOGONAL signal instead: time = agreement between a rule parser (SUTime/duckling) and
the model's slot; entity = alias-match strength (exact vs fuzzy vs embedding-only). Calibration fixes
aggregate miscalibration, not adversarial overconfidence. His bet: raw-confidence-weighted craters on the
skewed set; parser-agreement + alias-strength pulls the 0.42 back.

DRAFT (RAN IT — full gate cleared: validate/storm/audit/verify; numbers verified vs the probe JSON;
receipt pushed at mnemo/probes/locomo_orthogonal_trust_weight.py):

> Ran it — your core point holds, and I also hit the harder half: the orthogonal signal only pays if it's
> genuinely independent, and mine wasn't.
>
> Setup: same LoCoMo hybrid retriever + speaker filter, predicted extractor flipped wrong 25% of the time,
> and I made it overconfident-on-wrong (self-reported 0.9 *even on the flips* — the case you flagged). Two
> weights on the filter's RRF contribution:
> - self-confidence (w = 0.9 × selectivity): overall −0.014, but on the wrong-fire subset it craters to
>   **0.287 vs 0.589 no-filter**. Exactly your point — weighting by the model's own belief up-weights the
>   filter on the fires you most wanted to suppress.
> - orthogonal agreement (w = 0.9 if an independent second opinion agrees, else 0): wrong-fire subset
>   **0.303** — barely above self-conf, and **−0.071 overall** (worse).
>
> Why it barely moved: my "independent" signal wasn't yours. I couldn't cleanly simulate alias-strength /
> parser-agreement on LoCoMo's exact-name speaker detection, so I used the nearest proxy — the majority
> speaker of the top-10 retrieved turns. It disagreed with the wrong extractor on only **19%** of the harm
> cases (too correlated — it shares the retriever's error) and falsely distrusted enough right cases to
> cost more than it saved. That's just co-training/Condorcet: agreement only helps when the two views fail
> *independently*, and a retrieval-derived opinion doesn't.
>
> So this doesn't test your actual proposal — SUTime-vs-model for time, or alias-match strength for entity,
> are extraction-quality signals plausibly independent of the flip, which is the property mine lacked. That's
> the arm worth running; I just need a setup with a real exact/fuzzy split. (Full disclosure: an audit of my
> first cut caught that I'd scaled the orthogonal arm 1.0 vs self-conf's 0.9 — unfair — so these are the
> corrected equal-base numbers.)
>
> Receipt: https://github.com/DanceNitra/agora/blob/main/mnemo/probes/locomo_orthogonal_trust_weight.py — if
> you know a dataset where the alias/parser signal is real, I'll run your exact version.

VERIFIED NUMBERS (mnemo/probes/locomo_orthogonal_trust_weight_result.json): overall hybrid 0.583 /
self-conf 0.569 (−0.014) / orthogonal 0.512 (−0.071); harm subset hybrid 0.589 / self-conf 0.287 /
orthogonal 0.303; D2 disagreed on 73/383 = 19.06% of harm cases. Gate: STORM (principle = Condorcet /
co-training, NOT novel — frame as "measured an instance"); stress-claim/method-audit caught the scale bug
(fixed) + that the retrieval-D2 is a proxy, not jacksonxly's signal (disclosed in the reply); verify-claims
= numbers match the JSON.

---

## REPLY 2 — to u/damian-delmas (comment ouydvja)
His point: his system (flex, github.com/damiandelmas/flex + an arXiv kernel paper) makes SQL the single
retrieval substrate — embeddings/FTS/vector/graph all become SQL operands; content-addressed identity
(file/repo/content/URL UUID) survives renames/deletes/worktree pruning; a build-time graph over
mean-centered embeddings; graph/vector math runs outside SQL (numpy/NetworKit) but retrieval stays in SQL.
This is him sharing his design, not a critique — a courtesy/collaboration reply is warranted.

DRAFT (short, genuine, one real technical touch-point):

> Nice design — SQL as the single substrate so composition is just SQL (the ORDER BY v.score*(1+m.centrality)
> example makes the point cleanly). The content-addressed identity surviving renames / worktree pruning is
> the part I'd have underestimated — that's the join key everything else leans on. And "graph over
> mean-centered embeddings" caught my eye: centering to kill anisotropy is exactly what moved the needle in
> a retrieval thing I was just testing. Reading the flex repo and the arXiv kernel paper.

---

## Posting notes
- Edit into your own voice (this crowd flags AI prose — you already got "why does this feel like an LLM
  talking with an LLM" on another thread). Short is good.
- jacksonxly is a genuine collaborator (long constructive back-and-forth) — worth keeping warm.
- Don't over-promise: only say "I'll report the number" if you actually want me to run the arm.

---

## SHORTENED, Reddit-friendly (2026-07-02) — use these

### → jacksonxly (~190 words) — FINAL (positive; tests his ACTUAL signal, not a proxy)
Ran your actual entity signal — alias-match strength as the trust weight — and it works; it's the best of the three.

Same LoCoMo hybrid + speaker filter. Exact-name questions → reliable extraction (5% wrong); no-name/ambiguous ones → the extractor has to guess (63% wrong), so errors concentrate exactly where you'd expect. Weighting the filter's contribution:
- flat self-confidence (0.9): +0.077 recall@20 overall, but it craters the wrong-fire subset to 0.371 (vs 0.448 no-filter) — it fires on the ambiguous guesses too.
- alias-strength (0.9 × alias, ≈0 on no-name): +0.084 overall (best) and the wrong-fire subset back to 0.436 ≈ no-filter. It keeps the filter's benefit on exact matches and backs off exactly where extraction is unreliable — because alias-strength is knowable a priori, independent of the model's own belief. Your point, confirmed.

Honest caveat: part of that harm-subset recovery is structural (alias=0 ⇒ no filter on the ambiguous set), so the headline is the overall number — you get the filter's upside without its downside. Receipt: https://github.com/DanceNitra/agora/blob/main/mnemo/probes/locomo_alias_strength_weight.py

(The earlier retrieval-derived "second opinion" proxy failed — 19% error-coverage, too correlated; that was the wrong signal, not the wrong idea.)

### → damian-delmas (~95 words; READ his repo + arXiv:2603.22587 first)
Read the flexvec paper — PEM (exposing the score array + embedding matrix as SQL-composable surfaces) is a clean way to put fusion/centrality/decay in the query itself, and 3 modulations in 82ms on 1M chunks on CPU with no ANN index is a genuinely surprising number. SOMA (content-addressed identity surviving renames) is the part I'd have underestimated — it's the join key everything else leans on. And your mean-centered embeddings caught my eye: centering to kill anisotropy is exactly what moved the needle in a retrieval thing I was just testing. Nice work.
