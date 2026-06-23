# RAMR v2 adversarial-distraction: lexical near-miss does NOT bite (honest negative + corrected design)

**Date:** 2026-06-23  **Model:** qwen3-coder:30b (local, cloud-free)  **n=30** synthetic 3-hop chains.

## What was tested
v1 showed only mild distraction harm from *random* same-format distractors (a strong reader shrugs them off).
Hypothesis for v2: distraction bites when distractors are **confusable** — near-miss companies sharing the gold
company's name prefix (gold `Zyncorp` -> `Zyntech`, `Zyndyne`), each carrying a complete FALSE sub-chain
(`<C_near> is headquartered in <Xd>` + `currency of <Xd> is <Dd>`). No contradiction (the person P only works at
the gold company). Swept K near-miss chains and compared against a **matched random control** (same #distractor
facts). Falsifier: if adversarial accuracy is not materially below the random control at equal noise,
lexical near-miss is not the confusability lever.

## Result
| K near-miss chains | #distractor facts | ADVERSARIAL acc | RANDOM-control acc |
|---|---|---|---|
| 0 | 0  | 1.000 | 1.000 |
| 1 | 2  | 1.000 | 1.000 |
| 2 | 4  | 0.967 | 0.967 |
| 4 | 8  | 0.967 | 0.867 |
| 8 | 16 | 0.900 | 0.800 |

## Verdict (honest negative)
**Lexical near-miss is NOT the distraction lever.** Adversarial near-miss distractors did not hurt more than
random ones — if anything *less* (+0.10 the WRONG sign for the hypothesis, and within n=30 noise ~+/-0.09). A
strong reader pattern-matches the **full** gold entity token, so a shared 3-char prefix with a different suffix
(`Zyncorp` vs `Zyntech`) is trivially distinguishable. Both distractor types cause only mild harm (~0.10-0.20 drop
at 16 facts); neither collapses accuracy. So the v2 metric as designed does not bite.

## Lesson for the benchmark
Confusability that matters is **structural at the query anchor**, not lexical at the bridge. To make DISTRACTION
bite you must attack the entity the question pivots on (the person P): seed near-miss PERSON names, each carrying a
**complete false chain** to a different currency. If the reader confuses the query anchor (`Vorander` vs `Vorette`)
it follows the wrong chain and answers wrong — a genuine, fair (non-contradictory) trap. (Or: use a weaker reader;
but the point of the benchmark is to find the regime where even a strong reader fails.)

## Next (v2b, next cycle — one substantive change per cycle)
Query-anchor near-miss false chains; same matched-random control; same falsifier. Then add the FACT-RETENTION and
OUTCOME-RANKED-RECALL task families from the existing labs. Cloud-free; all publishing gated on owner approval.

_Discipline: change -> observe -> measure -> next. This cycle's change (v2 lexical near-miss) is measured and
falsified; the corrected design is recorded but NOT yet built (held for the next cycle)._
