# Two stores in the same product: one provenance field has 8 distinct values across 217,549 records, the other has 101. Both resolve to nothing.

I ship an agent memory layer. It has a `source` field, and I have quoted its coverage in public. Last
week I re-measured before citing it to someone and the number had moved, so I went looking.

Eleven live stores, 235,055 records, `source` populated on 92.63%. These are live stores that grow while you measure them, so the totals are a snapshot and the receipt is stamped; the figures that matter here are the ones that do not move. That aggregate hides two write
paths that fail in opposite directions.

```
store group          records   src %  distinct  distinct/sourced  re-checkable
eight agent stores   217,549  100.00%        8          0.000037             0
one coding store      16,215    0.63%      101          0.990196             0
```

**The agent stores** are stamped by one automated writer. `agent:scholar` appears in all 26,928
records of one of them; `agent:guard_r` in all 27,294 of another. Eight stores, eight distinct values,
one each, and each is the name of the process that did the writing.

**The coding store** looks like the opposite and much healthier: 101 distinct sources over 102 sourced
records, distinctness 0.99. Nearly every record points somewhere different.

Both columns resolve to **zero**. Not "few". Zero, across all 235,055 records, against a resolver I
can demonstrate works.

## Why the obvious metric doesn't save you, and I have the proof in my own data

The reflex when you see one constant value in a column is to reach for distinct-over-rows. That is a
real, named metric — column **Distinctness** in AWS Deequ, uniqueness in Abedjan, Golab & Naumann's
profiling survey, `expect_column_proportion_of_unique_values_to_be_between` in Great Expectations.
ydata-profiling raises `CONSTANT` automatically when distinct = 1. A profiler would have caught the
agent stores in one pass. Nobody ran one on an agent memory store, including me, which is its own
small finding about this corner of the field.

But distinctness would have passed the coding store at 0.99, and the coding store is exactly as
useless. Its sources look like `git:162de50e1702` — real commit SHAs, genuinely distinct, and not a
path or a URL, so nothing can follow them.

I did not have to construct that counterexample. It was sitting in the same product as the first one.

**High cardinality is not traceability.** Fill the column with a UUID per row and you score a perfect
1.0 while nothing resolves. Distinctness is a good detector for one degenerate shape and blind to the
next one over.

## What W3C already said in 2013

PROV-DM separates **`wasAttributedTo`**, the agent responsible for an entity, from
**`wasDerivedFrom`**, the entity it came from. My agent stores record attribution. My coding store
records a commit, which is closer but still not the artifact. Both get read as derivation, because
both live in a field called `source` behind a number called coverage.

The vocabulary to avoid this has been normative for thirteen years, and I still built it wrong.

## The number I should have been publishing

Not coverage, and not distinctness. **How many records have a source that resolves to something a
reader can actually fetch.**

For me that is 0 of 235,055.

That number can fail, which is the whole point of it. So it needs a control, and this is the part I
got wrong first: a resolver that returns `False` on everything reports zero re-checkable over any
corpus and looks identical to a corpus with none. The probe now writes a real file and an https URL
and refuses to report a finding unless both come back re-checkable.

## What I still can't tell you

**Whether it decayed or was always zero.** On 10 August I published 210,499 records at 98.3% coverage
and 0.01% re-checkable — 24 records whose locator resolved. Today it is 0. I did not keep those 24
ids. Denominator growth cannot explain a count going 24 → 0, so the real candidates are a resolver
regression, a changed store set, or those rows being rotated out, and I can rule out none of them.
That is a measurement-discipline failure and it is mine.

**Whether 0 is normal.** I have one system. I have no distribution to put it in, which is why the ask
below is a number and not an argument.

## The ask

If you run a memory layer, a RAG store, or an agent framework with a provenance field: **count the
records whose source resolves to something you can fetch, and post that count with your total.** Two
integers.

Not the coverage percentage, and not the distinctness ratio. I have both of those and they told me
nothing. The one that told me something was the one that came back zero.

The probe is one file with no dependencies and it prints both controls, including the resolver check
that has to pass before it will report anything:
[`a_provenance_field_at_100_percent_with_one_distinct_value.py`](https://github.com/DanceNitra/agora/blob/main/probes/a_provenance_field_at_100_percent_with_one_distinct_value.py).
If your store format differs, the check is `sum(1 for r in records if resolves(r.source))` and you
don't need my code for it.

---

*Distinctness is now reported by `check_sources()` in inspeximus 2.20.0, beside coverage and beside
the re-checkable count, and documented as a detector for one degenerate shape rather than a measure of
traceability — because of the counterexample above.*
