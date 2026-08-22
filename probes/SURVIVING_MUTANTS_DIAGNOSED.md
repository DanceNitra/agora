# The surviving mutants, diagnosed one by one

The mutation sweep (`do_the_controls_in_our_published_probes_actually_fail.py`, main `dbe25ec`) left
59 mutants alive across the 8 published probes. "Survived" is trivially true for a probe with no
verdict, so the count on its own is not evidence. Each flagged mutant below was run against its
baseline and the output diffed, and the question asked was the only one that matters: **does the
probe's conclusion move, or only its digits?**

Verdicts are one of REAL HOLE, MINOR, or NOT A HOLE. Four of the ten are NOT A HOLE and are recorded
as such, because a sweep that finds a defect everywhere it looks has stopped measuring.

---

## REAL HOLE — a hardcoded sentence beside a number that can contradict it

Two of these, and they are the same defect in two files.

### `llm_judge_length_null.py` L102 `== -> !=`

`ok += (r["winner"] == m)` inverted. GPT-4 vs human agreement falls **0.863 → 0.137**, and the line
printed next to it still reads:

    [1] GPT-4 judge vs HUMAN majority: 0.137 (n=798) <- the celebrated ~80% 'human parity'

The headline moves from `RECOVERS 50%` to `RECOVERS -50%` and nothing objects. A judge agreeing with
humans 13.7% of the time is *anti*-correlated, and the probe still narrates it as ~80% parity.

**Fix:** assert the baseline agreement exceeds chance before any of the downstream framing is printed.
Comparing to Zheng's 85% is meaningless if the measured figure is below 0.5.

### `nudge_pubbias_artifact.py` L33 `0.20 -> 0.4`

`TRUE_D` doubled. One line interpolates it and updates correctly:

    True between-domain ratio = 1.00 (identical true effect d=0.4 in every domain)

The next line hardcodes it and now lies:

    Pooled 'other' effect (n=300) = 0.40 (true 0.20, barely inflated)

The same constant is live in one sentence and frozen in the other. **Fix:** interpolate `TRUE_D`
everywhere it is named.

## REAL HOLE — a degenerate state reported as a result

### `founder_survivorship_null.py` L43 `< -> >`

The ruin filter `val.min(axis=1) < RUIN` reversed. Survival collapses **1.00/1.00 → 0.00/0.00** and
the probe still prints a confident gap (2.48x, 1.36x median) from what is left. There is a guard for
an empty cohort (`if len(inc_p) == 0 ... return None`) but none for a cohort that is technically
non-empty and substantively nothing.

**Fix:** assert the survival fraction is in a plausible band, e.g. `0.5 < sp <= 1.0`.

### `founder_survivorship_null.py` L55 `>= -> <=`

The inclusion cutoff `prof[sp & (prof >= cutoff)]` reversed, which turns "top 50%" into bottom 50%.
The gap explodes **1.55x → 6.29x** while the column header still prints `top 50%`.

**Fix:** assert the included cohort's mean exceeds the pooled mean — a one-line check that the label
and the computation agree.

### `good_to_great_null.py` L38 `0.6 -> 1.2`

`trait_prev` is a probability and 1.2 is not one. The probe accepts it and reports
**"~60 of 60 candidate traits are shared by ALL selected firms by chance"** against a baseline of ~0
of 60 — a result that looks like a finding and is an invalid input.

**Fix:** validate the domain of the probability parameters.

## MINOR

### `llm_judge_length_null.py` L48 `== -> !=`

`mode == "word"` inverted swaps the word-count and char-count branches. Rows [2] and [3] exchange
values (0.681 / 0.664) and the headline moves 50% → 45%. Two rows are mislabelled; the qualitative
conclusion survives. Worth a fix, not worth a correction notice.

## NOT A HOLE — recorded so the count is honest

### `founder_survivorship_null.py` L34 `0.05 -> 0.1`

`SIG_PROF` is a declared model parameter, not a threshold. Doubling it changes the volatility-ratio
column from 1.40x/1.80x/2.20x to 0.70x/0.90x/1.10x, which the probe prints. The reader sees the
different operating point. Changing a parameter changes the experiment; that is not a missing control.

### `good_to_great_null.py` L38 `0.5 -> 1.0`

`mediocre_band` lower bound. The cohort shrinks 30 → 11 firms and the summary sentence updates itself
to "a ~11-firm good-to-great cohort". The number propagates into the prose correctly. Not a hole.

### `meta_audit_scoring.py` L67 `17 -> 34`

This is a post **identifier** inside a data table, not a sample size — an earlier note of mine called
these "sample sizes" and that was wrong. Post 17 is replaced by post 34 and the probe faithfully
reports the new list. Mutating a datum changes the data.

### `meta_audit_scoring.py` L73, L79

Same shape as L67, same verdict.

---

## Tally

| verdict | count |
|---|---|
| REAL HOLE | 5 |
| MINOR | 1 |
| NOT A HOLE | 4 |

The five real ones fall into two shapes, and neither is exotic:

1. **A sentence written by hand next to a number computed at run time.** When the number moves, the
   sentence does not, and the pair becomes a lie no test is watching. Both instances are in prose the
   probe prints about its own result.
2. **No domain validation on an input.** A survival rate of zero, and a probability of 1.2, both pass
   straight through into a published-looking table.

Neither is caught by any existing check because seven of the eight probes assert nothing at all.
