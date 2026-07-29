# Checking a claim against the data that is supposed to support it

A Crucible procedure. Written 2026-07-29 from four consecutive rounds on a live collaboration, where
every round produced a claim contradicted by the author's own attached file.

The point is not that the author was careless — he was unusually generous with his data, which is the
only reason any of this was findable. The point is that **a claim and the file sent to support it are
two different objects, and almost nobody diffs them.** Every finding below came from reading the
attachment instead of the sentence.

---

## The order that works

Run these before arguing with the substance. Most defects die here, and dying here is cheap.

### 1. Count the rows against the claim's scope

The claim said "all N from 3 to 21". The CSV had 15 rows; N = 5, 7, 11, 13 were absent. The result was
being asserted for four data points that did not exist in the file.

> **Check:** enumerate what the sentence claims to cover, enumerate what the file contains, diff them.
> Not "does the file look complete" — *list both sets*.

### 2. Test every quantified boundary the claim states

The claim said "all odd N have p ≥ 0.092". One row had p = 0.03. Later: "for every odd N, p stays
above 0.45 even at the optimal T" — two rows sat at 0.067 and 0.117. And "p stays above 0.34 at every
angle" — four rows were at or below it.

> **Check:** for every `>`, `<`, `all`, `every`, `none` in the claim, write the filter and run it.
> Three of three such statements failed this way in one round.

### 3. Compare the effect size to the instrument's resolution

The separation was "perfect": max 0.026 on one arm, min 0.030 on the other. But `p = 0.012` appeared
eight times and nothing fell below it, putting the permutation count near 83 and the resolution near
0.012. **The gap was 0.004 — narrower than one step of the test measuring it.**

> **Check:** find the smallest distinct value the statistic can take (repeated values at a floor give
> it away), and compare that to the difference being claimed. A separation finer than the grid is not
> a separation.

### 4. Look for the confound that produces the result without the mechanism

Across the arm that "failed to resonate", Spearman(mean_error, p) = **−0.89**: the chains with the
*smallest* error had the *largest* p. A statistic that loses significance exactly where the model fits
best is not reading structure — it reads like a null that does not rescale with the error.

After the author supplied a normalised error column, it weakened but survived: −0.49 within that arm,
−0.83 across all of it, with the two groups differing in error scale (0.087 vs 0.062). So the labelled
variable and the error scale were the same variable under two names.

> **Check:** correlate the outcome against every *nuisance* column in the file — error, N, sample size,
> date. If the outcome tracks one of them as strongly as it tracks the claimed variable, the claim has
> a rival explanation sitting in its own dataset.

### 5. Check whether a scan was corrected

Two later tests scanned a parameter and reported the minimum p. **A minimum over a scan is not a
p-value.** Scanning thirty values of T and quoting the smallest needs either a correction or a null
built by running the identical scan on permuted data.

> **Check:** whenever a result is "at the best T / angle / threshold", ask what the null looks like
> *after the same search*. Applying the scan symmetrically to both arms keeps the comparison
> informative — but the number still cannot be quoted as a significance level.

### 6. Notice which objection goes unanswered

Four objections were raised. Three were addressed in the next round; the fourth — the confound in
step 4 — was skipped twice, silently, while new tests arrived for the others.

> **Check:** keep a list. An objection that keeps not being answered while adjacent ones are is
> usually the one the author cannot answer, and it is the one to press.

---

## What earns the right to do this

**Run everything on your own claim first.** In the same week this procedure was used, it killed our
own framing three times: a comparison that put a competitor's status-toggle beside our purpose-built
eraser (matched properly, we tie); a conclusion drawn from a module that turned out to be dead code;
and an "unverified" verdict that was a limit of our instrument, not of the system measured. A
procedure that only ever fires outward is a weapon, not a method.

**Say what survives.** Steps 1–3 above killed statements, not the result. The parity separation may
well be real. The finding is that three sentences describing it were not supported by the file
attached to them — which is fixable, and better fixed before publication than after.

**Send it to the author first.** Everything here reached the person whose work it concerns before it
reached anyone else, with the data and the script. A finding that arrives as a public verdict rather
than a question is an attack, and it will be answered as one.
