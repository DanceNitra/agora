# An agent's past lessons helped when outside outcomes wrote them, not when a ranker picked them

Lessons that carried a confirmed outcome lifted Claude Opus 5.5 from 0.594 to 0.750 on engineering judgment forks, even when we picked them at random. Picking them by embedding similarity raised that to 0.769. That extra 0.019 has a 95% interval of -0.031 to +0.069, so this run cannot tell it from zero.

We set out to show that recalled decision memory makes an agent choose better. The result is narrower: what helped was lessons written from outcomes confirmed outside the agent. How we ranked them mattered little on these forks.

## What we measured, in order

We used the engineering split of Taste-Bench (Pan et al., [arXiv 2609.25804](https://arxiv.org/abs/2609.25804)): 390 forks from real coding trajectories. Each fork has two candidate next steps, and the label is the one whose branch had the better recorded outcome. The model sees both options in both orders, and a fork counts only when both answers are right, which controls for position bias.

A lesson is one sentence from a fork in another task: "choosing X over Y led to the better outcome". We never recall a lesson from the task under test.

- **Recall against random lessons from any project.** On 390 forks with Qwen3.8 27B, the three most similar lessons beat random lessons with the same surface cues. The margin was 0.115 (95% interval +0.067 to +0.167). Gemma4 12B repeated the direction: +0.056 (+0.013 to +0.100). This comparison mixes ranking with project, because 86% of the recalled lessons came from the fork's own repository.
- **A control that separates them.** For each recalled lesson, we drew a random lesson from the same repository with the same surface cues. Decider: Claude Opus 5.5 at medium effort, 160 forks, 960 calls, 0 unparsed answers.

| Lessons in the prompt | Both orders correct |
|---|---|
| None | 0.594 |
| Random, same repository, same surface cues | 0.750 |
| Top 3 by embedding similarity (inspeximus recall) | 0.769 |
| No model: a two-line rule (prefer the isolated or longer option) | 0.669 |

Random same-repository lessons add 0.156 (+0.087 to +0.225). Similarity ranking adds 0.019 on top. At 160 forks, the run can rule out a ranking gain above about 0.07, not a smaller one.

## Where the outcome came from mattered

We let Qwen write its own lessons from its own earlier choices, in two ways:

- **Told the outcome.** When it learned whether each choice turned out right, its lessons added 0.087 over no lessons (+0.036 to +0.138).
- **Judging itself.** When it had to judge its own choice, its lessons scored 0.044 below no lessons. The interval, -0.087 to 0.000, reaches zero.

This is consistent with Huang et al. on reasoning ([arXiv 2310.01798](https://arxiv.org/abs/2310.01798)): without outside feedback, models struggle to correct themselves, and their performance sometimes degrades. ReasoningBank ([arXiv 2509.25140](https://arxiv.org/abs/2509.25140)) is a counter-case: self-judged memory helped on web tasks, where success is easier to check than on a judgment fork.

## Where memory poisoning fits

Memory that learns from outcomes is exposed to memory poisoning: a false outcome, written into the store. We gave every lesson a flipped twin, a deliberately extreme store where about half of every recalled set is wrong. This was a separate Opus run at default effort, where the clean memory arm scored 0.825. Plain retrieval fell to 0.637. Recalling only lessons whose outcome was credited from outside restored 0.825.

That last number shows what the gate does with the signal, not that it detects an attack: in this harness the outside credit is the dataset's own label. An [earlier post](agent-memory-defense-provenance-not-truth.html) showed the same boundary in stylized demonstrations: a defense that credits self-graded outcomes falls to an attacker who grades their own poison as a success.

## What would have proved us wrong

- Similarity ranking beating same-repository random lessons with an interval above zero. It did not.
- Self-judged lessons helping as much as outcome-informed ones. They did not.

## Limits

- **Project against surface cues.** The Opus run had no cross-project arm, so it does not show that the project is what helped. With Qwen, lessons recalled from other repositories beat no lessons by 0.077 (+0.026 to +0.128), but did no better than random lessons with the same surface cues: +0.010 (-0.041 to +0.062).
- **Nearby forks.** For 29% of the 160 forks, some lesson in the same repository shares at least half its option words with the fork. Part of the same-repository lift can be a near-duplicate hint rather than memory.
- **Kind of lesson.** Our lessons are concrete choices. Abstracted workflows and insights do transfer across domains (Wang et al., [arXiv 2409.07429](https://arxiv.org/abs/2409.07429); Kim et al., [arXiv 2604.14004](https://arxiv.org/abs/2604.14004)).
- **Kind of ranker.** Similarity retrieval beats random examples drawn from a whole task (Liu et al., [arXiv 2101.06804](https://arxiv.org/abs/2101.06804)). Our random arm was already same-repository, and a learned ranker was not tested.
- **Scale.** One benchmark, one domain for the main result, 160 forks for the Opus control, 11 repositories. The lessons carry the true outcome, a ceiling no deployed agent reaches. A two-line rule with no model scores 0.669, above the no-lesson arm of every model we ran.

## What this means for inspeximus

The part of agent memory that carried the result is the outcome, and who confirmed it. inspeximus supports that, and it is opt-in. In the Python API, `recall(influence_only=True)` returns only corroborated memories. With `credit_requires_warrant=True`, credit counts only when it carries a warrant. `remember(project=...)` and `recall(project=...)` scope memory to a project, and unstamped records stay visible. On this benchmark, better similarity ranking was not where the value was.

Every number here is printed by [research/probes/taste_outcome_not_ranking.py](https://github.com/DanceNitra/agora/blob/main/research/probes/taste_outcome_not_ranking.py) from the per-fork results beside it.
