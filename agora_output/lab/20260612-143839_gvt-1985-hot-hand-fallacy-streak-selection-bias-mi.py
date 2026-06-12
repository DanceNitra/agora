"""
Replication: Gilovich, Vallone & Tversky (1985) "The hot hand in basketball:
On the misperception of random sequences" (Cognitive Psychology 17).

THE CANONICAL CLAIM under test: GVT measured P(hit | streak of 3 hits) vs
P(hit | streak of 3 misses) in finite shooting records, found no positive difference,
and concluded the hot hand is a cognitive illusion. The method's implicit premise:
for a shooter with NO hot hand, the conditional estimates are unbiased, so
"difference ~ 0" means "no streak effect".

THE TEST (Miller & Sanjurjo 2018, Econometrica): that premise is false. Selecting
trials that FOLLOW a streak inside a fixed finite sequence is a biased selection -
the streak-selection bias. We measure it exactly by simulation:

  1) i.i.d. Bernoulli(p) shooters (no hot hand BY CONSTRUCTION), n shots.
     Estimator D = Phat(hit|k prior hits) - Phat(hit|k prior misses), sequence-level
     average (GVT's design). If the method were sound, E[D] = 0.
  2) The flip: inject a REAL hot hand of size delta (P(hit) rises by delta after k
     consecutive hits) and find the delta at which GVT's estimator reads ZERO -
     i.e. what a GVT-zero actually implies.

VERDICT RULE:
  FAILED      -- E[D] is significantly NEGATIVE for an iid shooter (the method
                 manufactures an anti-hot-hand signal; GVT's "~0" then implies a
                 positive hot hand), i.e. the claim's mechanism does not compute.
  REPRODUCED  -- E[D] ~ 0 for iid shooters (the method is unbiased after all).
"""
import numpy as np

rng = np.random.default_rng(20260612)


def seq_stats(x, k):
    """Phat(hit | k prior consecutive hits), Phat(hit | k prior consecutive misses)
    within one finite sequence x (GVT's per-record estimator). None if no opportunity."""
    n = len(x)
    hits_after_h = opp_h = hits_after_m = opp_m = 0
    run_h = run_m = 0
    for t in range(n):
        if run_h >= k:
            opp_h += 1
            hits_after_h += x[t]
        if run_m >= k:
            opp_m += 1
            hits_after_m += x[t]
        if x[t] == 1:
            run_h += 1; run_m = 0
        else:
            run_m += 1; run_h = 0
    ph = hits_after_h / opp_h if opp_h else None
    pm = hits_after_m / opp_m if opp_m else None
    return ph, pm


def iid_bias(p, n, k, reps):
    """E[Phat_H], E[Phat_M], E[D] across iid sequences (sequences lacking an
    opportunity are dropped from that side, as in GVT)."""
    PH, PM, D = [], [], []
    for _ in range(reps):
        x = (rng.random(n) < p).astype(np.int8)
        ph, pm = seq_stats(x, k)
        if ph is not None: PH.append(ph)
        if pm is not None: PM.append(pm)
        if ph is not None and pm is not None: D.append(ph - pm)
    D = np.array(D)
    se = D.std(ddof=1) / np.sqrt(len(D))
    return np.mean(PH), np.mean(PM), D.mean(), se, len(D)


def hot_shooter(p, delta, n, k):
    """A shooter with a REAL hot hand: P(hit) = p + delta when the last k shots
    were all hits, else p."""
    x = np.empty(n, dtype=np.int8)
    run = 0
    for t in range(n):
        prob = p + delta if run >= k else p
        x[t] = 1 if rng.random() < prob else 0
        run = run + 1 if x[t] == 1 else 0
    return x


def hot_D(p, delta, n, k, reps):
    D = []
    for _ in range(reps):
        ph, pm = seq_stats(hot_shooter(p, delta, n, k), k)
        if ph is not None and pm is not None:
            D.append(ph - pm)
    D = np.array(D)
    return D.mean(), D.std(ddof=1) / np.sqrt(len(D))


REPS = 6000
print("=== GVT (1985) hot-hand method on an iid shooter (NO hot hand by construction) ===")
print("    (if the method were unbiased, every D below would be ~ 0)")
for p, n, k in [(0.5, 100, 3), (0.5, 100, 2), (0.5, 100, 4), (0.46, 100, 3), (0.5, 248, 3)]:
    ph, pm, d, se, m = iid_bias(p, n, k, REPS)
    print(f"  p={p:.2f} n={n} k={k}:  E[P(hit|{k}H)]={ph:.4f}  E[P(hit|{k}M)]={pm:.4f}  "
          f"E[D]={d:+.4f} (SE {se:.4f}, t={d/se:.1f})  [{m} usable seqs]")

print("\n=== The flip: how big a REAL hot hand reads as ZERO under GVT's estimator ===")
print("    (p=0.50, n=100, k=3 — GVT's typical per-player record size)")
for delta in [0.00, 0.04, 0.08, 0.10, 0.13]:
    d, se = hot_D(0.5, delta, 100, 3, 4000)
    print(f"  true hot hand delta=+{delta:.2f}:  measured D={d:+.4f} (SE {se:.4f})")

print("\n=== Verdict ===")
ph, pm, d, se, m = iid_bias(0.5, 100, 3, REPS)
if d < -2 * se:
    print(f"FAILED: GVT's estimator is biased {d:+.3f} (t={d/se:.0f}) on a shooter with NO hot hand.")
    print("A measured difference of ~0 in their data is therefore evidence FOR a positive hot")
    print("hand of roughly the bias magnitude - the canonical 'fallacy' was itself the fallacy")
    print("(Miller & Sanjurjo 2018). The claim's mechanism does not compute.")
elif abs(d) <= 2 * se:
    print("REPRODUCED: the estimator is unbiased; GVT's inference stands.")
