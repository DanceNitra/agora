# Contradiction / stale-echo detection fixture

A small, labeled, self-contained benchmark for **structural detection of a corrected-away fact that is
re-stated** ("echo"). The task: given the CURRENT (corrected) fact and a candidate assertion, flag whether
the candidate is a **stale echo** (a restatement — verbatim or paraphrased — of a value that was already
corrected away) or just the current value restated.

**Why it's hard (the point):** plain embedding similarity can't separate a *contradiction/stale value* from
a *duplicate/current value*. In this fixture a **paraphrased** stale echo sits at mean cosine **~0.83** to
the current correct fact — indistinguishable by similarity alone. Consistent with the published finding that
cosine separates contradictions from duplicates at **AUROC ~0.59** (near chance), with contradictions often
*more* similar to the original than a genuine rephrase (Yadav, "Temporal Validity in Retrieval Memory",
arXiv:2606.26511). So a detector that flags the stale echo must use **structural**, not distributional, signal.

## Files
- `contradiction_echo_detection_fixture.jsonl` — 126 rows.

## Columns
| field | meaning |
|---|---|
| `scenario_id` | row id |
| `question` | the query the fact answers |
| `current_fact` | the CURRENT, correct value (after correction) |
| `candidate` | the assertion to classify |
| `candidate_kind` | `stale_echo_verbatim` / `stale_echo_paraphrase` / `restated_current` |
| `is_stale_anomaly` | **label**: 1 = stale echo (should be flagged), 0 = current value |
| `cosine_to_current` | nomic-embed-text cosine(candidate, current_fact) — the embedding baseline to beat |

## Scoring
Precision / recall / F1 on `is_stale_anomaly` (83 positives / 43 negatives). A pure cosine-threshold
baseline does poorly on the `stale_echo_paraphrase` rows by construction — that gap is the target.

## Provenance
Dialogue text derived from **MemBench** (github.com/import-myself/Membench, MIT); paraphrased echoes
generated across three model families. MIT-licensed, no private data. Built for a cross-framework test of
structural anomaly detection against the embedding-similarity baseline.
