# quitkit — when to quit a depleting effort, with a measured threshold

> "Set exit criteria and ignore the sunk cost" is advice without a number. `quitkit` is the number:
> quit a yield process when its recent yield falls a fraction **θ ≈ 0.6** below its running peak (a
> drawdown stop), then reallocate. And the part most people miss — there's an **interior optimum**:
> quitting too early *and* too late both lose. One file, zero dependencies.
> A sibling of [mnemo](../mnemo) / [ragfresh](../ragfresh) / [nullcheck](../nullcheck) / [selfref](../selfref).

## The pain
A project, an ad campaign, a research line, a content series, a sales channel, a job-search source —
its yield decays as you exhaust it. When do you cut it and move to a fresh one? Persistence advice and
"sunk-cost" sermons don't give you a threshold, so people either grind a dead vein forever or bail at
the first bad week. There's a measured answer.

## Use it
```python
from quitkit import should_quit, Tracker

# you have your per-period yields so far (hits/misses, revenue, conversions, findings…)
should_quit(recent_yields)                 # -> {'quit': True/False, 'drawdown': 0.79, 'reason': '...'}
should_quit(recent_yields, theta=0.6)      # theta = how much of your peak you'll give back before cutting

# streaming: feed one period at a time
t = Tracker(theta=0.6, window=25)
for y in stream:
    v = t.update(y)
    if v["quit"]: break                    # drawdown stop hit — reallocate
```

## The measured threshold (`python quitkit.py`)
```
mine-to-depletion baseline: 811 findings (same budget)
theta=0.4: 2082    theta=0.5: 2364    theta=0.6: 2535  <- best    theta=0.7: 2374    theta=0.8: 2149
=> quit at theta=0.6 -> +213% vs mining to depletion
```
The curve **peaks at θ=0.6** and falls off on both sides — that's the interior optimum. (The numpy
reference model, Agora Lab `565aa7`, gives +239% at the same θ=0.6; the pure-stdlib demo here reproduces
≈+213%. The threshold is robust to the RNG; the lift is large either way.)

## Why an interior optimum, not "quit ASAP" or "never quit"
- **Too loose** (θ→1, mine to depletion): you pour effort into a vein long after its marginal yield
  has collapsed — the baseline above leaves ~⅔ of the findings on the table.
- **Too tight** (θ small): you abandon veins on normal noise before harvesting them, and churn through
  setup costs. Both tails lose; θ≈0.6 banks most of a vein then leaves before the dead zone.

## What it is / isn't
`quitkit` decides *when a declining effort has declined enough to cut* — a drawdown stop on yield. It is
not a forecast of whether a brand-new bet will pay off, and `window`/`theta` are levers you set to your
domain (default window 25 periods, θ 0.6 from the reference model). It turns "don't throw good money
after bad" into a rule you can actually run. Open-core; the core stays free.
