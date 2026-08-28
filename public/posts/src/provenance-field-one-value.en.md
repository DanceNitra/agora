# Two stores in the same product: one provenance field has 8 distinct values across 217,549 records, the other has 101. Neither FIELD resolves.

**Correction, 28 August 2026.** That last clause used to read "Both resolve to nothing", and it
was wrong about the coding store. u/perseus-computing found that the resolver behind these numbers
never made a request. Fixing it properly meant asking the question of the whole record instead of
one field, and the answer changed: in that store 168 of 174 sourced records carry a locator that
retrieves, and the `meta.sha` + `meta.files` pairs resolve inside the tree of their own commit 426
times out of 432. The provenance was there. It sat one key away from the field I was auditing, and
a field-scoped audit reported zero over it. The column below called `re-checkable` is relabelled
`addressable`, which is what it measured; its zeros are unchanged. The eight agent stores are
unchanged too: nothing resolves there at either level. Detail in the update at the foot of this
piece.

I ship an agent memory layer. It has a `source` field, and I have quoted its coverage in public. Last
week I re-measured before citing it to someone and the number had moved, so I went looking.

Eleven live stores, 235,055 records, `source` populated on 92.63%. These are live stores that grow while you measure them, so the totals are a snapshot and the receipt is stamped; the figures that matter here are the ones that do not move. That aggregate hides two write
paths that fail in opposite directions.

```
store group          records   src %  distinct  distinct/sourced   addressable
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

*Two turned out to be too few. See the update below, which is where the ask now stands.*

The probe is one file with no dependencies and it prints both controls, including the resolver check
that has to pass before it will report anything:
[`a_provenance_field_at_100_percent_with_one_distinct_value.py`](https://github.com/DanceNitra/agora/blob/main/probes/a_provenance_field_at_100_percent_with_one_distinct_value.py).
If your store format differs, the check is `sum(1 for r in records if resolves(r.source))` and you
don't need my code for it.


## Update, 26 August: two readers moved the measurement

Three people replied on r/RAG and two of them changed what I think the right number is.

**Terrible_Front_583 split "source coverage" into three things I had been treating as one:** field
presence, semantic provenance, and fetchability, with the gate requiring a resolvable source object
plus snapshot or version, owner, and an access check. That is better than my two integers, and my own
data agrees with him inside one query: presence is itself two numbers. In my coding store the
`source` key is present on every one of the 20,162 records in the stamped receipt and carries a
value on 145 of them, 0.72%. A
schema check sees the first number. Coverage, computed the way I was computing it, sees the second.
Neither of them is what I published.

The rest of that tier I cannot score at all. Neither of my schemas has a snapshot, a version, an
owner, or an access field, so for me that layer is not zero, it is unmeasurable. That is a worse
place to be than a bad score, and no coverage percentage will ever show it to you.

**arupbuildsai pointed out that there are two audits here rather than one:** does the source resolve,
and does it support the claim. He ran the second on a production RAG assistant whose citations also
looked healthy, and found the answers wrong around 35% of the time while sounding certain, the
citation often decorating a claim its source never made; moving chunking from size-based to
header-based to semantic brought that to roughly 8%. My probe can only ever test the first half. It
fetches, it never reads, so a source that resolves to a page contradicting the claim passes it clean.
The second half already has benchmarks: ALCE scores citation precision and recall directly (Gao et
al., [arXiv:2305.14627](https://arxiv.org/abs/2305.14627)), and AIS is the earlier framing (Rashkin
et al., [arXiv:2112.12870](https://arxiv.org/abs/2112.12870)).

**And the number moved again, which is the one thing this post predicted about itself.** Re-run
today: 240,715 records across the same eleven stores, `source` populated on 91.15%, re-checkable 0.
That is 5,660 records more than the table above, and every total in it is now stale. Re-checkable has
been 0 at every measurement since this post went up; the count I still cannot explain is the 24 from
10 August.

So the ask is three counts rather than two. How many records you have, how many carry a source value
at all, and how many of those resolve to something a reader can fetch. The third is the one that can
fail.

---

*Distinctness is now reported by `check_sources()` in inspeximus 2.20.0, beside coverage and beside
the re-checkable count, and documented as a detector for one degenerate shape rather than a measure of
traceability — because of the counterexample above.*


## Update, 28 August: the resolver never made a request, and the headline was wrong

u/perseus-computing ran the published probe against `https://example.invalid/...` and it came back
re-checkable. He was right, and the function was worse than his report: a prefix test plus an
`os.path.exists`, so it never issued a request at all, and the bare string `https://`, a scheme with
no host, passed it too.

It is two functions now. `addressable` is syntax. `retrieves` opens the file or issues one GET and
takes only a 2xx. The control is his suggestion, a local server answering 200 on one path and 404 on
another, and it runs the same fixture the corpus goes through rather than the function on its own.

The first attempt at that fix is the more useful mistake. It added the retriever, gave it the
control, and left the scan calling the old function, so the retriever passed its own test without
ever seeing a record of the corpus.

**Then a hostile re-run of my own numbers killed the headline.** The audit was scoped to the field
named `source`, and I had read a zero over that field as a zero over the records. Every figure in
this paragraph is from the receipt stamped `2026-08-27T22:03:30Z`, and they move: by the time the
reply to him was written, twenty minutes later, the first pair read 170 of 176 and the second 441 of
447. A provenance count without a time on it is the same class of mistake as the one this post is
about. In the coding store 168 of 174 sourced records carry a locator that retrieves. The `meta.sha` and `meta.files` pairs
resolve inside the tree of their own commit 426 times out of 432, and all 171 distinct shas are real
commits. The provenance was there the whole time, one key away from the field I was auditing.

There is a caveat I only found by asking the right question. Of those 171 commits, 161 are reachable
from public main. Ten are not, so ten of those references are re-checkable by me and by nobody else,
which for a claim published to strangers is a different kind of zero.

What survives: the eight agent stores, 220,417 records, eight distinct values, and nothing that
resolves at either level. That is the case the post was making and it is untouched. What does not
survive: the coding store as the second example. Its records were the counterexample I had been
holding up, and they resolve.

The instrument was the problem in both directions, so it is worth naming what changed in it. The
control fixture used string sources while every record in the real corpus is an object, and mutating
the reader to ignore objects takes coverage from 90% to 0.00% with the control still green. The cap
on retrievals counted local file opens, so it bound at 200 with 148 locators untried and reported the
undercount as a result. Non-addressable strings were being counted as network attempts, 169 of them
on a run that never opened a socket. And the receipt now carries a `measured_at`, because the record
count moved four times in one session and the record-level figure went 167 to 168 in five minutes.

A companion file breaks the probe seven ways and fails if any mutation survives, including the defect
he reported and both directions a retriever fails in. Yes-to-everything passes a 200-only check.
No-to-everything passes a 404-only check, and no-to-everything is not hypothetical: an earlier
version had it, and its answer was zero, which is also this post's headline.


## Update, 28 August, second correction: I made the post's own mistake inside its correction

The correction above says the provenance was there and I had audited the wrong field. An adversarial
re-run of that correction says it is too strong, in the same direction as the error it corrects.

`meta.files` is `git show --name-only` of `meta.sha`. Measured: **450 of 450** cited paths are files
that commit itself changed. So the pair records what the write PRODUCED, not the document the memory
came from. In the vocabulary this post is built on, that is `wasGeneratedBy`, not `wasDerivedFrom`.
The post's whole argument is that we recorded attribution and read it as derivation, and I did it
again one layer down, while correcting it.

Three more things the same pass found, all of which narrow the claim:

The record-level number is my own artifact. `record_locators` reads eight keys, and every one of the
170 records rides on a single one, `meta.files`, which I added to that list after looking at the
data. Drop it and the count is 0. The seven others contribute nothing, and a store keeping its
reference under `citation`, `origin` or `ref` scores zero here.

The commit-specific check earns less than it looks. Resolving the pair inside its own commit gives
444 of 450. Asking the sha-blind question, does this path exist in the repository today, gives 426 of
450. The sha buys four percentage points.

And the denominator was inflated. The finding covers 170 records in one store: 0.07% of the 243,985
in the corpus, not a fact about eleven stores.

There is prior art for the error and I should have cited it in the first correction rather than the
second. Column completeness is named in Pipino, Lee and Wang, *Data Quality Assessment*, CACM 45(4),
2002, alongside schema and population completeness; Scannapieco and Batini set out value, tuple,
attribute and relation completeness in 2004. Measuring a column and reporting it as a property of the
record is the textbook case, not a new failure mode. What is ours is only the specimen and the
runnable probe.

One more, and it is the worst of them, because it is in the artifact this post invites you to run.
Point the probe at a store that is not shaped like ours and it prints seven green controls, then
`no item list`, then `FAIL -- no stores read; nothing was measured`. A healthy-looking instrument
that never reached its target, in the file whose subject is healthy-looking instruments that never
reach their target. That is being fixed; until it is, the invitation only works for stores that
already look like mine.
