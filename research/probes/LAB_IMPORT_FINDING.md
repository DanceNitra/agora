# The lab measures a 1.20.0 copy — and what that did and did not cost

**Measured 2026-07-28, overnight audit loop.** Everything here was re-run this cycle.

## The defect

Thirteen scripts under `agora_output/lab/` insert `agora/inspeximus_pypi` into `sys.path`. Several insert
two or three roots in sequence, so which one wins is decided by insertion order, not by intent. Replaying
each script's own path edits in its own order and asking `importlib` what it would load:

**13 of 13 resolve to `agora/inspeximus_pypi/`**, which declares `name = "inspeximus"`, `version = "1.20.0"`.

Three different behaviours sit behind that one import name:

| artifact | `forget_subject('hr/alice')` on a store holding alice, bob, carol |
|---|---|
| `inspeximus_pypi` (1.20.0) | **erased 3, store empty** |
| live repo (HEAD) | erased 1, bob and carol survive |
| published wheel 1.86.0 | **REFUSED** — `AmbiguousSubject` |

The copy predates both erasure fixes: no `_canon_subject`, no ambiguity guard.

The import line reads identically whether it resolves to the copy or is a dead entry. That is exactly what
makes the harmful case invisible, and why the resolution is *replayed* rather than reasoned about
(`research/probes/audit_lab_import_resolution.py`).

## What it cost: nothing yet, and that is a measurement, not a hope

The scripts behind published numbers were re-run against **both** libraries, same inputs, same cycle.

**`exp_unnamed_revert.py`** — zero-dependency, 8 revert phrasings + 5 negative controls + a multi-key case:

```
                          as committed (1.20.0)     forced onto HEAD
revert-recall baseline         0/8 = 0.000            0/8 = 0.000
revert-recall prototype        8/8 = 1.000            8/8 = 1.000
false-positive rate            0/5 = 0.000            0/5 = 0.000
multi-key bare 'go back'       'small'                'small'
named-subject wins             'blue'                 'blue'
```

**`integrity_conditioned_recall.py`** (RAMR) — same nomic embeddings, n=100/scenario, GPU pre-flighted:

```
                        as committed (1.20.0)                    forced onto HEAD
supersession   naive 0.51 | recency 1.0 | insp 1.0 | +warrant 1.0     identical
revert         naive 0.55 | recency 0.0 | insp 1.0 | +warrant 1.0     identical
poison         naive 0.00 | recency 0.0 | insp 0.0 | +warrant 1.0     identical
```

Identical on both. **Neither published number moves.** The code paths these exercise did not change
between 1.20.0 and HEAD; the erasure paths, which did, are not what they measure.

So the honest statement is two-sided, and both sides matter:

- The exposure is **real**: a lab that measures an artifact nobody ships is the defect that cost a physics
  claim earlier this month — verifying against the wrong thing.
- The damage is **zero so far**: the two most-exposed published claims are unaffected, verified by running
  them, not by arguing that recall code "probably didn't change".

Remaining scripts are unverified per-claim. `locomo_prefix_vs_mem0`, `locomo_recall_comparative`,
`poison_defense_working`, `poison_deoracle_test` and the rest each need the same both-ways run before any
number from them is cited again.

## The fix that matters more than re-pointing the paths

Re-pointing thirteen `sys.path.insert` lines removes today's instance. It does not stop the next one: the
next script will copy the line from a neighbour, and nothing will say which library answered. The
structural fix is for a lab run to **record the artifact it measured** — path and version — alongside its
numbers, so a result that came from the wrong library says so on its face instead of needing a probe to
discover it a month later.

`agora/inspeximus_pypi/` also declares the production package name at version 1.20.0. It is not on PyPI
(`agora-inspeximus` and `agora_inspeximus` both 404, and the real `inspeximus` publishes from
`DanceNitra/inspeximus`), so nothing is shipping from it — but a stale tree claiming the live package name
is a loaded gun, and it should either be deleted or renamed.
