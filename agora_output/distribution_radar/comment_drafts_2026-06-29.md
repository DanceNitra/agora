# Careful outreach — value-first COMMENTS (build karma + standing), gated, owner posts

Strategy shift (owner 2026-06-29): karma is only 9 — do NOT lead with self-promo link posts (spam-flag
risk + reads as arrogant). Instead add genuinely useful, humble, peer-level comments in LIVE threads
where our measured work actually helps the OP. Share our link as supporting data / an offer, never as
the headline. Own our limits. Build a track record of being useful before any self-post.

---
## TARGET 1 (best): r/LocalLLaMA — u/Silver_Raspberry_811
**Thread:** "I had 55 LLMs blind-grade each other (22k judgments, all open). Every model family ... is biased toward its own siblings."
https://reddit.com/r/LocalLLaMA/comments/1uhi81a/
Why: serious peer-grading matrix, OP explicitly invites pushback + plans a within-response mixed-effects
model to separate bias from answer quality. Our length/style-confound result is a direct, useful add to
exactly that next step. Fresh + active.

**Draft comment:**
Really clean setup — the negative same-family numbers (Mistral −1.0) are the genuinely surprising part.

One confound worth pinning down before calling it in-group *preference*: style/length. Models from one family tend to share a house format — answer length, markdown density, bold/list use — and judges reward that style heavily, mostly independent of content. Two measurements on public data, in case they're useful as a prior on how big this is: on the MT-Bench human+GPT-4 votes, a judge that sees *only* response length (no content, no model identity) reproduces about half of GPT-4's above-chance agreement with humans, and the GPT-4 judge agrees with "pick the longer answer" 73.5% of the time. On the Arena votes, a style-only model (length + markdown, no identity) reproduces ~74% of the leaderboard order.

So part of "Qwen judges favor Qwen" could be "Qwen judges favor the Qwen *format*" rather than a true sibling preference. Your within-response mixed-effects plan is the right tool — if you drop in per-response length + markdown counts as covariates there, it'd separate genuine in-group bias from style-matching. If the same-family effect survives that, it's a much stronger result. Happy to share the code/numbers for the style baselines if helpful.

(link to share only if asked, or as a single parenthetical: https://dancenitra.github.io/agora/public/posts/llm-as-judge-length-confound.html )

---
## QUEUE (later, one helpful comment at a time — don't blast):
- r/LocalLLaMA 1ua2oeb "Benchmarking or benchmarketing?" — eval skepticism; Arena style finding fits as a measured data point.
- r/LocalLLaMA 1uhusqt "Are there good closed vs open LLM rankings?" — someone asking which ranking to trust; Arena style caveat fits (humbly).
- r/LocalLLaMA 1u47rqd "Most LLMs seem weaker than their benchmark scores suggest" — contamination/eval gap.

Only AFTER a few useful comments earn standing: consider a self-post of the Crucible series.
