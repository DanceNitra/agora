# Temporal admissibility — candidate vendor-neutral fixtures

**Status: CANDIDATE. Proposed to nobody yet, accepted by nobody.** Drafted from the six boundaries
[@safal207](https://github.com/safal207) named on
[anthropics/claude-code#34556](https://github.com/anthropics/claude-code/issues/34556) on 2026-08-17,
which folded in the two [@Stratogain](https://github.com/Stratogain) proposed the evening before.

**Authored by an interested party.** inspeximus wrote these cases and is one of the implementations
they grade. Nothing here is independent evidence about inspeximus. A separate producer must validate
both the implementations and this fixture.

## The invariant

> historical evidence may remain valid without being admissible evidence for the current session,
> current world-state, or current use.
>
> — @safal207, #34556

The implementations can stay completely different — the systems that produced these failures include
a Python store, a JS hook ledger and a hook-based collector. **What should interoperate is the
falsification surface**, so that is the only thing specified here: a closed vocabulary of reasons, a
closed vocabulary of surfaces, and six histories expressed as plain data.

## What is in here

| File | What it is |
|---|---|
| `admissibility-cases.json` | Six failure cases, each with a paired non-failure control; one also carries a discrimination case. Plus the reason vocabulary, the surface vocabulary, and the degradations each case must fail under. |
| `run_admissibility.py` | The runner. Enforces five rules on the fixture itself before reporting any score. |
| `inspeximus_binding.py` | Our adapter — about 100 lines, all of it translation. |
| `naive_binding.py` | An ordinary store with no temporal admissibility. It **must** score 0/6. |
| `admissibility.result.json` | Raw output of the last run. |

## Results

```
inspeximus                6/6
naive-store (must fail)   0/6      passes every control, detects nothing
```

**Read the second line first.** A fixture set scored by the party that wrote both halves is the exact
arrangement in which everything passes and nothing is measured, so the number that makes the first
line mean anything is the second. The naive store is not a strawman: it records text under a key,
keeps the locator, and stores a digest **at write time** — which feels like provenance and answers a
different question. It passes every control (it never cries wolf) and detects none of the six.

## The six

| | Case | From |
|---|---|---|
| T1 | Same locator, different observed bytes | @safal207 · found in two ledgers independently |
| T2 | Same locator and digest, different session | @Stratogain, who measured `OBSERVED_FRESH` on a file the session had never read |
| T3 | Honest capture, later source drift (+ discriminates drift from orphaned) | @safal207 |
| T4 | Verified state, changed before use | @safal207 · built independently by two of us the same evening |
| T5 | Collector stops while coverage stays healthy | @Stratogain |
| T6 | The identifier written is not the identifier queried | @Stratogain, whose hook stored `session_id.slice(0, 8)` and compared the full id |

## The five rules the runner enforces on its own fixture

Each comes from a defect we shipped or nearly shipped, and all five run before any score is printed.

1. **No expectation without a citation.** An earlier conformance harness of ours derived expected
   verdicts by splitting case names on a hyphen and scored five false failures against a
   specification's own fixtures.
2. **No case without a paired control.** @safal207's condition. `cries_wolf` — inadmissible for
   everything — passes every failure case, so without controls the set is satisfiable by a detector
   that is simply broken in the reassuring direction.
3. **No fixture that has never failed.** Each case names degradations that must break it, and they
   are applied. A case surviving `always_admissible` is measuring nothing.
4. **No case that never reached its subject.** `reaches` is checked against what the binding reports
   consulting. A suite that cannot tell *the property holds* from *the case never arose* has measured
   nothing.
5. **No control that is secretly a second failure case.** A control must expect `admissible: true`.

**Rules 4 and 5 caught this fixture on its own first run**, which is the only reason they are worth
stating. Two of the six shipped with a "control" that expected *inadmissible* — a second failure case
wearing the control's name, which `cries_wolf` sailed through. One case expected `admissible`, so no
degradation could break it; it had to be inverted to its failing direction. And every `reaches` value
was free prose, so no foreign implementation could have known what to report — the surface vocabulary
exists because of that.

## Running it against your own store

Implement six methods. No inheritance, no dependency, no import of anything here.

```python
class YourBinding:
    name = "your-store"
    def setup(self, workdir):                          ...  # -> handle
    def observe(self, h, *, doc, bytes_, session):     ...  # a session read these bytes
    def write(self, h, *, key, text, source, session): ...
    def mutate_source(self, h, *, doc, bytes_):        ...  # the world moves
    def delete_source(self, h, *, doc):                ...
    def verify(self, h, *, key, session):              ...  # your pin/checkpoint, if you have one
    def assess(self, h, *, key, window, session):      ...  # -> {admissible, reason, consulted}
```

```
python run_admissibility.py --binding your.module:YourBinding
```

`reason` must be one of `reason_vocabulary` or `null`; `consulted` uses the keys of
`surface_vocabulary`. Return whatever richer detail you like internally and map it onto exactly one
code — **that mapping is the interoperable surface**, and writing it down is most of the value.

## What a pass is not

A pass is not a certificate, and 6/6 is not a claim that a store is correct. These cases measure one
narrow thing: whether an implementation can distinguish evidence that is *valid* from evidence that
is *admissible now*, across six boundaries that six people hit in production. The set is candidate,
partial, and authored by an interested party.

Corrections, additional cases, and a binding that fails one of these are all more useful than
agreement.
