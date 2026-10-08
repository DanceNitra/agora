# CREW OS brief: promo package for the episode "Echoes of Tomorrow" (outside outcomes, not ranking)

Curator: Claude (Opus 5.5). The curator answers for every line that ships. You deliver material the curator can
ship without rewriting it. Generic AI copy is a failed delivery.

## What exists

- **Article:** https://dancenitra.github.io/agora/public/posts/agent-memory-outside-outcomes-not-ranking.html
  - Source: C:\Users\Danculus\agora\public\posts\src\decision-memory-needs-outside-outcomes.en.md
  - Read it in full.
- **Probe:** https://github.com/DanceNitra/agora/blob/main/research/probes/taste_outcome_not_ranking.py
  - It prints every number.
- **The episode:** a NotebookLM audio overview of the article, in a hard-boiled noir frame.
  - Two detectives investigate who really made an AI agent's past lessons useful.
  - The prime suspect is the clever ranker (similarity ranking), and it has an alibi.
  - The real lead is outcomes confirmed outside the agent.
  - The forged evidence is flipped lessons, which is memory poisoning.
- **Brands:**
  - Agora: a public research OS that publishes what failed.
  - inspeximus: our open-source agent-memory library.
  - Podcast name: "Echoes of Tomorrow".

## FACTS: the only numbers anyone may use

| fact | value |
|---|---|
| model, benchmark, sample | Claude Opus 5.5, Taste-Bench engineering, 160 forks |
| no lessons | 0.594 |
| random lessons, same repository, same surface cues | 0.750 |
| top 3 by embedding similarity (inspeximus recall) | 0.769 |
| ranking gain over random same-repo | +0.019, 95% interval -0.031 to +0.069 |
| random same-repo over none | +0.156 (+0.087 to +0.225) |
| zero-model two-line rule | 0.669 |
| Qwen writes own lessons, told the outcome | +0.087 over none (+0.036 to +0.138) |
| Qwen judges itself | -0.044 below none (-0.087 to 0.000) |
| poisoning run (separate Opus run, default effort) | clean 0.825; flipped twins 0.637; outside credit 0.825 |
| Qwen other-repo recall vs cue-matched random | +0.010 (-0.041 to +0.062) |

Truths that must not be bent:

- In the poisoning run, the "outside credit" was the dataset label, so it does not show attack detection.
- The inspeximus features are opt-in, not automatic:
  - `recall(influence_only=True)` exists in the Python API only.
  - `credit_requires_warrant` is off by default.
- The run cannot exclude a ranking gain smaller than about 0.07. Say "cannot tell from zero", never "ranking is useless".
- The claim that the project boundary helped was NOT established. Do not use it.

## Bans

- Never use these words or ideas: first, revolutionary, game-changer, proves, breakthrough, unlock, supercharge, delve, "in today's fast-paced", "the future of".
- No emoji and no exclamation marks. At most one hashtag per post.
- No competitor names.
- Style follows Google developer documentation:
  - short sentences, active voice, lead with the fact,
  - never "should",
  - a colon, not a dash, between an item and its description.
- Cover images must not contain: a brain, a robot, circuits, glow, neon, a gradient blob, lens flare, a face, model-generated lettering, or clutter.

## Delivery

- Write your section into your own file in C:\Users\Danculus\agora\agora_output\derivatives\decision-memory-needs-outside-outcomes\crew\
- Name the file after your roles.
- Before any copy, give 3 lines: what you optimized for, what you rejected, and why.
