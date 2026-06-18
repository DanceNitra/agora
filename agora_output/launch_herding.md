# Distribution piece #1 — multi-agent herding (insight, not a product pitch)

**Goal:** put one genuinely interesting, true result in front of real AI people and see if it resonates.
NOT selling anything. The open-source tool is mentioned once, at the end, as "check it yourself."
**Gated: Rasto posts.** All numbers re-verified 2026-06-15 (herdcheck, Lab 678a9c + red-team 14becd).

Links to use:
- deep-dive: https://dancenitra.github.io/agora/public/posts/why-crowds-get-dumber-when-they-watch-each-other-and-the-sur.html
- the one-file model/tool (open source): https://github.com/DanceNitra/agora/tree/main/herdcheck

---

## Hacker News — submit the deep-dive link with this title

**Title (pick one):**
1. `Multi-agent LLMs get dumber than their best member once the agents see each other`
2. `We measured when multi-agent LLM systems start herding: at two visible peers`

**URL:** the deep-dive link above.

**First comment (post right after, seeds the discussion):**

> "More agents = better" kept bugging me, so I measured it on the simplest honest model: N agents, each
> gets a private signal (~60% accurate), then sees `k` other agents' *answers*, updates, and acts.
> Collective accuracy:
>
> - k=0 (independent): ~100%
> - k=1: ~90%
> - **k=2: ~64%** — barely above a single agent (60%)
>
> The collapse is sharp and early. Once an agent weights the answers it observes more than its own
> evidence (threshold ≈ own-weight + 1 peer), the crowd herds and stops aggregating — and adding more
> peers past that does nothing.
>
> Then I tried to kill my own result, because it looked too clean. It is: the collapse is specific to
> *naive* updating — agents treating a peer's verdict as a fresh, independent fact. If agents discount
> the redundancy in correlated answers (a peer's answer already baked in whatever they saw), or share
> *evidence* instead of *verdicts*, the collapse mostly vanishes — back near 100% at the same k. So the
> fix isn't fewer agents; it's how they combine.
>
> Lines up with some 2026 results where heterogeneous multi-agent teams fail to beat their best single
> member. The model is one open-source file if you want to poke holes in it (herdcheck). Genuinely
> curious whether people running agent swarms in production see this — and at what k it bites for you.

---

## Reddit — r/LocalLLaMA (or r/MachineLearning)

**Title:** `I measured when multi-agent LLM setups start herding — it hits at 2 visible peers, and it's brutal`

**Body:**

> Everyone's bolting more agents together right now, so I wanted a number for when "more agents" stops
> helping. Simplest model I could defend: each agent gets a private ~60%-accurate signal, then sees `k`
> other agents' answers before deciding.
>
> - independent (k=0): collective ~100%
> - k=1: ~90%
> - k=2: ~64% — essentially a single agent (60%)
>
> It collapses the moment observed answers outweigh an agent's own evidence (threshold k_c = own-weight
> + 1), and stays collapsed for higher k. The crowd stops being a crowd.
>
> The honest part: I red-teamed it. The collapse only happens with *naive* social updating — treating a
> peer's conclusion as independent evidence. Discount the redundancy (a peer's verdict isn't independent
> of what they saw), or pass evidence instead of verdicts, and it goes back to ~100%. The fix is the
> aggregation rule, not the agent count.
>
> One-file model + the check are open source (herdcheck) if you want to break it. What I actually want to
> know: does this match what you see building agent systems? Where does it bite for you?

---

## X / thread (3 posts)

1. "more agents = better" is mostly wrong. I measured it: a crowd of LLM-ish agents is ~100% accurate
   when independent, but drops to ~64% (≈ a single agent) the moment each one sees just 2 peers' answers.
   Herding is sharp and early. 🧵
2. The threshold: collapse starts once observed answers outweigh an agent's own evidence (k_c =
   own-weight + 1). More peers past that don't help — the crowd already stopped aggregating.
3. The fix isn't fewer agents — it's how they combine. Discount redundant peer answers, or share
   evidence not verdicts, and accuracy goes back to ~100%. One-file open-source model if you want to
   break it: github.com/DanceNitra/agora/tree/main/herdcheck

---

## Notes for Rasto
- This is a *listening* move. Success = real comments/questions/DMs from people building agent systems,
  not upvotes. If it resonates → there may be a real audience (and later, real clients) around
  "the people who actually measure agent reliability." If it lands flat → we learned cheaply, pick the
  next result.
- Post ONE place first (HN or r/LocalLLaMA), watch the response for a day, then decide on the others.
- No product, no pitch. Just the work.
