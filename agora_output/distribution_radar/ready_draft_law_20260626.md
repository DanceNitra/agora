# GATED Reddit distribution draft — Adaptation-Corruption law post (2026-06-26)

Owner posts MANUALLY. Native self-post, humble framing, link at the end. Numbers verified vs .lab.json
(trust f490d8: 6.08/2.51/2.42; real-data b0ed58: 16 NAB streams, sustained 0/6 for naive, ASG 0-vs-1181).
Do NOT reuse an identical hook elsewhere. After posting: reply to comments (that is where the value is).

## Best target
r/LLMDevs (agent-memory topic is live there right now) OR r/Rag (smaller, exactly on-topic).
Flair: Discussion. Post as a TEXT self-post (not a link post).

## Title
Four agent-memory decisions turned out to be the same problem — and the fix is "change detection"

## Body
Building a memory layer for agents, I kept hitting the same wall in four different places:

- **what to forget** (consolidation),
- **when to believe a fact that contradicts what you already stored**,
- **how fast to stop trusting a source that goes bad**,
- **how many samples to take before you trust the best one** (best-of-N).

They look separate, but they're the same tradeoff: a single update rule is either too fast (one poisoned/odd input flips your memory) or too slow (it lags a real change). The reason is annoying but fundamental — at the instant something deviates, an isolated bad input and the first sample of a genuine change are *the same observation*. You can't tell them apart until you see whether it **persists**.

That's just **sequential change detection**, which has a known-optimal answer (CUSUM). So the practical fix isn't tuning a decay rate — it's a persistence-based update: confirm a change over a few corroborating samples before you commit, with the confirmation window set to how transient your noise is vs how fast real change happens.

I tried to falsify the "persistence is better" claim on real data instead of just sims — 16 expert-labelled anomaly streams (Numenta Anomaly Benchmark). The honest result is an **asymmetry**, not a clean rule:

- On every **sustained** change, a persistence detector wins or ties — the naive point rule never won one (e.g. a server misconfiguration: **0 vs 1181** false alarms for the same recall).
- The naive rule only ever wins on **transient spikes**.
- So "is the genuine change sustained?" tells you which to use. The converse isn't clean (some transient anomalies persist enough that persistence still wins).

Caveats I'd want pointed out if I were reading this: it's a unification of known ideas, not a new theorem; the size of the gain is regime-dependent (shrinks to ~0 when changes are big and the signal is clean); and the persistence approach is exactly *wrong* if the signal you care about is itself a brief spike.

Full writeup with the numbers + the reproducible sims (and where it provably breaks):
https://dancenitra.github.io/agora/public/posts/adaptation-corruption-separation-law.html

Curious whether others building agent memory have hit the same gullible-vs-rigid wall, and what you did about it.

## Alternative (lower effort, also good): a COMMENT, not a self-post
On r/LLMDevs thread "RAG has not felt like enough for agent memory, at least in my testing"
(reddit.com/r/LLMDevs/comments/1ubqyqk) — but we already commented there once, so skip unless replying to someone.
