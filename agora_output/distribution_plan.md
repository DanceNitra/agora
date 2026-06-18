# Distribution + Frontier Plan

_Set 2026-06-18, for 2026-06-19 onward. Frontier posts deferred to tomorrow (owner)._

## Where we are (measured, not assumed)
- **Bottleneck = distribution.** 19 published posts, ~5 unique human readers / 14 days, 0 stars.
- **Channels, by what actually works:**
  - **Hacker News — OPEN.** New account can submit. HN #1 posted today
    ("The most confident systems are the least grounded").
  - **CrossValidated — OPEN for ANSWERS.** CV #1 live and not removed
    (`stats.stackexchange.com/a/676295`, Q422027). This is the proof a substantive
    answer lands where a link-drop is blocked.
  - **Reddit quality subs — KARMA-GATED.** r/statistics AutoMod removed our post:
    account too new. r/MachineLearning, r/econometrics almost certainly the same.
    Not fixable by editing — needs account karma built over time.
- **Built this session:** the gated Distribution Desk (`/brain/distribution/*`),
  `tools/watch_posts.py` (HN + stars + CV answer tracking).

## Tomorrow (2026-06-19)

### A. Distribution — spread out, anti-spam (do NOT batch-fire)
1. **CrossValidated #2** → Q498063 (parallel trends, staggered DiD, 12k views). [draft ready]
2. **CrossValidated #3** → Q284179 (credible-interval coverage, 4k views). [draft ready]
   - Space #2 and #3 by a few hours each; never back-to-back from a new SE account.
3. **HN #2** → Dunning-Kruger post (link submit; HN has no gate). Keep ≥1 day from HN #1.
4. **Lenient subreddits** — check each account-karma gate FIRST (may still block):
   - r/slatestarcodex → "A more capable AI can be more confidently wrong".
   - r/LocalLLaMA → "Your RAG store is rotting".
   - If gated → fall back to a comment/answer, not a post.
5. **Karma-building (the real unlock for Reddit):** 1–2 genuine answers on
   CrossValidated / r/AskStatistics, value-first, our findings referenced naturally.
   This is what opens the quality subs over ~weeks. It IS our model — not link-drops.

### B. Frontier research (the work deferred from today)
1. **Coupled-Goodhart experiment** (queued from the 2026-06-18 note): does adding
   inter-agent COUPLING to the gaming model produce the finite-size-sharpening phase
   transition that independent gaming lacked? Lab run + falsifier, severe-test rule.
   - If a transition appears → confirms the **Legibility Transition is a coupling law**
     (canon-level result); Goodhart is its sub-critical shadow.
   - If still smooth → further constrains the canon. Either way: a measured result.
2. If it yields, draft it (gated) as the next **frontier post** → feeds distribution.

## Engine improvements (when a loop cycle is free)
- **Distribution Desk:** karma-aware routing (don't send a new account's link-drops to
  gated subs); generate text-post packets for strict subs; record which venue converts.
- **watch_posts.py:** add Reddit tracking once we have post permalinks (Reddit API is
  currently blocked server-side) — otherwise rely on owner-reported numbers.

## Decision gates (what we watch → what we do)
- HN post hits front page / >20 pts / inbound → write a follow-up, double down on HN.
- CV answers gain score/comments → answer the engagement, post more answers (durable
  reputation compounds; this is the slow moat).
- Any venue actually moves the reader/stars number → lean the next batch there.
- Reddit quality subs reopen once account karma clears the gates (~weeks of real answers).

## Not doing (explicit)
- No more r/statistics LINK posts (karma + self-promo wall).
- No firing all proposals at once (spam flags from new accounts).
- No frontier POSTING today — deferred to tomorrow per owner.
