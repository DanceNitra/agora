Similarity ranking beat same-repo random lessons by 0.019 (95% CI -0.031 to +0.069) on 160 forks

Setup first, because it decides how far this goes. The random baseline was not random over everything: each random lesson came from the same repository and carried the same surface cues as the lesson similarity search picked. We did not test a learned ranker. And every lesson carried the fork's true outcome, which no deployed agent gets.

What we ran: 160 engineering forks from Taste-Bench (Pan et al.). Each fork is a real coding decision with two options and one that led to the better outcome. Claude Opus 5.5 sees both options in both orders and only scores when both answers are right. A lesson is one line from another task: "choosing X over Y led to the better outcome".

- No lessons: 0.594
- Random same-repo lessons: 0.750
- Top 3 by embedding similarity: 0.769

So the lessons helped a lot, and picking them by similarity added 0.019, which this run cannot tell from zero.

What did matter was where the outcome came from. In a separate Qwen run, lessons written after it was told the outcome added 0.087 (+0.036 to +0.138). When it judged its own earlier choices, its lessons scored 0.044 below no lessons (-0.087 to 0.000).

How are you scoring the memories your agent learns from: by an outside result, or by the agent itself?

Write-up, with a probe that prints every number:
https://dancenitra.github.io/agora/public/posts/agent-memory-outside-outcomes-not-ranking.html
