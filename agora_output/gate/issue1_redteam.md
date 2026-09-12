# red-team pass, reply_inspeximus_issue1_close.md, 2026-08-31

Skill: .claude/skills/stress-claim, invoked in pre-draft mode on the CLAIM and its measurement.

## HOW IT RAN, stated because it is a departure

The session forbids spawning agents, so the five lenses were NOT fanned out to general-purpose
agents as the skill prescribes. I took the skill's questions and answered the two that were
answerable by measurement rather than opinion. That is weaker than the panel and is recorded as such.

## Claim under test

Both contracts @mioimotoai-lgtm proposed in inspeximus issue #1 are implemented, verified from a
clean clone at d6c2722.

## Two hits, both material, both fixed before drafting

OVERCLAIM. "Both contracts" was false as written. Their option 1 has a clause I had skipped: an
existing process-level OPENAI_API_KEY must survive the dotenv. Untested at the time of the first
draft. Now tested: a server/.env saying `from-the-dotenv` against a process saying
`from-the-process` resolves to `from-the-process`. The draft now says three things rather than two
and shows that transcript.

METHOD. The "clean clone" was not exercising the clone. The first arm ran with an editable install
pointing at my working tree, so the transcript proved nothing about a fresh checkout. Worse, the
`pip install -e .` I then ran inside the clone repointed the whole machine's `inspeximus` at a
scratch directory, which also put the release check running at the time in doubt. Environment
restored; both arms re-run inside a dedicated venv whose `inspeximus.__file__` was printed and
confirmed to be the clone.

## Two judgement calls left standing, recorded rather than resolved

CLOSING WITHOUT A REPLY. The reporter has not answered since 2026-08-22. Closing with an explicit
invitation to reopen is normal and reversible, so this is not treated as a blocker.

QUOTING 1.00 IN PUBLIC. It comes from an instrument we ourselves label as not comparable with the
published figures. Kept, because the tool prints the disclaimer immediately below it and removing
the number would look like hiding it, with a sentence in our own voice saying it is not offered as
a result.

## Verdict

PUBLISH, after the two fixes above. The claim as now written is narrower than the claim I started
with.
