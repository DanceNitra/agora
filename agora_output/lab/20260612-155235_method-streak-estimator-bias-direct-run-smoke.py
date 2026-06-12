
import numpy as np
rng = np.random.default_rng(7)
k, n, p, reps = 3, 100, 0.5, 1000
def seq_stats(x):
    hh = oh = hm = om = 0; rh = rm = 0
    for t in range(len(x)):
        if rh >= k: oh += 1; hh += x[t]
        if rm >= k: om += 1; hm += x[t]
        if x[t]: rh += 1; rm = 0
        else: rm += 1; rh = 0
    return (hh/oh if oh else None), (hm/om if om else None)
D = []
for _ in range(reps):
    ph, pm = seq_stats((rng.random(n) < p).astype(np.int8))
    if ph is not None and pm is not None: D.append(ph - pm)
D = np.array(D); se = D.std(ddof=1)/np.sqrt(len(D))
print(f"MEASURED: E[D] = {D.mean():+.4f} (SE {se:.4f}, t={D.mean()/se:.1f}) on iid null, k={k} n={n} p={p}")
print(f"VERDICT: {'BIASED - a ~0 measurement implies a REAL effect of ~'+format(-D.mean(),'.3f') if abs(D.mean())>2*se else 'UNBIASED - the naive estimator is fine here'}")
