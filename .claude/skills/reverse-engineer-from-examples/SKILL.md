---
name: reverse-engineer-from-examples
description: Learn how something works from finished examples, then rebuild it and test the rebuild. Use when the owner says "reverse engineer", "reverzne inzinierovat", "pozri ako to robi X a postav nase", "nauc sa z prikladov", "postav skill podla vzorov", or when a feature, a report, a video style, a bot behaviour or a claim is easier to show than to specify. Works on artifacts we own or may lawfully inspect. Not for copying someone else's code or assets, and not for bypassing any protection.
---

# Reverse engineer from examples

Built 2026-10-14 from Nate Herk's video "I Tested the Viral Reverse Engineer Anything Skill" and from the
skill that ships in morluto/rea (MIT). The video's own point: the repo adds a disciplined process, not a new
idea. A finished example is a more exact specification than a typed one.

## Rule 0: what may be examined

- Examine only what we own, hold a licence for, or that is public and permitted to inspect.
- Rebuild the behaviour, never the code or the assets. Our version looks and is written differently.
- Never bypass a licence check, a DRM, a login, bot protection, or any access control.
- Never touch a private system of someone else. Public availability is not permission.
- When unsure whether an artifact may be examined, ask the owner before opening it.

## The five steps

1. **Pick one feature or one output type.** Not "clone X". Write the question in one line, for example
   "how does the camera bubble follow the cursor" or "what do our best Friday reports have in common".
2. **Route by build.** Name the artifact kind (video, report, JavaScript app, binary, API, log file, bot
   run), then choose the tool for that kind. Look at existing tools and skills first. A guess about the
   tech stack goes into the ledger as INFERRED.
3. **Summary first.** Write the full analysis to disk once, under `agora_output/reverse/<slug>/`, with the
   artifact's sha256. Read a short summary of it. Do not run the full analysis again without a changed
   input.
4. **Tag every finding SEEN, INFERRED or UNKNOWN.**
   - SEEN: cites where it was observed (file and line, frame and timestamp, command and output).
   - INFERRED: names the evidence it rests on and the check that would confirm it.
   - UNKNOWN: names what could not be reached and why.
   Never build on an INFERRED item as if it were SEEN. Give it a test that can fail first
   (see the instrument-control skill).
5. **Rebuild and test.** Run the rebuild on a held-out example that was not used to extract the rules.
   Compare against the original behaviour. Report the mismatches. Iterate until the mismatch list is
   short or the remaining ones are UNKNOWN. No runnable test, no claim.

## Mode B: from output examples to a skill

Use this when the target is a style or a format, not a program.

1. Collect 5 to 30 strong examples and 3 to 5 weak ones. Ask the owner which are which.
2. Analyse each example part by part (frame by frame for video, section by section for text).
3. Write a rule table: property, value seen in strong examples, value seen in weak ones, tag.
4. Write the skill from the table, with the weak examples as the "avoid" list.
5. Generate one new output. Compare it blind against one held-out strong example. Report the differences.

## Finding ledger

Keep one table next to the analysis. Columns: question, tag, evidence, limit, next check. Before
finishing, go through the original questions and mark each answered, partly answered, or unresolved.
Say "unresolved" when it is.

## Costs and limits

- This is slower than a one-line prompt. The video reports a slower run with better results in one
  comparison; that is one anecdote, not a measurement.
- The result depends on the model that reads the evidence. Rerunning the rebuild with a cheaper model
  on the saved ledger is a valid experiment.
- A rebuild that matches the examples shows we reproduced those examples. It does not show the
  mechanism is the same.
- Anything that goes outward (a post, a claim, a number) still goes through the outbound gate and the
  owner's `posli`.

## Inside other projects

Obey that project's own CLAUDE.md first. In ftmo-lab that means: no trading or live commands, no use of
the protected OOS-2 and FORWARD periods without the owner's explicit consent in the session, research
only through the project's own interpreter and thread budget.
