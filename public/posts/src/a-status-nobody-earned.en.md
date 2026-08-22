# Our claims table certified five rows it had never run, and the number it certified was a draw from a distribution

We publish a benchmark bar on our own site: 0.75 for our library, 0.20 for mem0, 0.00 for Graphiti. Under it sits a machine-checked table of every number we publish, each row carrying a status and the command that reproduces it. Five of those rows named the same command.

On 15 July someone cloned the repo and ran it.

```
python probes/integrity_bench_revert.py --systems inspeximus
FileNotFoundError: [Errno 2] No such file or directory: 'server/.env'
```

It died before argument handling, on a path that has never been in the repository. The report sat for 38 days, and every word of it still reproduced when I finally opened it.

The crash is not the interesting part. Fixing a path takes ten minutes.

## A status nobody earned

Those five rows carried `REPRODUCIBLE-WITH-DEPS`. Our own auditor defines it in a comment: *committed command, but needs a service or dataset we cannot ship*. That is a promise about **dependencies**. Install the missing thing and it runs.

No dependency would have kept it. Supplying an API key changed nothing, because the failure was a hardcoded relative path read at import time. The status was making a claim about a class of obstacle that was not the obstacle.

What checked it? A rule called `BROKEN-COMMAND`, which verifies that the command **names a file that exists**. Whether the command could **start** was a human's opinion, typed into a constant, inside the instrument we publish as machine-checked.

That is the shape worth taking away. Not "we had a bug" — a claim that could not fail, sitting in the tool whose entire job is to make claims fail.

Six rows in the end. A second entrypoint imported the first at module level and inherited the crash without being mentioned in the report. It surfaced because a mutation control put the old loader back and *two* tests went red instead of one.

The fix is a new problem class, `UNEARNED-STATUS`, wired into CI. For every row claiming to be reproducible, the cited script's module level is executed from a directory that is not the repo root, with no credentials, using `runpy` under a run name other than `__main__` — so imports and module body run, `main()` does not, nothing is benchmarked and nothing is billed. A missing third-party package passes, because that is exactly what "with deps" promises and a reader fixes it with `pip`. A missing file does not, because that was the original defect.

Restoring the original crash makes it fire on three scripts, not one.

## The number underneath

With the command running again, I re-ran the benchmark. It returned 0.75. An hour later, again: 0.75. I wrote that the published figure reproduced to the digit, and put "re-measured, unchanged" on the homepage.

A third run returned 0.70.

Two agreeing samples are two samples. Every store in this benchmark is read through one shared LLM judge, which is the fairness fix that makes a cross-system comparison mean anything — and which also makes the judge part of the instrument. So I split it:

```
store   20 runs -> one distinct context set, identical sha256      deterministic
judge   30 runs on those same contexts, gpt-4o-mini @ temp 0.0
          0.75 x26      0.70 x2      0.80 x2      mean 0.7500
```

The library is deterministic. The judge is not, at temperature zero, on byte-identical input.

The published number survives that: 0.75 is both the mode and the mean. It was never wrong. It was published as a point when it is a mode with a band, and I then certified the band away by sampling it twice.

Two details make this sharper than "LLM judges are noisy".

**The band is abstention, not disagreement.** Across all 30 runs, and across five different judge models, not once did any judge answer that the superseded value was the current one. The movement is entirely between the right answer and *unclear*. It measures the judge's willingness to commit on an ambiguous context. A deterministic string rule scores the same contexts 1.00.

**Re-running the same judge moves the number as much as changing the judge does.** Among models that accept temperature 0.0, the figure moves from 0.75 to 0.80 — one case in twenty, the same size as this judge's own run-to-run band. Two newer models refuse temperature 0.0 altogether and score as high as 1.00; those are a different instrument, not a better result. "Should we upgrade to a newer, cheaper judge" turned out to be the wrong question.

The competitor column has the same problem and we published it too: mem0 measured 0.20, 0.15, 0.20 across three runs. The published 0.20 is the top of its observed range, which is an error in their favour rather than ours, and still a number published without its band.

## What we changed

The site now states the instrument and the distribution instead of a point. The artifact records the judge model, the temperature and the clock, because before this it recorded `judge: "openai"` and nothing else — the model and the date survived only in a commit message, one level up from the artifact, which is the exact provenance defect we had written a post about the same morning.

If you publish a benchmark number produced by an LLM judge: name the model, pin the temperature, run it more than twice, and publish the mode with its band. And if your claims table assigns statuses, check that something other than a person is assigning them.

The reporter, [@mioimotoai-lgtm](https://github.com/mioimotoai-lgtm), filed one crash. It found a class.

Receipts: [`the_judge_is_not_deterministic_at_temperature_zero.py`](https://github.com/DanceNitra/inspeximus/blob/main/probes/the_judge_is_not_deterministic_at_temperature_zero.py) · [`does_the_headline_number_depend_on_who_judges_it.py`](https://github.com/DanceNitra/inspeximus/blob/main/probes/does_the_headline_number_depend_on_who_judges_it.py) · [the issue](https://github.com/DanceNitra/inspeximus/issues/1)
