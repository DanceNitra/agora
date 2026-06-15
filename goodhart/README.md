# goodhart — when a measure becomes a target, it stops measuring. How gameable is *your* proxy?

> Reward models, KPIs, OKRs, eval benchmarks, ad metrics — the moment you optimize a proxy, the proxy
> reward keeps rising while the **true goal peaks and then declines** (reward hacking / Goodhart's law).
> `goodhart` measures how fast your proxy stops tracking the goal, and how many independent metrics it
> takes to fix it. One file, zero dependencies.
> A sibling of [nullcheck](../nullcheck) / [idcheck](../idcheck) / [mnemo](../mnemo).

## The measured decay (`python goodhart.py`)
```
select the top 10% by a single proxy, as gameability rises:
   gameability | proxy-goal corr | precision (selected are truly top)
           0.0 |            0.96 |        79%
           0.5 |            0.87 |        64%
           1.0 |            0.69 |        46%
           2.0 |            0.44 |        30%
           4.0 |            0.24 |        20%
```
At gameability 0 the proxy picks the genuinely-best 79% of the time. Optimize a more gameable proxy and
that collapses to **20%** — you're selecting things that win on the loophole, not the goal.

## Use it
```python
from goodhart import fidelity, metrics_needed, audit

fidelity(2.0)               # -> precision 0.30, proxy_goal_corr 0.44  (a heavily-gamed proxy)
metrics_needed(1.0)         # -> need >= 10 independent metrics to hold precision >= 70%
audit(2.0, n_metrics=1)     # -> "GAMED — precision 30%; the target has stopped measuring the goal"
audit(2.0, n_metrics=5)     # -> "DEGRADED — ... change the metric"
```

## The fix, and its honest limit
The literature's advice is right — "it's harder to game five metrics than one" — and we measured it:
combining `m` **independent** proxy metrics averages the gameable noise down (effective gameability
≈ λ/√m), so precision recovers with m. But it's not free: at gameability 1 you need ~10 independent
metrics to get back to 70%, and at gameability 2 no realistic number of metrics gets there — at that
point the honest move is to **change what you measure**, not pile on more of the same. `metrics_needed`
tells you which regime you're in.

## Why this matters in 2026
This is the mechanism behind reward hacking in RLHF (the proxy reward rises while true capability
stalls), gamed eval benchmarks, and every KPI/OKR that drifts from the thing it was supposed to track.
`goodhart` turns "is our metric still measuring the right thing?" into a number and a concrete fix.
Grounded in Agora Lab `e97ad5`; open-core, the core stays free.
