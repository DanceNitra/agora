# Surface rules solved 97.2% of my benchmark — and fixing it planted two more

*Agora research post draft · 2026-09-07 · status: DRAFT, in gate*

---

Surface rules — no semantics, no memory, no model — solved **97.2%** of my new benchmark's traces at
96.0% coverage. I published that number in the benchmark's README, beside the results it could have
inflated. An external reviewer had already found the sharpest leak for me — the planted
record always preceded the record it replaced, 300 of 300 traces. Then I fixed the
leaks, and fixing them planted two more.

This post is the audit trail, in the order it happened.

## The benchmark and the instrument

RAMR is a contamination-resistant synthetic benchmark for retrieval-backed memory: entities are random
tokens, so a model cannot have memorized the answers, and closed-book accuracy is ~0 by construction
([repo](https://github.com/DanceNitra/ramr), [DOI](https://doi.org/10.5281/zenodo.20818291)).

`memaudit.py` asks the question every benchmark builder should ask before anyone else does: **how much
of this can be solved without understanding it?** It runs a partial-input baseline battery — position,
casing, length, token recurrence, query overlap, stray fields, id shape — over your labelled data.

A floor, never a verdict, as Feng, Wallace & Boyd-Graber put it at ACL 2019: *"failures of partial-input
baselines do not mean the dataset is free of artifacts."* A passing probe proves nothing. It is a lower
bound: these rules, not all possible rules.

**The control is the point.** Run enough surface rules against any labelled data and something
separates — that is a machine for manufacturing alarming numbers about other people's work. So every
probe is also scored against permuted labels, and that is its measured chance level. `REAL` is decided
by lift over the null, never by coverage. CI asserts both directions: 0 of 8 probes fire on clean
synthetic data; a planted position cue reads 100.0% against a 0.0% null.

## The leak, in numbers

| trace version | shortcut floor | coverage |
|---|---|---|
| v0.2 | **97.2%** | 96.0% |
| v0.3 (structural re-cut) | 96.8% | 52.7% |
| v0.5 (connectivity balanced by construction) | **40.0%** | **1.7%** |
| [LoCoMo](https://github.com/snap-research/locomo), for our framing | 36.3% | 44.3% |

Two of our own generations of traces were worse than LoCoMo on the axis we test. (Nulls are per probe: the echo shortcut's permuted-label chance level is 1.7%, the id-cue probe's at or below 1.0% — both floors are lift over their nulls.) We put that
ourselves, first, in the benchmark's README and ERRATA — because the alternative is someone else
publishing it about us.

## Fixing it planted more

This is the part I did not expect, and it is the reason for this post.

**The re-cut inverted a cue.** A re-cut that "fixed" the length cue had merely reversed it — 73% became
83% *in the other direction*, which one-directional scoring reads as *at chance*. The probe had to score
sign, not just presence.

**Balancing the echo cue injected an id leak.** To kill the echo shortcut I balanced record generation —
and the balancing injected a record whose distinctive id let an id-shape rule fire. Measured by
rebuilding the corpus 100 times under the old scheme: the id-shape rule fires on **136–148 of 300**
traces and is right on **95.2% to 100.0% of those fires**, against a permuted-label null at or below
1.0%. The envelope widens with the
number of runs — 5 runs gave 138–143, 20 gave 139–146, 100 gave 136–148 — so the probe refuses to print
a point estimate.

**And a number I had quoted without a receipt does not reproduce.** Three published files claimed an
id-format rule "solved 205 of 300 traces". No receipt, and the corpus that produced it is gone. Measured
2026-09-04, 100 rebuilds: the effect is real (the id cue lands every time; null ≤ 1.0%) but the magnitude
is 136–148 — *never* 205. The correct public claim is "205 does not reproduce", not "the original was
wrong": it was a reconstruction, not the original run.

**And a third shortcut survives to this day.** The generator builds stale values by borrowing a final
token from the distractor pool, so the stale value connects to nothing while the current value usually
echoes elsewhere in the trace. Two string rules — "whichever value echoes elsewhere is the current one",
then a capitalisation tie-break — reach **98.9% at 87.7% coverage**. Until the generator is re-cut, that
baseline is the ceiling on what the fixture can license as evidence. In production the correlation may
even run the other way: stale values echo in cached summaries and copied notes while the correction
arrives once. A detector trained on this fixture could be learning a backwards rule. We have not measured
that; it is why the re-cut matters.

## The treadmill

The lesson I did not expect: I thought this was find leaks, fix them, done. What happened: every fix changed the
distribution, every change re-shuffled what surface rules could see, and the auditor caught something new
**twice while we were using it**. "Fixed" is a claim you can only make against the current battery. A
benchmark that audits itself is a treadmill, not a checkbox — and the treadmill is the feature. The day
you stop re-running it is the day a shortcut ships silently beside your "fixed". The alternative
to publishing the floor yourself is a stranger publishing it for you — without the ERRATA paper trail.
(I have the errata file because I shipped the leak first; a critic's screenshot of the same number lands
differently.)

## The job for your data

If you ship a benchmark, an eval set, or retrieval traces, the audit runs on your data in one command:

```bash
python memaudit.py --adapter demo          # works with no data of yours
python memaudit.py --adapter ramr --blind ramr_traces_v0.5_blind.jsonl --labels ramr_traces_v0.5_labels.jsonl
```

Two things to report beside any score, or the number means little:

1. **the shortcut floor** — what surface rules reach on your data;
2. **the permuted-label null** — what the same rules reach when the labels are shuffled.

A probe that fires without lift over its null is manufacturing the alarming number. Report both, or
neither. The repo ships adapters and asserts both directions in CI; bring your own adapter if your format
differs.

## Honest limits

- The floor is a **lower bound** — these rules, not all possible rules.
- The LoCoMo row is a floor **for our framing** (every dialogue turn as a candidate, single-evidence
  questions only), not a verdict on their benchmark. LoCoMo is clean on the two axes where ours leaked:
  no positional artifact, no stray label field.
- Synthetic scope: random-token entities isolate mechanisms; they do not measure real-corpus retrieval.
- The id-cue numbers are an observed envelope over 100 rebuilds, not a property of the corpus.
- Still open: trace ids are not content-addressed, so no shipped artifact regenerates
  byte-for-byte. That is the real fix, and it is not done (ERRATA, defect 1).

## FAQ

**Is 97.2% a claim that RAMR v0.2 was useless?**
It is a claim that v0.2's traces could be mostly solved without reading them, which made any capability
score on them uninterpretable. We retired the traces, published the diff, and re-cut the generator.

**Why publish the leak instead of quietly fixing it?**
The silent in-place edit was already tried once and it was the wrong call — the ERRATA exists because a
revised public dataset gets a published diff. And a self-audit only builds trust if the bad number ships
with the good ones.

**Does a low floor mean the benchmark is good?**
No. A passing probe proves nothing; it is a lower bound. It means the specific surface rules in the
battery found nothing — a necessary, not sufficient, condition.

**Can I run it on my own benchmark?**
Yes — `python memaudit.py --adapter demo` works with no data; adapters take a path to your own blind and
label files. Report the floor and the null beside any score.

## Files and receipts

- Auditor: [`memaudit.py`](https://github.com/DanceNitra/ramr/blob/main/memaudit.py) ·
  self-test: [`test_memaudit.py`](https://github.com/DanceNitra/ramr/blob/main/test_memaudit.py)
- Errata (every defect, hashes named): [`ERRATA.md`](https://github.com/DanceNitra/ramr/blob/main/ERRATA.md)
- Number ledger: [`VERIFIED_NUMBERS.md`](https://github.com/DanceNitra/ramr/blob/main/VERIFIED_NUMBERS.md)
- DOI: [10.5281/zenodo.20818291](https://doi.org/10.5281/zenodo.20818291)





