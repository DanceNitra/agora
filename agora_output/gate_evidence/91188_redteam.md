# stress-claim on the #91188 reply, run before the rewrite

Four adversarial lenses ran against the CLAIM and its measurement, not against prose. Every severe
finding was then re-checked against the primary source rather than accepted.

## What the panel found, and what survived my own check

1. REDUNDANCY (severe, upheld). Our own #82056 comment 5366420966 already published both halves of
   the unit finding: "the same mirrored file computes it as `const byteCount = trimmed.length`,
   which in JavaScript is UTF-16 code units" and "the warning then divides those by 1024 and calls
   the result KB". @tonydzi carried it into #91188 the same day, crediting us. The draft's first two
   paragraphs were telling a collaborator what he had just told the thread. CUT.
2. FABRICATED FIGURE (severe, upheld by the verification probe, not by the panel). The earlier draft
   attributed "24.4KB" to @niels-roest. It appears nowhere in that thread. It is the rendering of
   the cap itself, 25000/1024, which I had carried over from #82056. Removed, then re-derived from
   the formatter and stated as what it is.
3. INFERENCE SOLD AS OBSERVATION (severe, upheld). "Which cap is binding is already computed; it is
   the label that does not reach you" was refuted by code 2 kB from the code it described: the
   sibling path reads `d.dimension` outright, and `capDesc` renders `200-line` or `24.4KB`, so the
   label does reach the user. The sentence was inverted rather than softened.
4. IGNORED QUESTION (severe, upheld, and MY SUMMARY OF IT WAS WRONG). I wrote here that @tonydzi
   and @pm25coder "each asked" about a ~22KB target and that neither could answer. Both halves are
   false, and verify-claims caught them by reading the thread by author. @tonydzi asked
   @niels-roest, whose figure it is; @pm25coder answered about his OWN number and wrote in that
   thread that the ~22KB figure "belongs to the issue author, not me". The question is still open
   for the issue author. The draft now says exactly that, and the verification probe is keyed to
   the author of each comment rather than to words appearing anywhere in the thread.
5. OVERCLAIM (upheld). "No wc invocation can ever agree with it" is false for an ASCII index, where
   dividing by 1024 reconciles exactly. Cut.
6. HEDGE ON THE 17.1 DERIVATION (raised, then superseded). A lens showed 102 integers render "17.1"
   under x/1024, so the value was identified but the mechanism was not. Superseded by reading the
   source: `targetDesc:Ut(Math.floor(e.byteCap*HUn))` with `HUn=0.7` and `MU=25000` is the mechanism,
   traced rather than inferred. Independent confirmation of the formatter: our own environment
   reports 24.9KB for an index of 25,463 units, and 25463/1024 = 24.87.

## Boundary the draft now states

win32, CLI 2.1.257, read out of the shipped bundle by string search rather than traced in a
debugger. Every string asserted is paired in the probe with a near miss that must be absent.

## Verdict

REFRAME, applied. The draft was rewritten around what the source shows and what only we can
contribute, and the redundant material was removed rather than reworded.
