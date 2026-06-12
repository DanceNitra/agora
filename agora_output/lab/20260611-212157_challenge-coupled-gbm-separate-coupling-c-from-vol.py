"""
Challenge to insight 'one coupling parameter turns textbook GBM into a crash-prone market'.

The belief attributes fat tails + volatility clustering to the cross-asset COUPLING c, with the
table covarying c and g (vol feedback) together so they can't be separated. But structurally the
return is r = sqrt(v)*[(1-c)*eps + c*z] with eps, z Gaussian — a mix of two Gaussians is STILL
Gaussian. So coupling c alone cannot create excess kurtosis; only the stochastic-volatility term
v = 1 + g*|market return| can. Test: drive c and g INDEPENDENTLY.

Prediction (the challenge): (c>0, g=0) stays kurtosis ~3 with ~0 clustering (Gaussian), while
(c=0, g>0) produces the fat tails and clustering. If so, the belief's tail-attribution to
'coupling' is mis-stated and should be REVISED: g generates the stylized facts; c generates
systemic co-movement, a different fact.
"""
import numpy as np

rng = np.random.default_rng(5)
N, T = 40, 4000


def simulate(c, g):
    eps = rng.standard_normal((T, N))
    z = rng.standard_normal(T)
    r = np.zeros((T, N))
    mkt_prev = 0.0
    for t in range(T):
        v = 1.0 + g * abs(mkt_prev)
        r[t] = np.sqrt(v) * ((1 - c) * eps[t] + c * z[t])
        mkt_prev = r[t].mean()
    pooled = r.reshape(-1)
    kurt = float(((pooled - pooled.mean()) ** 4).mean() / (pooled.var() ** 2))   # ~3 if Gaussian
    mkt = r.mean(axis=1)
    a = np.abs(mkt)
    ac1 = float(np.corrcoef(a[:-1], a[1:])[0, 1])                                 # vol clustering
    # average pairwise cross-asset correlation (the systemic co-movement c is supposed to drive)
    cc = np.corrcoef(r.T)
    avg_corr = float((cc.sum() - N) / (N * (N - 1)))
    return kurt, ac1, avg_corr


print(f"{'(c, g)':>12} {'kurtosis':>9} {'vol-cluster AC1':>16} {'avg pair corr':>14}   note")
cases = [((0.0, 0.0), "textbook GBM"),
         ((0.7, 0.0), "COUPLING ONLY (g=0)"),
         ((0.0, 6.0), "VOL-FEEDBACK ONLY (c=0)"),
         ((0.7, 6.0), "both (belief 'near-critical')")]
for (c, g), label in cases:
    k, ac1, corr = simulate(c, g)
    print(f"{('('+str(c)+', '+str(g)+')'):>12} {k:>9.2f} {ac1:>16.2f} {corr:>14.2f}   {label}")

print("\nGaussian kurtosis = 3.00. If COUPLING ONLY stays ~3 / AC1~0 and VOL-FEEDBACK ONLY lifts")
print("them, fat tails+clustering come from g (stochastic vol), not from the coupling c.")
