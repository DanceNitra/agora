# nullcheck — is this number real, or just what noise would produce anyway?

> A result is evidence of a real effect only if a model with **no effect** can't reproduce it.
> `nullcheck` simulates that null — the world where there's no true difference — at *your* sample
> sizes, and tells you, in plain language, whether your number survives. One file, zero deps.
> A sibling of [mnemo](../mnemo) / [ragfresh](../ragfresh).

## The problem (2026)
Teams are "awash in data, can't tell signal from noise." A/B tools flash *significant* on a fluke; a
dashboard moves and nobody knows if it's real; and the most common self-own — **peeking** (re-checking
the test as data arrives and stopping when it first looks good) — silently inflates false positives.

## What it does
```python
from nullcheck import ab_test, permutation_test, peeking_false_positive_rate

ab_test(100, 1000, 115, 1000)     # 10.0% vs 11.5% — a "+15% lift"
# -> p_empirical 0.28, verdict "NOISE — a no-effect null reproduces this routinely"

ab_test(1000, 10000, 1180, 10000) # +18% lift at big n
# -> p_empirical 0.0001, verdict "REAL — a no-effect null almost never reproduces this"

permutation_test(rev_A, rev_B)    # any two samples (revenue, latency…), assumption-free: shuffle the labels
```

- **`ab_test`** — conversion A/B by null simulation (no normality assumption): empirical two-sided p + a plain verdict.
- **`permutation_test`** — for *any* two samples; if the A/B label carried no signal, shuffling it would produce your gap just as often.
- **`peeking_false_positive_rate`** — quantifies the early-stopping trap.

## Measured (`python nullcheck.py`)
```
A/B 100/1000 vs 115/1000 (+15% lift) -> p 0.28  NOISE
A/B 1000/10000 vs 1180/10000 (+18%)  -> p 0.0001 REAL
permutation, same distribution        -> p 0.50  NOISE
peeking trap (true null): 1 look 5.3% false-positive -> 5 looks 14.4%  (2.69x inflation)
```

## Why this, not a significance calculator
A p-value formula bakes in assumptions (normality, one fixed look) that the real workflow violates —
which is exactly how teams get fooled. `nullcheck` *simulates* the null at your real sizes (no
distributional assumption via `permutation_test`) and makes the peeking inflation visible instead of
hidden. It's the "credit only the effect a null can't reproduce" engine behind our replication ledger,
turned into a self-serve check. Open-core; the core stays free.
