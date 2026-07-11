# Value-obscuring reversion fixture (the structural frontier)

The companion to `contradiction_echo_detection_fixture.jsonl`. There, a re-stated stale value **keeps the
value token**, so a deterministic object/value match catches it. Here the harder case: after a fact is
corrected (`old -> new`), a later utterance **re-opens the decision without ever naming the value** —
"let's go back to what we had before", "revert that last change", "undo the correction". The task: does the
utterance **reopen the fact to the stale value** (label 1) or affirm the current one / introduce a named new
change (label 0)?

**Why it's the frontier:** the value is never spoken, so both value-based and similarity-based methods fail —
the signal is a **discourse relation** (revert vs keep), not the sentence content. Measured baselines on this
set (140 rows, 60 positive):

| baseline | F1 | why it fails |
|---|---|---|
| object/value match (= mnemo `echo_guard`) | **0.032** | the reversion never names the old value — nothing to key on |
| cosine (candidate vs old fact, best threshold) | **0.554 ≈ chance** | "go back" carries no lexical/semantic trace of the value (positive base rate 0.43) |

A method that flags "this utterance re-opens a settled decision" from the **shape** of the exchange rather
than its values would be a real result neither approach gets today.

## Columns
`id`, `entity`, `old_value`, `current_value`, `context` (the old->new correction history), `candidate`
(the utterance to classify), `kind` (`obscuring_revert` / `obscuring_keep` / `named_new`),
`reopens_stale` (**label**: 1 = reopens the fact to the stale value), `cosine_cand_to_oldfact` (a baseline).

Synthetic, MIT, no private data. Built to test structural / discourse-level reversion detection.


## Independent replication (Marat Sultanov / TAT)

Marat Sultanov ran his TAT / Triplenet structural model against these fixtures and published the write-up:
[TAT-ROOT / value_obscuring_rastislav](https://github.com/maratsultanov2/TAT-ROOT/tree/master/experiments/value_obscuring_rastislav).
Scoped to what it actually shows, and cross-checked on our side row-for-row:

- **v2 / v3** (paraphrase-without-revert-words; structural value assertion): TAT F1 **1.00**, where the
  object/value and cosine baselines sit at 0.03–0.60. On these levels the structural-over-lexical claim holds,
  and we reproduced the numbers independently (v2 from the shared model, v3 predictions matched 140/140).
- **v4** (coreference; the anchor referenced by role, no named value): TAT F1 **0.6667** (recall 1.0,
  precision 0.5), which we recomputed from his predictions. The failure is cleanly localized: it detects
  whether a referenced role exists in the context (`named_new` 20/20) but not which anchor owns that role
  (`obscuring_keep` 0/60) — the second hop of the chain, still open.

Note the audit history behind v4: our first two cuts had shortcuts (a literal anchor-name substring, then a
template-parity artifact) that a trivial baseline solved at F1 ~1.0; both were found and fixed before this
result, which is why v4 is now hard for every method including TAT. Next step (agreed): a naturalized variant
with the same held-out discipline, comparing multi-hop attention vs feature-engineered chains vs an LLM
baseline on text none of them saw.

## Honest limitations
- **Templated utterances:** the reversions/affirmations are drawn from a small set of hand-written templates
  ("go back to what we had before", "revert that last change", etc.), so a detector could exploit surface
  template patterns rather than learn the general discourse relation. Treat high scores here as necessary, not
  sufficient — a real win should generalize to unseen phrasings.
- Synthetic, single-domain (config-style facts), n=140. A starting probe for structural reversion detection,
  not a definitive benchmark.
