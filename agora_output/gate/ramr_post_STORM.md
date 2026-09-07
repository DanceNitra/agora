# STORM pass — RAMR memaudit post (2026-09-07, pre-audit briefing)

Four perspectives on the draft before the adversarial audit. Each names its strongest attack.

## 1. Benchmark author (peer who ships an eval)

**Attack:** "You made a leaky benchmark, fixed it, and now sell the fix as content. The 40% v0.5
floor is still HIGH — your benchmark still licenses 40% right-by-rote, and LoCoMo comparison is
framing-gamed."
**Check:** Does the post claim v0.5 is clean? — No: it reports 40.0% with 1.7% coverage, calls the
LoCoMo row "for our framing", and states the echo shortcut still survives at 98.9%/87.7% (the ceiling
on what the fixture licenses). The treadmill section explicitly says "fixed" only ever means against
the current battery.
**Verdict:** attack lands only if the reader stops at the TL;DR. The body pre-commits the concessions.
**Fix:** none needed, but the TL;DR table should not sit alone — it already links Limitations. OK.

## 2. Eval skeptic (methods reviewer)

**Attack:** "memaudit is a battery of weak baselines; passing it says nothing (you admit it); and your
chance-level control via label permutation may be too weak — some surface rules could exploit
structure that survives permutation."
**Check:** The post quotes Feng et al. (lower bound), states pass-proves-nothing, and defines REAL by
lift over the permuted null. The permutation preserves set size/text/order and moves the label — the
author's measured chance level, not a theoretical one. Residual weakness: a rule exploiting label
POSITION distribution might survive permutation (positions are preserved). The post's example — a
planted position cue reads 100% vs 0% null — shows position cues DO get caught... because the planted
cue breaks position/label independence. Honest residual: permutation-null may not catch rules keyed to
per-instance metadata that correlates with the label through the generator, not through the label field.
**Verdict:** the post's claim survives because it never claims completeness — lower bound, explicitly.
**Fix:** add half a sentence naming this residual? — the Honest limits already say "these rules, not
all possible rules". Sufficient.

## 3. The audience being recruited (eval/benchmark builders, RAG engineers)

**Attack (as incentive question):** "Why would I publish my floor? It hands attackers ammo and
embarrasses the project."
**Check:** The post's own answer: the silent edit was tried and it was wrong; a self-audit ships the
bad number with the good ones; the ERRATA norm. Plus the practical: report floor + null or neither.
**Verdict:** incentive framing is present but thin — the job-for-reader section covers mechanics, not
motivation. Could add one line on the field norm (citing the auditor caught us twice = credibility
asset). The S4 loss-up-front already does this implicitly.
**Fix:** optional — one sentence in "The treadmill" about the alternative (a stranger finds it for
you, without the ERRATA norm). Worth adding.

## 4. Hostile reader (competitor/vendor framed as target)

**Attack:** "This is self-flagellation as marketing — you leak, you fix, you post. And the LoCoMo
comparison is dressed as humility while implying their benchmark has a 36.3% problem."
**Check:** The post hedges LoCoMo three separate times (framing, not verdict; clean on the two axes
where ours leaked). The self-flagellation charge is the genre — the distribution playbook's evidence
says the null-in-first-person format is what earned engagement. The post never names a product and
never claims RAMR is good BECAUSE of the audit.
**Verdict:** survives; the hedge density around LoCoMo is the defense.
**Fix:** none.

## Summary of fixes to apply
1. (P3) One sentence in "The treadmill": the alternative to publishing the floor yourself is a
   stranger publishing it for you — without the ERRATA paper trail.
