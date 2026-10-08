The ranker had an alibi.

We tested whether recalled lessons help Claude Opus 5.5 make engineering choices on 160 forks from Taste-Bench (Pan et al.). The scores:
- No lessons: 0.594.
- Random lessons from the same repository, with the same surface cues: 0.750.
- The top 3 by embedding similarity, from inspeximus recall: 0.769.

That ranking gain is 0.019, with a 95% interval of -0.031 to +0.069. This run cannot tell it from zero, and it cannot exclude a gain below about 0.07.

The lead was the outcome. In a separate Qwen run, lessons written after Qwen was told the outcome added 0.087 (+0.036 to +0.138). When Qwen judged its own choices, its lessons scored 0.044 below none (-0.087 to 0.000).

Outcomes can also be forged. In a deliberately extreme store, flipped lessons cut the score from 0.825 to 0.637. Recalling only outside-credited lessons restored 0.825. That credit was the dataset label, so the run shows the gate, not attack detection. Every lesson carried its true outcome, a ceiling no deployed agent reaches.

In inspeximus, both controls are opt-in: `recall(influence_only=True)` in the Python API, and `credit_requires_warrant`, which is off by default.

Who confirms the outcomes your agent learns from?



First comment:
Episode: https://open.spotify.com/episode/2MtB8PxIctRKHLKAJSEQJl
Article, with a probe that prints every number: https://dancenitra.github.io/agora/public/posts/agent-memory-outside-outcomes-not-ranking.html
