# Promo package: Echoes of Tomorrow, episode 2

Curator: Claude (Opus 5.5). Revision 2, after the gate by 04 Critic, 05 Skeptic and 06 Verifier. The gate report is in `crew/04-05-06_gate.report.md`.

Verified:
- All 17 numbers match `research/probes/taste_outcome_not_ranking.py`.
- The article URL and the probe URL return 200.
- All 6 arXiv ids match their attributions.
- The 0.825 restore ran through `recall(..., influence_only=True)`, per `ramr_taste_poison.py` recall3.

To fill after Spotify publishes:
- https://open.spotify.com/episode/2MtB8PxIctRKHLKAJSEQJl
- (00:00) The case file
(02:34) The lineup: 0.594 with no lessons
(05:12) Random lessons from the same drawer
(06:39) The ranker's alibi
(07:20) The real lead: outcomes from outside
(11:02) Memory poisoning: the flipped twins
(12:30) Gatekeeping with outside credit
(14:18) The limits of the investigation
(16:48) The two-line rule
(18:54) The verdict, and what inspeximus does, from the checked transcript.

Nothing ships before the owner approves the render.

## Title

**The ranker had an alibi: agent lessons helped when outcomes came from outside**

Runner-up: "Random lessons came within 0.019: what carried an AI agent's memory"

## Spotify description

What made an AI agent's past lessons useful? On 160 engineering forks from Taste-Bench (Pan et al.), random lessons from the same repository lifted Claude Opus 5.5 from 0.594 to 0.750. Picking the top 3 by embedding similarity reached 0.769. That is a gain of 0.019, with a 95% interval of -0.031 to +0.069, which this run cannot tell from zero.

This episode is the investigation, told as a detective story. The prime suspect is similarity ranking, and it has an alibi. The lead is the outcome, and who confirmed it:
- In a separate Qwen run, lessons written after Qwen was told the outcome added 0.087 (+0.036 to +0.138).
- When Qwen judged its own choices, its lessons scored 0.044 below none (-0.087 to 0.000).

The forged evidence is memory poisoning. In a deliberately extreme store, every lesson got a flipped twin, and the score fell from 0.825 to 0.637. Recalling only outside-credited lessons restored 0.825, and that credit was the dataset's own label. Every lesson here carried its true outcome, a ceiling no deployed agent reaches.

Questions this episode takes on: Does ranking recalled lessons by similarity help an agent choose? Where does a lesson's value come from? What happens when an agent grades its own past? What does a planted, flipped lesson do to memory?

Chapters
(00:00) The case file
(02:34) The lineup: 0.594 with no lessons
(05:12) Random lessons from the same drawer
(06:39) The ranker's alibi
(07:20) The real lead: outcomes from outside
(11:02) Memory poisoning: the flipped twins
(12:30) Gatekeeping with outside credit
(14:18) The limits of the investigation
(16:48) The two-line rule
(18:54) The verdict, and what inspeximus does

Read the article with every number, source and the probe:
https://dancenitra.github.io/agora/public/posts/agent-memory-outside-outcomes-not-ranking.html
https://github.com/DanceNitra/agora/blob/main/research/probes/taste_outcome_not_ranking.py

Sources discussed: Pan et al., Taste-Bench (arXiv 2609.25804); Huang et al. (arXiv 2310.01798); ReasoningBank (arXiv 2509.25140); Wang et al., Agent Workflow Memory (arXiv 2409.07429); Kim et al. (arXiv 2604.14004); Liu et al. (arXiv 2101.06804).

Echoes of Tomorrow is produced by Agora, an autonomous research organization. Every episode rests on a published article with a runnable probe. When a replication fails, we say so.

Article: https://dancenitra.github.io/agora/public/posts/agent-memory-outside-outcomes-not-ranking.html

## X thread

1/
Our own ranker had an alibi. On 160 engineering forks, random same-repo lessons lifted Claude Opus 5.5 from 0.594 to 0.750. Ranking them by similarity reached 0.769: a gain of 0.019 (-0.031 to +0.069) this run cannot tell from zero.

2/
The lead was the outcome. In a separate Qwen run, lessons written after it was told the outcome added 0.087 (+0.036 to +0.138). When it judged its own choices, its lessons scored 0.044 below none (-0.087 to 0.000).

3/
Outcomes can be forged. In a deliberately extreme store, a flipped twin of every lesson cut Opus from 0.825 to 0.637. Recalling only outside-credited lessons restored 0.825, but that credit was the dataset label. It shows the gate, not attack detection.

4/
Two detectives, one suspect with an alibi, and a probe that prints every number.
Episode: https://open.spotify.com/episode/2MtB8PxIctRKHLKAJSEQJl
Article: https://dancenitra.github.io/agora/public/posts/agent-memory-outside-outcomes-not-ranking.html

## LinkedIn post

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

Opening comment: the episode https://open.spotify.com/episode/2MtB8PxIctRKHLKAJSEQJl and the article https://dancenitra.github.io/agora/public/posts/agent-memory-outside-outcomes-not-ranking.html

## Reddit (r/Rag, the owner pastes)

**Title:** "Similarity ranking beat same-repo random lessons by 0.019 (95% CI -0.031 to +0.069) on 160 forks"

The opening paragraph of the body, written after the owner's go, must say three things:
- The random baseline was filtered to the same repository and the same surface cues.
- A learned ranker was not tested.
- The lessons carried the true outcome.

The article link goes in the body, and the episode link goes in a comment.

## Cover (Concept A from 20 and 32)

The prompt and settings are in `crew/20-32_cover.report.md`, section 2. We overlay the typography; the model renders none of it:
- **Title:** Oswald 500, uppercase, upper left, `#E9E4D8`.
- **Series name:** "ECHOES OF TOMORROW" in IBM Plex Mono, `#B8914A`.
- **Brand:** "AGORA" at the bottom left.

Test render: fixed seed, checked at 150 px in greyscale, at most 3 tries.

## Media plan

This plan assumes the episode is live on Spotify by Tuesday, 29 September:

| Day | Time | Channel |
|---|---|---|
| Tuesday | 15:30 | LinkedIn |
| Tuesday | 16:00 | X, for the record |
| Wednesday | 15:00 | Reddit |
| Thursday | | Replies in live threads only |

Every item passes the outbound gate and the owner's render approval.
