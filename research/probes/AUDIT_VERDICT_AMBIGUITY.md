# `unaudited` means two different things, and one of them is bad news

**Measured 2026-07-29** on the published 1.87.0 wheel (routed-correction defect present) against local HEAD
(fixed). Read-only.

## What was tested

Whether `erasure_audit` — the surface built to answer "did anything survive that still carries the erased
material?" — would have caught last night's finding: a correction written through `route()` that survived
the subject's DSAR while holding their **current** value.

## What it actually did

| | published 1.87.0 (defect) | local HEAD (fixed) |
|---|---|---|
| `erased` | 1 | 2 |
| CURRENT value left in store | **True** | False |
| `erasure_audit` verdict | `unaudited` | `unaudited` |
| residue items | 0 | 0 |
| with `values=` supplied | advisory `value_possibly_recoverable` | advisory empty |
| `coverage.records` | 1 | 0 |

## The honest reading

**The audit did not falsely certify anything.** `unaudited` is not a pass — it is the documented,
deliberate "I inspected nothing", and it was returned correctly: the routed correction declared no lineage,
so there were no edges to walk. The surface behaved exactly as its own honest-scope note says it will.
Reporting this as "the audit certified an erasure that left data behind" would be false.

Two real weaknesses remain, and neither is the dramatic one:

**1. The same verdict covers a completed erasure and an incomplete one.** Both columns say `unaudited`.
An operator reading the verdict alone cannot tell "nothing survived, nothing to inspect" from "something
survived and I cannot see it". The only thing that separates them here is `coverage.records` — 0 versus 1 —
which is not what the verdict field is for. A field that returns the same value in the good case and the
bad case carries no information at the moment it is needed most.

**2. The one signal that WOULD have caught it is advisory-only and opt-in.** With `values=["9 Oak Ave"]`
the audit does surface `value_possibly_recoverable`. But the caller has to know to pass the erased values,
and nothing prompts them — `forget_subject` already knows exactly which values it just erased and does not
offer them to the audit. That is a join the library could make and does not.

## The constructive version

The store has the information both weaknesses need:

- `forget_subject` returns the ids it erased; their values are the natural `values=` argument for a
  follow-up audit. Handing them over automatically turns an opt-in heuristic into the default check.
- The verdict could distinguish "nothing left that is attributable to this subject" from "nothing
  declared, so nothing inspectable" — the coverage block already holds the difference.

Neither is a data-loss fix, so neither belongs in a hotfix. Both are worth doing before the compliance
story is sold harder, because the surface an auditor reads is the surface that has to be legible when the
answer is bad, not only when it is good.

## Method note

The first framing of this probe was going to be "our own audit certified the residue". It did not, and the
measurement said so. Recorded because the wrong version of this finding would have been more dramatic and
completely false — the same failure mode as the red-team panel's namespace claim, which measured a stale
vendored copy and reported a catastrophe that does not exist on any shipped build.
