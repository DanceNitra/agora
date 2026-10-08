# 25 Campaign-Creator, 02 Media-Buyer, 13 Retention: campaign copy, retention, media plan

Episode: "Echoes of Tomorrow", {TITLE}. Episode link: {EPISODE_URL}.
Sources read in full: the three role cards, the three Pamat files, BRIEF.md, and
`public/posts/src/decision-memory-needs-outside-outcomes.en.md`.
Status: draft for the curator. Nothing posted, sent, committed, or pushed.

## Three lines before the copy

- Optimized for: one message in every piece. Our own ranker has an alibi, and the outcome did the work. Every number comes from the FACTS table, and the lead number sits in the opening sentence.
- Rejected: "ranking is useless", the project-boundary claim, attack-detection wording for the 0.825 restore, the 390-fork and 0.115 figures (true in the article, absent from FACTS), competitor names, and any hashtag.
- Why: 25's rule is one idea and at most three arguments. We carry the ranker's alibi, the outcome lead, and the poisoning caveat. A copy that bends one truth loses the credibility the storefront sells.

## 1. Spotify description (paste as is)

The ranker had an alibi: random lessons from the same repository lifted Claude Opus 5.5 from 0.594 to 0.750 on 160 Taste-Bench engineering forks, with no ranking at all. Picking the top 3 by embedding similarity reached 0.769. That extra 0.019 has a 95% interval of -0.031 to +0.069, so this run cannot tell it from zero. The real lead is the outcome: Qwen lessons written after it was told the outcome added 0.087, while lessons Qwen judged itself scored 0.044 below none. In a separate run, flipped lessons cut the score from 0.825 to 0.637.

https://dancenitra.github.io/agora/public/posts/agent-memory-outside-outcomes-not-ranking.html
https://github.com/DanceNitra/agora/blob/main/research/probes/taste_outcome_not_ranking.py

Word count: 96 words of prose plus two URL lines, 98 in total (checked by script, see the receipts section).

## 2. X thread

1/
Random lessons from the same repository lifted Claude Opus 5.5 from 0.594 to 0.750 on 160 engineering forks. Ranking them by embedding similarity, with our own recall, added 0.019. The 95% interval is -0.031 to +0.069. This run cannot tell our ranker from zero.

2/
The outcome did the work. When Qwen wrote lessons after it was told the outcome, they added 0.087 over no lessons (+0.036 to +0.138). When Qwen judged its own choices, its lessons scored 0.044 below no lessons.

3/
Outcome memory can be poisoned. In a separate Opus run, a flipped twin of every lesson cut the score from 0.825 to 0.637. Recalling only outside-credited lessons restored 0.825, but that credit was the dataset label. It shows the gate, not attack detection.

4/
The noir episode, two detectives and one ranker with an alibi:
{EPISODE_URL}

The article, with a probe that prints every number:
https://dancenitra.github.io/agora/public/posts/agent-memory-outside-outcomes-not-ranking.html

Hashtags: none. Raw lengths: 261, 210, 257, and 266 characters, the last with a 55-character Spotify episode URL (the length of an open.spotify.com/episode/ link). X counts each URL as 23 characters, so post 4 weighs about 150 on X.

## 3. LinkedIn post

The ranker had an alibi.

We tested whether recalled lessons help Claude Opus 5.5 make engineering choices. On 160 Taste-Bench forks, no lessons scored 0.594. Random lessons from the same repository, with the same surface cues, scored 0.750. The top 3 by embedding similarity, from inspeximus recall, scored 0.769.

That ranking gain is 0.019, with a 95% interval of -0.031 to +0.069. This run cannot tell it from zero, and it cannot exclude a gain smaller than about 0.07.

The outcome carried the result. Lessons Qwen wrote after it was told the outcome added 0.087 over no lessons. Lessons where Qwen judged its own choice scored 0.044 below none.

So the source of an outcome matters. In a separate Opus run, flipped lessons cut the score from 0.825 to 0.637. Recalling only outside-credited lessons restored 0.825. That credit was the dataset label, so the run shows the gate, not attack detection.

In inspeximus these controls are opt-in: recall(influence_only=True) in the Python API, and credit_requires_warrant, which is off by default.

Episode: {EPISODE_URL}
Article: https://dancenitra.github.io/agora/public/posts/agent-memory-outside-outcomes-not-ranking.html

Word count: 169 words of prose (checked by script).
Note for the curator: earlier LinkedIn posts (verify-agent-memory-deletion) put links in the opening comment. The brief asks for links at the end, so this version ends with them. The curator decides.

## 4. Retention: the opening 60 seconds (for the NotebookLM focus prompt)

1. 0-15 s, cold open, no show intro: open on the alibi. Random same-repository lessons lifted Opus from 0.594 to 0.750 before anyone ranked anything.
2. 15-40 s, BUT: name the prime suspect, similarity ranking, and give its 0.019 with the interval -0.031 to +0.069. Say "we cannot tell it from zero" and nothing stronger.
3. 40-60 s, THEREFORE: give the real lead. Told the outcome, Qwen's lessons added 0.087. Judging itself, they fell 0.044 below none.
4. Close the minute on an open loop: forged evidence is coming. Flipped lessons cut 0.825 to 0.637. Hold the dataset-label caveat for the reveal act, and never drop it.
5. No statement in the opening minute may suggest the project boundary helped, or that inspeximus features run by default.

## 5. Media plan (zero paid budget, times in Europe/Bratislava)

1. Tue 29 Sep, by 12:00: owner publishes the episode on Spotify and gives us the URL. {EPISODE_URL} gets filled, and nothing ships before that.
2. Tue 29 Sep, 15:30: LinkedIn post. This is the only channel with an Agora audience, and 15:30 lands at the EU afternoon and the US East morning (09:30).
3. Tue 29 Sep, 16:00: X thread from @Dance_NR, as a public record only. The account has 8 followers and a music audience, so we expect no reach from it.
4. Wed 30 Sep, 15:00: Reddit text post on the finding (the ranker's alibi and the outcome lead) in r/Rag, where u/Danculus has 17 posts. The article link goes in the body, and the episode goes in a comment. The owner pastes it, because the browser cannot reach Reddit.
5. Thu 1 Oct: reply only where a live thread asks whether recalled memory helps an agent choose, with the numbers and the probe link. No cold drops.
6. One metric per channel, with no kill rule because nothing is paid: LinkedIn impressions and comments at 48 h, Reddit upvote ratio at 24 h, Spotify plays at 7 days. We log each one to the ledger.
7. Every item passes the owner gate (`outbound` skill, render approval, "posli") before it leaves. This plan authorizes no send.

## Receipts: checks run on the copy above

Run 2026-09-28 by a Python check over the sections in this file:

| check | result |
|---|---|
| Spotify prose words | 96 (98 with the two URLs), target 80-120 |
| X posts, raw characters | 261, 210, 257, 266 (with a 55-character episode URL), limit 270 |
| LinkedIn prose words | 169, target 120-200 |
| Retention lines / media plan lines | 5 / 7, limits 6 / 8 |
| Banned words (first, prove, breakthrough, unlock, should, the future of, and the rest of the brief's list) | 0 hits after one fix ("useless" removed from retention line 2) |
| Exclamation marks, hashtags, em or en dashes, non-ASCII characters | 0 |
| Competitor names | 0 |
| Numbers used | 0.594, 0.750, 0.769, 0.019, -0.031, +0.069, 0.07, 0.087, +0.036, +0.138, 0.044, 0.825, 0.637: all in the FACTS table |

Truth checks: the 0.825 restore always carries the dataset-label caveat; the inspeximus features are called opt-in; the ranking gain is "cannot tell from zero"; the project boundary is not claimed anywhere.
