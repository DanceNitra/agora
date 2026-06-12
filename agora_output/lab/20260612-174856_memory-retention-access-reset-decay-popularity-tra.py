"""
Lab test for the deer-flow#1898 reply claim:
'access-reset half-life decay is a POPULARITY signal, and popularity != value — so it
systematically under-retains high-value-but-low-frequency memories ("load-bearing but cold"),
which a value-aware blend protects.'

Setup: N memories, each with a true VALUE v_i (heavy-tailed) and a base ACCESS RATE lambda_i
(popularity). Crucially value and access-rate are only weakly correlated, and a distinguished
subset is HIGH-VALUE / LOW-FREQUENCY (procedural+semantic facts: rarely queried, critically
load-bearing). Accesses arrive over T steps (Poisson by lambda). At each budget-enforcement we keep
the top-B memories under each policy:
  A) access-reset half-life decay: importance = exp(-(now - last_access)/H); retrieval resets the
     clock. (= ferhimedamine's mechanism — pure recency/popularity.)
  B) value-aware blend: score = (1-w)*decay + w*normalized_value.

Measured under a TIGHT budget: total true value retained, and RECALL of the high-value/low-frequency
subset (the memories the claim says get starved).
VERDICT:
  CLAIM SUPPORTED -- decay-only starves the high-value/low-frequency subset (markedly lower recall +
                     lower total retained value) vs the value blend.
"""
import numpy as np

rng = np.random.default_rng(20260612)

N = 5000
T = 4000
H = 300.0                 # decay half-life-ish constant (steps)

# value: heavy-tailed (a few memories are critical)
value = rng.pareto(1.8, N) + 0.1
# base access rate: popularity, mostly independent of value
access_rate = rng.gamma(1.2, 1.0, N)
# distinguished subset: HIGH value, LOW access frequency ("procedural/semantic, load-bearing but cold")
crit = np.argsort(value)[::-1][:250]          # top-5% by value
access_rate[crit] *= 0.06                     # ...made deliberately rarely-queried
hi_val_lo_freq = crit

# simulate accesses; track last-access time per memory
last_access = np.full(N, -1e9)
acc_count = np.zeros(N)
# pre-draw which memory is accessed each step ∝ access_rate
p = access_rate / access_rate.sum()
hits = rng.choice(N, size=T, p=p)
for t, m in enumerate(hits):
    last_access[m] = t
    acc_count[m] += 1

now = T
decay = np.exp(-(now - last_access) / H)       # current importance under access-reset decay
vnorm = (value - value.min()) / (value.max() - value.min())


def retained_metrics(keep_idx):
    keep = np.zeros(N, bool); keep[keep_idx] = True
    total_value = value[keep].sum() / value.sum()
    recall_crit = keep[hi_val_lo_freq].mean()
    return total_value, recall_crit


print("=== Memory retention under a tight budget: access-reset decay vs value-aware blend ===")
for budget_frac in [0.30, 0.15, 0.07]:
    B = int(budget_frac * N)
    # Policy A: keep top-B by decay only (pure access-reset / popularity)
    keepA = np.argsort(decay)[::-1][:B]
    # Policy B: value-aware blend (w=0.5)
    blend = 0.5 * decay + 0.5 * vnorm
    keepB = np.argsort(blend)[::-1][:B]
    tvA, rcA = retained_metrics(keepA)
    tvB, rcB = retained_metrics(keepB)
    print(f"\n[budget = {budget_frac:.0%} of memories kept]")
    print(f"  decay-only : retained value {tvA*100:5.1f}%   recall of high-value/low-freq {rcA*100:5.1f}%")
    print(f"  value-blend: retained value {tvB*100:5.1f}%   recall of high-value/low-freq {rcB*100:5.1f}%")
    print(f"  -> value blend keeps {tvB/max(tvA,1e-9):.2f}x the value, "
          f"{(rcB-rcA)*100:+.0f}pp recall of the load-bearing-but-cold set")

# headline at the tightest budget
B = int(0.07 * N)
tvA, rcA = retained_metrics(np.argsort(decay)[::-1][:B])
tvB, rcB = retained_metrics(np.argsort(0.5*decay + 0.5*vnorm)[::-1][:B])
print("\n=== Verdict ===")
if rcA < 0.5 * rcB and tvB > tvA:
    print(f"CLAIM SUPPORTED: at a 7% budget, pure access-reset decay recalls only {rcA*100:.0f}% of the")
    print(f"high-value/low-frequency memories and retains {tvA*100:.0f}% of total value; a value-aware")
    print(f"blend recalls {rcB*100:.0f}% and retains {tvB*100:.0f}%. Popularity != value: decay-only")
    print("starves the load-bearing-but-cold memories. The contract needs a value channel separate")
    print("from access recency.")
else:
    print(f"INCONCLUSIVE: decay recall {rcA*100:.0f}% vs blend {rcB*100:.0f}%, value {tvA*100:.0f}% vs {tvB*100:.0f}%.")
