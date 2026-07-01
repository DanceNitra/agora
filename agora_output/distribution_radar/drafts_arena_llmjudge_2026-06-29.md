# Gated distribution drafts — Arena + LLM-judge (2026-06-29)

Owner posts MANUALLY. Reddit account is NOT shadowbanned (works). **HN account DanceNitra IS shadowbanned**
— see warning below. Numbers verified vs Lab 14c41f (Arena) + bf7bb9 (LLM-judge). Space the two posts
out (don't blast both same hour); engage in comments; own any mistakes.

---
## REDDIT — Draft A: Chatbot Arena  → r/LocalLLaMA (best fit), alt r/MachineLearning [R]

**Title:** A style-only model — no idea which LLM wrote the answer — reproduces ~74% of the Chatbot Arena leaderboard order

**Body:**
I took the public Arena votes (lmarena-ai/arena-human-preference-140k, ~28k decided battles) and trained the dumbest possible judge: it sees only the answer's *style* — length, markdown headers, bold, lists — and nothing about which model produced it.

- It predicts the human winner 61.5% of the time (chance/majority 50.8%).
- Rank the 48 models by its style-only predictions and that ranking correlates 0.74 (Spearman) with the real win-rate ranking.
- Length carries almost all of it — the markdown features add ~nothing on top.

I'm not claiming models are equal or that Arena is useless — quality and style are entangled. But "cite Arena rank to pick a model" is partly citing formatting. Verbosity bias is known (Zheng 2023; LMSYS shipped a style-control adjustment in 2024); the part I hadn't seen shown is reproducing the leaderboard *order* with no model identity at all.

Runnable code + raw numbers (and the falsifier — style-controlled Elo would overturn it): <POST URL>

Where is this wrong?

> POST URL: https://dancenitra.github.io/agora/public/posts/chatbot-arena-style-not-skill.html

---
## REDDIT — Draft B: LLM-as-judge  → r/LocalLLaMA or r/LLMDevs

**Title:** On the original MT-Bench data, "pick the longer answer" reproduces about half of GPT-4-judge's agreement with humans

**Body:**
LLM-as-judge's headline is that GPT-4 agrees with human preferences ~80% of the time, on par with human–human — so it's a valid stand-in for human quality eval. On the original released votes (lmsys/mt_bench_human_judgments) I built a null judge that just picks the longer response — zero understanding.

- Length-only vs human votes: 68% (chance 50%).
- I reproduced the famous number first (GPT-4 vs human ≈ 84%) so it's apples-to-apples.
- The GPT-4 judge itself agrees with "pick the longer one" 73.5% of the time.

So a rule that understands nothing reproduces ~half of the judge's above-chance agreement. Not saying LLM judges are worthless — there's a real (smaller) semantic signal — but "80% agreement = valid quality judge" overstates it; use length controls and report the length-only null as your real baseline, not 50%.

Code + numbers: <POST URL>

> POST URL: https://dancenitra.github.io/agora/public/posts/llm-as-judge-length-confound.html

---
## HN — ⚠️ WARNING: DanceNitra HN account is SHADOWBANNED (all prior submissions [dead], invisible)
Do NOT post from DanceNitra — it won't be seen. Options: (1) email hn@ycombinator.com to appeal first;
(2) post from a different/aged account; (3) skip HN, focus Reddit. If/when an account works, ONE
combined submission is stronger than two:

**Title:** Length fakes the LLM judge and the Chatbot Arena leaderboard
**URL:** https://dancenitra.github.io/agora/public/crucible/index.html  (or the Arena post)
**First comment (context):** Two runnable nulls on public data: (1) "pick the longer answer" reproduces ~half of GPT-4-judge's 80% human agreement on MT-Bench; (2) a style-only model with no model identity reproduces ~74% of the Chatbot Arena leaderboard order. Verbosity bias is known; the new bit is reproducing the leaderboard *order* with no identity. Both have code + a pre-registered falsifier. Curious where these break.
