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


## Honest limitations
- **Templated utterances:** the reversions/affirmations are drawn from a small set of hand-written templates
  ("go back to what we had before", "revert that last change", etc.), so a detector could exploit surface
  template patterns rather than learn the general discourse relation. Treat high scores here as necessary, not
  sufficient — a real win should generalize to unseen phrasings.
- Synthetic, single-domain (config-style facts), n=140. A starting probe for structural reversion detection,
  not a definitive benchmark.
