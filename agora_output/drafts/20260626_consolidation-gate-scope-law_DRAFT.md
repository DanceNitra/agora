<!--
GATED DRAFT — NOT FOR PUBLICATION WITHOUT OWNER APPROVAL.
Owner: review, then decide Crucible entry vs storefront post. Bilingual EN/SK rendering happens at
publish time (tools/render_post.py). All numbers verified against Labs 84b6b7 / 0f030e / 10cdf9 /
c509ba / a0e420 (re-run in-cycle, cloud-free, pure-numpy + real nomic embeddings of real LoCoMo turns).
No-overclaim check done: prior art cited, strong baselines (tuned EWMA/mean/median), framed as a scope
law not a SOTA win, minimal-model + single-embedder caveats stated up front.
-->

# When should an AI's memory *refuse* to believe what it just saw?

**A measured scope law for memory-consolidation operators — and why robustness to poisoning and sensitivity to sudden change are two ends of the same stick.**

Give an AI agent a long-running memory and you immediately face a dirty question: when a new observation contradicts what's stored, is it **new truth** (update fast!) or **poison** (ignore it!)? Every memory system answers this implicitly through its *consolidation operator* — the rule that turns repeated, noisy, sometimes-adversarial observations of a fact into one stored value. We measured what that choice actually costs.

This is deliberately a **minimal-model** study (small, fully reproducible simulations + real-embedding checks on one embedder). It is not a benchmark of a production system. The point is a *law and a design rule*, with every number reproducible from the linked scripts.

## The frontier nobody gets to skip

Track a value over time from noisy observations. Two failure modes pull in opposite directions:

- **Adapt fast** to genuine change → weight recent observations heavily (a fast exponential moving average, EWMA). But then a single adversarial spike moves your estimate a lot.
- **Resist poison** → average over a long window (slow EWMA, or a plain mean). But then you lag real change.

Sweeping the EWMA decay rate traces a clean **speed↔robustness frontier**. This part is textbook — it is the classic bias/variance and *breakdown-point* tradeoff from robust statistics (Huber; Hampel's influence functions), and the median/trimmed-mean robustness used in Byzantine-robust learning. We use it only as the **baseline**.

## The coupling (the part that isn't textbook)

mnemo — our open memory core — uses a **corroboration gate**: admit a new observation into the stored estimate only if several recent observations corroborate it; reject isolated outliers. In a minimal scalar model the gate does something the frontier can't: it makes the **breakdown bounded** — as an adversarial spike grows from 8σ to 32σ, a fast EWMA's error grows *linearly* while the gate stays flat (it simply rejects the spike).

But the **same mechanism** that rejects an isolated poison spike must, by construction, also reject the **first sample of a genuine sudden change** — to a corroboration test the two are identical. So:

> **The Consolidation-Gate Coupling.** A consolidation operator with bounded breakdown under poisoning is, by the same mechanism, lagged on uncorroborated sudden novelty. Tightening the gate (requiring more corroboration) *monotonically* improves poison-robustness **and** worsens response to sudden change — one knob, opposite effects. (Measured: across gate strictness k=3→6, robustness and jump-lag move in lockstep, every run.)

## The scope: when does the gate actually help?

Here is the honest part — and a result that surprised us. The gate's advantage is **bounded breakdown against an *unbounded* attack**. So it only pays off when observations can be unboundedly large:

- **Unbounded-magnitude memory** (counts, scores, prices, durations, latencies — which are genuinely heavy-tailed; our own system's task durations run median 0.5s, mean 5.1s, max 60s). Here, even under realistic heavy-tailed (Student-t) noise, the gate **escapes the frontier**: as the adversarial spike scales 30× (×5→×150), the gate's error stays flat (~0.5 MAE) while a tuned EWMA's climbs from 0.8 to **22.3** and a plain mean's from 0.2 to **5.5**. **The gate wins.**
- **Bounded embedding recall** (unit-norm vectors — what most "AI memory" actually stores). We tested this on **real nomic embeddings of 240 real LoCoMo conversation turns**. Result: the gate **does not escape** the frontier — a tuned EWMA, or even a plain mean, *dominates* it. Why: a unit-norm poison vector has bounded influence, so every operator already has bounded breakdown; the gate's rejection buys nothing and its novelty-blindness is pure cost. (Operational note: raw nomic is anisotropic — all cosines compress to 0.75–0.81 — so you must **center** the embeddings before any outlier logic has signal.)

> **Scope law.** A corroboration gate Pareto-helps **iff the observation magnitude is unbounded**. For bounded embedding recall, use a tuned decay. The coupling holds in both regimes; the *benefit* does not.

## Can you escape the coupling? Yes — into a latency floor

If one operator can't have both, use two. A **two-channel consolidator** — a corroboration-gated *slow* channel + a fast channel + a **persistence selector** that switches to the fast channel only once a deviation has persisted ≥ d steps — **beats every single operator**: bounded poison-robustness *and* fast response to sustained change.

But the coupling doesn't vanish; it **transforms into a detection-latency floor**. With zero waiting (d=1) robustness collapses — you cannot tell an isolated spike from the *onset* of a real change until you see whether it persists. Robustness reaches its floor at d≈2–3 steps.

> **Irreducible core.** Telling poison from genuine novelty requires observing ≥ d corroborating steps. Architecture converts the robustness↔novelty *tradeoff* into a fixed *detection latency* — escapable in design, irreducible in information.

## What this means if you build agent memory

- **Don't gate embedding recall.** Use a tuned decay (or a mean for stable facts). Centering first is mandatory for nomic-style embeddings.
- **Do gate unbounded-magnitude memory** (counts, scores, prices, durations): a corroboration gate bounds the damage from arbitrarily large poison.
- **For memory that must survive both poison *and* legitimate regime changes**, use two channels with a persistence selector, and tune the confirmation delay `d` to the expected poison burst length (≈ burst + 1). Accept that you cannot get robust novelty-detection at zero latency.

## Honest caveats

Minimal computational models throughout; the embedding leg uses **one** embedder (nomic) on **one** conversational corpus — the bounded-embedding null could shift with a different geometry. The latency-floor claim is demonstrated mechanistically, not proven as a formal impossibility. These are *design laws to test in production*, not benchmark wins.

## Reproducibility

Five self-contained scripts (pure-numpy + local embeddings; no cloud): episodic-control seed `84b6b7`, scalar coupling `0f030e`, real-embedding scope test `10cdf9`, heavy-tailed confirmation `c509ba`, two-channel capstone `a0e420`.

## Prior art

Robust statistics & breakdown point (Huber 1964; Hampel 1974); robust/Byzantine aggregation (median, trimmed mean); max-operator overestimation (van Hasselt 2010, Double Q-learning); Model-Free Episodic Control (Blundell et al. 2016). Our contribution is the *unified scope law* across consolidation operators for agent memory, the *coupling*, and the *two-channel → latency-floor* resolution — not any single one of those pieces.
