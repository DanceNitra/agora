> **QUEUED FIX** — found 2026-07-29 ~03:30 while the mutation gate was running, so the repo was off
> limits. Recorded here in full so the fix is a five-minute job and not a re-derivation.

# The echo branch of `route()` has the defect the correction branch had

Last night's fix made a routed CORRECTION declare the record it corrects, so `forget_subject` reaches it.
`route()` has other branches that write, and I fixed one. The echo branch still writes an unattributed
record holding the subject's data.

## Measured

```
remember("alice addr is 5 Elm St", key="a::addr", object="5 Elm St", source={"doc": "hr/alice"})
route("actually alice moved to X", key="a::addr", object="X")            # correction — FIXED, declares a parent
route("alice addr is 5 Elm St and 9OakAve", key="a::addr", object="5 Elm St")   # restatement -> intent 'echo'

store:
  [superseded] src=hr/alice  df=None            'alice addr is 5 Elm St'
  [active]     src=None      df=['c27f06e35c']  'actually alice moved to X'      <- reached, fixed branch
  [superseded] src=None      df=None            'alice addr is 5 Elm St and 9OakAve'   <- the echo record

forget_subject('hr/alice')  ->  erased = 2
survivors: ['alice addr is 5 Elm St and 9OakAve']
```

The echo record carries the subject's address verbatim and nothing connects it to her. Same shape as the
correction defect, one branch over.

## It was caught by the feature built an hour earlier

```
residue_in_store: {ok: false, checked_records: 1, searched_values: 3,
                   findings: [{id: 241b435d41, field: "text",   fingerprint: 4016c1ad3454},
                              {id: 241b435d41, field: "text",   fingerprint: 0c5f28a9037f},
                              {id: 241b435d41, field: "object", fingerprint: 4016c1ad3454}]}
```

That is the in-store residue check doing exactly what it was built for, on a defect nobody was looking
for. Worth noting because the feature was justified on a hypothetical and immediately paid.

## The fix

`route()` writes at four sites. Only the correction/assert one was given provenance:

| line | branch | state |
|---|---|---|
| ~4446 | `object is None or key is None` | no source, no parent — **but there is no key, so nothing to derive from**; caller's `source=` is the only lever |
| ~4456 | correction / assert on a known key | **FIXED** — declares `_current_active(key)` |
| ~4467 | reaffirm (`policy='trusting'` / context-aware) | unattributed — it restates a value ON A KEY, so the same parent is available |
| ~4471 | echo, guard on | unattributed — same |
| ~4473 | echo, guard off (keyless write) | deliberately keyless so it cannot LWW-clobber; a `source` still applies |

The correction fix's argument transfers unchanged: a restatement or reaffirm of a value on a key is *about*
whatever that key already holds, and `route` knows which record that is. Pass `source` through on all of
them, and declare `_current_active(key)` as the parent wherever a key exists.

## What NOT to do

Do not infer a subject from the key string (`alice::addr` → `hr/alice`). Inventing a data subject nobody
supplied is the failure this month produced twice, and every control in the erasure tests exists to stop
it. Where there is no key and no caller source, the record stays unattributable and `attributable: false`
says so — that is the contract, not a gap.

## Method note

My first probe reported `leaks=True` on two `assert` arms as well. That was the PROBE being imprecise: it
searched for a marker string anywhere in the store, and on those arms the marker was never in an erased
record, so there was nothing for the residue check to compare against. `residue_ok=True` was correct on
both. Only the echo arm is a finding, and it is a finding because the check itself said so.
