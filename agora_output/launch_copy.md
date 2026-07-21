# Distribution launch copy — option (a)

All numbers below were re-verified against their source labs/demos on 2026-06-15.
**Gated: Rasto posts these.** Repo link: https://github.com/DanceNitra/agora  ·  Blog: https://dancenitra.github.io/agora/
Self-audit page (the strongest hook): https://dancenitra.github.io/agora/public/self-audit/

After posting, run `python tools/distribution_metrics.py` each cycle — per-tool repo click-through +
referrers reveal which tool is the wedge.

---

## ★ PRIMARY hook — Show HN, led by the self-audit (use this one first)

**Title:**
`Show HN: I built an autonomous research company that audits itself with its own 8 open-source tools`

**URL:** `https://dancenitra.github.io/agora/public/self-audit/`

**First comment:**

> I run an autonomous research setup (agents that pull real papers, test claims in code, and only keep
> what reproduces). Its public output is eight zero-dependency Python tools — agent memory, RAG
> freshness, an is-this-number-real check, a model-collapse governor, a when-to-quit threshold, a
> causal bad-control auditor, a proxy-gameability (reward-hacking) check, and a multi-agent herding
> check. Each ships a runnable, measured benchmark.
>
> The fun part: I turned all eight on the system *itself*, on real internal data. It came back 8/8
> healthy — not at model-collapse risk (94% of inputs externally grounded), agents not herding
> (diverse across 89 topics), research not depleting, internal metric not gamed (standing↔value corr
> 0.83) — and it **caught two real gaps I then fixed** (the memory wasn't consolidating; 291 grounded
> contributions but 0 marked verified). Fixing them even made the audit's own null-test find a real
> signal (grounded items verify 55% vs 0% ungrounded). The audit page is the link; the tools + code
> are at github.com/DanceNitra/agora. `pip install` or copy a file; each has an MCP server. Open-core,
> cores free. Honest feedback — and which tool you'd actually use — is what I'm after.

---

## Show HN (news.ycombinator.com/submit)

**Title:**
`Show HN: Five one-file Python tools, each with a measured benchmark`

**URL:** `https://github.com/DanceNitra/agora`

**First comment (post immediately after):**

> I run an autonomous research setup that only keeps results it can reproduce, and I distilled five of
> them into zero-dependency, single-file tools. Each ships with a runnable benchmark — the rule was
> "measured, not assumed," so you can re-run the claim yourself:
>
> - **inspeximus** — agent memory + a self-maintaining notes layer: value-ranked recall, consolidation,
>   dead-link/orphan/stale repair.
> - **ragfresh** — a freshness/decay layer for RAG/vector stores. Ranking by value×freshness retained
>   **96%** of an oracle's quality on a held-out set vs **52%** for recency-only (+83%).
> - **nullcheck** — "is this number real or noise?": simulates the no-effect null at your sample sizes.
>   A +15% A/B lift on n=1k reads as **noise (p=0.28)**; +18% on n=10k is **real (p=0.0001)**; peeking
>   5× inflates false positives **2.7×**.
> - **selfref** — a governor for systems that train on their own output (model collapse). With no real
>   data **94%** of runs collapse; a **~5%** real-data anchor cuts that to ~10%. Plus the
>   self-confirmation lock: a self-trust exponent p>1 permanently locks bias (p=2 → **50%**).
> - **quitkit** — when to quit a depleting effort: a drawdown-exit threshold (θ≈0.6, an interior
>   optimum — too early and too late both lose) beats mining-to-depletion by **+239%** in the reference
>   model.
>
> `pip install` or copy a file; each also has an MCP server so an agent can call it. Open-core, cores
> free, honest caveats in each README. I'd genuinely like to know **which one is most useful to you** —
> I'm trying to learn which of these people actually need.

---

## Reddit r/LocalLLaMA or r/MachineLearning

**Title:**
`Five zero-dependency tools for agent memory / RAG hygiene / model-collapse, each with a runnable benchmark`

**Body:**

> Open-sourced five single-file tools I built for an autonomous research agent setup. No dependencies,
> each with a measured demo you can re-run:
>
> - **inspeximus** — agent long-term memory + self-maintaining notes (value-ranked recall, consolidation).
> - **ragfresh** — RAG/vector-store freshness layer; value×freshness kept 96% of oracle quality vs 52%
>   for recency-only.
> - **nullcheck** — A/B / metric sanity by null simulation (a +15% lift on 1k samples is p=0.28 noise;
>   peeking inflates false positives 2.7×).
> - **selfref** — model-collapse / self-reference governor (no real data → 94% of runs collapse; ~5%
>   anchor fixes it; self-trust p>1 locks 50% of a bias at p=2).
> - **quitkit** — when-to-quit drawdown threshold (θ≈0.6 beats mine-to-depletion +239%).
>
> Each has an MCP server so Claude/Cursor/any agent can call it. Repo + benchmarks:
> https://github.com/DanceNitra/agora — feedback on which is most useful is what I'm after.

---

## One-line pitch (X / replies)

> Five one-file Python tools, each with a runnable benchmark: agent memory (inspeximus), RAG freshness
> (ragfresh), is-this-number-real (nullcheck), model-collapse governor (selfref), when-to-quit
> (quitkit). Zero deps, MCP-ready, open-core. https://github.com/DanceNitra/agora
