# Humanizer skill pass — drafts/camel_4206_authority_invariants.md

Skill: `.claude/skills/humanizer` (project skill), invoked 2026-09-06.
Constraints given to it, overriding its style defaults: pure ASCII, no em or en dashes
(a real send once mangled one into mojibake), every number and claim kept exactly as
measured, keep the AI disclosure, keep it short. Prior third-party feedback on our
comments: read as AI-written and verbose.

## What the pass found in the draft

| # | Pattern | Where | Fix |
|---|---|---|---|
| 16 | Inline-header vertical list | Two bold pseudo-headings introducing each claim | Turned into plain ordinal sentences: "First, ...", "Second, ..." |
| 32 | Aphorism formula | "Collapsing to one answer deletes the contradicting evidence from view." | Replaced with what the reader actually gets: one confident falsehood and no trace a correction was written |
| 9 | Negative parallelism | "the invariant is not 'does supersession stick' but ..." | Stated positively: "The invariant to test is whether supersession survives a re-assertion of the value it replaced." |
| 31 | Manufactured punchline | "it is where I have measurements rather than opinions" | Cut. Replaced with "Two things I measured today bear on it." |
| 27 | Persuasive-authority trope | "The point for a benchmark is narrower" | Cut; the sentence now just makes the point |
| 24 | Hedge-then-pivot | "That may be exactly what a protected key is meant to do, and I am not claiming otherwise." | "Blocking every write may be what a protected key is for." |
| 22 | Servile closing | "I am happy to write either case up" | "I can write either one as a test ... if that is more use than a suggestion." |

## What it deliberately left alone

The measured tables, the commit hash, the package version, the tp/tn/fp/fn figures and
the 8/8, 0/8 and 30/30 counts. The AI disclosure line. The @-mentions, including the
answer to @Rishik00, whose 2 September question is still unanswered in the thread.

## Result

394 words, 2,369 characters, zero non-ASCII characters, zero em or en dashes.
