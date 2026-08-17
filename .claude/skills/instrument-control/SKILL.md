---
name: instrument-control
description: Before reporting ANY measured finding — a zero, a 404, an empty result, a count, a percentage, a "this is missing", a "nobody does X", a pass/fail verdict — run the control that would have caught the instrument instead of the world. Use when about to tell the owner a number, write one into a commit message or a comment, base a recommendation on a measurement, or conclude that something is absent, broken, uncovered or unused. Also use when a hypothesis is about to become an action.
---

# Instrument control — the finding is about your tool until a control says otherwise

## Why this exists

**2026-08-17: twelve instrument failures in one day.** Not twelve mistakes of care — twelve findings
that were true of the measuring apparatus and false of the world. Every single one was caught by a
LATER measurement, never by confidence, and the most expensive one was one sentence away from
persuading the owner to dismantle his own frontier lock.

That is the whole argument. You cannot feel the difference between a real zero and a broken
instrument. You can only measure it.

## The one rule

> **A negative, an absence, or a count does not leave the workspace without a control that would have
> failed.**

Everything below is that rule, specialised.

## The six shapes, each from a real 2026-08-17 failure

| shape | what happened | the control |
|---|---|---|
| **Absence by uncontrolled instrument** | Two published receipt links reported dead on a 404. The control — the same fetch against a file known to be present — also 404'd. GitHub throttles unauthenticated blob URLs; the links were fine. | Run the identical query against something you KNOW is there. If the control fails, the finding is void. |
| **Wrong field / wrong path** | A bucket scored "0 of 3 on-priority" because the probe read `question` while the code builds its quest from `origin`. Another missed a `kind == "research"` filter the code applies. | Read the CONSUMING code and measure the field it reads, not the one that looks right. |
| **Truncated window** | `grep -n "^import re" file \| head -8` declared the import missing. It sits at line 466. | Count before you conclude (`grep -c`), or drop the pipe. A window that can hide the hit is not a search. |
| **The harness creates the state it reports** | A probe passed `receipts=True` and then reported "receipts enabled, chain empty". Same file, three ways of opening it, three verdicts. | Vary the instrument. Open it three ways; if the finding moves, it is about the setup. |
| **A handler swallowing the defect** | A thread checker returned UNKNOWN for everything because `json` was not imported and the `NameError` landed in its own `except`. It reported "0 not open" and looked clean. | A control must distinguish *failed to look* from *looked and found nothing*. Never let an unknown render as a pass. |
| **Comparing values that carry noise** | Two pytest runs with identical outcomes compared unequal, because the summary string ends in the elapsed time — so a SURVIVING mutant was reported as killed. | Compare the extracted numbers, never the rendered line. |

## The procedure

1. **Name the claim as a sentence** with its number in it. "X is absent." "N of M pass." "The rate fell
   from A to B."
2. **Write the control before the measurement**, not after: *what result would prove my instrument
   works?* If you cannot state one, you cannot make the claim.
3. **Run the control.** A positive control for absences, a must-fail mutant for guards, a known-present
   fixture for counts.
4. **Vary one thing about the instrument** — the fetch method, the field, the parser, the path — and
   check the finding survives.
5. **Only then report**, and report the control alongside the number. A number without its control is
   a rumour with a decimal point.

## Hard stops

- **Never report an absence** whose positive control you have not run. This is the single most
  expensive shape; it accounts for four of the twelve.
- **Never recommend an action** from a measurement whose instrument you have not varied. The frontier-lock
  near-miss was exactly this: a correct measurement of the wrong population.
- **Never let `except` decide.** If a check can fail silently, it will, and it will look clean while
  doing it.
- **A green suite that cannot tell "the fix works" from "the case never arises" has measured nothing.**
  Verify BOTH directions: the mutant fails, and the tree is green when reverted.

## What is already automated

`.claude/hooks/instrument_control.py` (PostToolUse, Bash) fires on the mechanical shapes without being
remembered: an empty grep/find, a `| head` truncated search, a `github.com/blob` curl, a `gh issue/pr`
GraphQL call, a pytest summary compared as a string. It is deliberately narrow — a reminder that fires
on everything is wallpaper, and this repository has measured that too: 1.5 million identical log lines
made a three-day outage invisible.

The hook catches the shapes a machine can see. This skill is for the ones it cannot: the wrong field,
the wrong population, the hypothesis that was never a measurement.

## Related

`verify-claims` checks the facts of a finished draft; this checks the MEASUREMENT before there is a
draft. `stress-claim` attacks the argument; this attacks the apparatus. The standing gate
(validate → storm → audit → verify) assumes the numbers entering it are real — this is what makes that
assumption true.
