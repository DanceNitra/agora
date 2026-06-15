# selfref — is your AI quietly training on itself?

> Any system that learns from its **own output** is a strange loop: a model retrained on synthetic
> data, an agent whose memory is its past generations, a RAG store indexing the system's prior
> answers, a recommender fed by the clicks it shaped. Strange loops fail in two measured ways.
> `selfref` measures both at *your* settings. One file, zero dependencies.
> A sibling of [mnemo](../mnemo) / [ragfresh](../ragfresh) / [nullcheck](../nullcheck).

## The two failure modes (and the two knobs that fix them)

**1. Collapse — the data-mix law.** Retrain recursively on your own outputs and diversity drains
away (the "curse of recursion" / model collapse — a documented 2026 production concern, not just a
paper). The cure is a floor of real/external data, and we **measured the floor**:

```python
from selfref import collapse_risk, min_external_anchor
collapse_risk(0.0)["collapse_rate"]    # pure self-training -> ~0.92  (most runs lose their diversity)
collapse_risk(0.05)["collapse_rate"]   # 5% real data      -> ~0.06  (the knee)
collapse_risk(0.20)["collapse_rate"]   # 20% real data     -> ~0.01  (clean)
min_external_anchor()                   # -> "Keep >= ~5-10% of inputs real/external"
```

**2. Lock — the self-trust law.** If a system weights its *own prior belief* faster than fresh
evidence can correct it (self-trust exponent `p > 1`), a fixed fraction of any initial bias is
**never** washed out — no matter how much data arrives. Closed form, exact:

```python
from selfref import lock_fraction, lock_risk
lock_fraction(1.0)   # 0.00  — p<=1 is the safe boundary, bias washes out
lock_fraction(1.5)   # 0.177 — 17.7% of any bias is locked in permanently
lock_fraction(2.0)   # 0.500 — half of it, forever
lock_fraction(3.0)   # 0.809
lock_risk(2.0)["verdict"]   # "LOCK — p=2 permanently locks 50% of any bias; no amount of data corrects it"
```

**One combined call:**
```python
from selfref import audit
audit(external_fraction=0.0,  self_trust_p=2.0)["overall_verdict"]   # "COLLAPSE"  (+ the fix)
audit(external_fraction=0.20, self_trust_p=1.0)["overall_verdict"]   # "SAFE"
```

## Measured (`python selfref.py`)
```
COLLAPSE law — recursive self-training:
   real fraction f   mean diversity   collapse rate
              0.00            0.250            92%
              0.05            1.161             6%
              0.20            1.005             1%
LOCK law — permanent self-confirmation bias:
   p=1.0: 0.0000 (SAFE)   p=1.5: 0.1771 (WATCH)   p=2.0: 0.5000 (LOCK)   p=3.0: 0.8094 (LOCK)
```

## How to read it for a real system
- **external_fraction** = the share of your training/retrieval inputs that are *real/external* (human
  data, fresh ground truth) rather than self-derived (the model's own outputs, synthetic data, prior
  generations). Keep it above the measured knee (~5%, and ≥20% for clean).
- **self_trust_p** = how aggressively your update rule re-weights its own prior vs new evidence. The
  field test: inject a known bias, then keep feeding *unbiased* data — if the bias **doesn't decay**
  as you add more, you're at `p > 1` and it's permanently locked. Cap self-trust so the prior never
  out-weights fresh evidence.

## Why this, not a vibe
Both laws are *measured*, not asserted — `selfref` reproduces Agora Lab **75db49** (the strange-loop
attractor): the recursive-self-training collapse and the `p>1` permanent lock. The peer-reviewed
literature agrees on the cure (accumulate real + synthetic data; replacing real with synthetic grows
error without bound) — `selfref` turns that into a number you can put a threshold on. Open-core; the
core stays free.
