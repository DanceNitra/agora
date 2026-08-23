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

**Fix, and the first version of this line was wrong.** It said "assert the included cohort's mean
exceeds the pooled mean". That guard fails on clean data: the founder cohort's fatter right tail
drags the pooled mean above the professional cohort's own top half (13.512 against 13.830) with
nothing wrong. The invariant that holds is against each subset's OWN cohort mean — selecting the top
of a distribution always raises that distribution's mean, and reversing the comparison always lowers
it. See the status section below.

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

---

## Status: all six fixed, each tested in both directions

Every fix below had to satisfy two conditions before it shipped: the clean run still exits 0, and the
mutant that exposed the hole now fires. That is not ceremony. **Three of the seven first attempts
failed one of the two conditions**, and only the test found it:

| file | guard added | clean | mutant fires |
|---|---|---|---|
| `llm_judge_length_null.py` | baseline agreement must exceed chance | 0 | yes |
| `llm_judge_length_null.py` | explicit word/char dispatch, `else: raise` | 0 | yes |
| `nudge_pubbias_artifact.py` | `TRUE_D` interpolated, not frozen in prose | 0 | n/a (correctness fix) |
| `founder_survivorship_null.py` | survival band `0.5 < s <= 1.0` | 0 | yes |
| `founder_survivorship_null.py` | included subset above its **own** cohort mean | 0 | yes |
| `good_to_great_null.py` | `trait_prev` is a probability; band is ordered | 0 | yes |

The three that failed first time:

1. The survival assert does not reach the inclusion-cutoff hole at all — survival stays 1.00/1.00
   whichever way that comparison points. A second, different guard was needed.
2. That second guard first compared the included subset with the **pooled** mean and failed on clean
   data: the founder cohort's fatter right tail drags the pooled mean above the professional cohort's
   own top half, 13.512 against 13.830, with nothing wrong. Comparing each subset with its own cohort
   mean is the property that actually separates "top" from "bottom".
3. The word/char swap was first going to be an assert on the two counts. There is no such invariant to
   assert — word counts and char counts have no fixed order across datasets. An explicit dispatch with
   a raising `else` was the honest fix: it makes the same edit loud instead of provable.

One file needed no change at all: `meta_audit_scoring.py`, whose three flagged mutants are all
identifier edits in a data table. It was already the only GATE of the eight. `adaptive_defenses.py`
and `arena_style_only.py` had no flagged survivors to diagnose, so they are untouched and unjudged
here rather than cleared.

---

## Adversarial re-read of the four NOT A HOLE verdicts

Those four were judged by me and by nobody else, which is the weakest evidence in this document. Each
was attacked with the specific argument most likely to overturn it. **All four survived** — and a
re-read that always confirms is worth no more than the first read, so what each attack actually did
is recorded below rather than just the outcome.

### `founder_survivorship_null.py` L34 `SIG_PROF 0.05 -> 0.1` — attacked, stands

The attack: the probe ends with a verdict that is conditional on one number and asserts a second,

    print("VERDICT (mechanism):", "FAILED -- ... tail-driven (median << mean)."
          if gap >= 2.0 else "PARTIAL.")

`gap >= 2.0` is measured. **`median << mean` is not looked at anywhere.** That is the same shape as
the "~80% human parity" hole ruled REAL above, so it should have fallen.

The falsifier: sweep every reachable operating point and find one where `gap >= 2.0` while the median
is NOT far below the mean. 24 points qualified. The median/mean ratio maxes at **0.642** (sig_f=0.09,
inc=70, gap 2.42, median 1.55) and falls to 0.000 by sig_f=0.30. The clause is never asserted falsely
in any configuration this probe can reach.

Verdict stands, and now for a measured reason rather than an assertion. The hardcoded clause is still
a latent risk if the parameter space ever widens — noted, not fixed, because fixing it today would
mean guarding a condition nothing can currently violate.

### `good_to_great_null.py` L38 `mediocre_band 0.5 -> 1.0` — attacked, stands, with a limitation

The attack: line 82 prints a hand-written `"(mediocre 15y, then >=Nx market 15y)"`. With the band
mutated to (1.0, 1.5) the cohort is at-or-above market, so the word "mediocre" would be doing what
"top 50%" did in the cutoff hole.

It does not land. (1.0, 1.5) is still *around* market, not exceptional, so the label is narrowed
rather than falsified — unlike the cutoff case, which was a clean inversion.

**The limitation found instead:** the guard added tonight only asserts `0 < lo < hi`. A band of
(2.0, 3.0) would select clearly above-market firms and still print "mediocre". Not fixed, because the
honest invariant would have to encode what "mediocre" means and inventing one to have something to
assert is the mistake this document already records under the word/char swap.

### `meta_audit_scoring.py` L67/L73/L79 — attacked, stands

The attack: the flagged mutation turns post id 17 into 34, and 34 is not in the table (ids run 1-31,
36, 42 across 32 rows). A reader following that list finds nothing. So: does anything validate ids?

Sharpened to the case that would actually bite — mutate 17 into **18**, a duplicate of an existing
id. The probe exits 1 against a base exit of 0. Its own assertions catch it, which is consistent with
it being the only GATE of the eight. The original mutation produces a unique-but-unused id and the
probe reports the new data faithfully, which is what mutating a datum should do.

Verdict stands.

