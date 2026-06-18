
import numpy as np
rng = np.random.default_rng(21)
# Goodhart / cost of legibility: a proxy P is used to SELECT for a true goal G. P = G + lambda*g,
# where g is a cheap, gameable dimension independent of G. As optimization pressure raises gameability
# lambda, top-by-P items increasingly win by inflating g, not G -> the proxy stops identifying high-G.
N = 100000
G = rng.standard_normal(N)            # true value (what we actually want)
g = rng.standard_normal(N)            # gameable dimension, independent of G
def proxy_precision(lam):
    P = G + lam*g + rng.standard_normal(N)*0.3
    top_by_P = P >= np.percentile(P, 90)        # select top 10% by the proxy
    g_cut = np.percentile(G, 90)
    # precision: of those selected by the proxy, what fraction are truly top-10% by G?
    prec = np.mean(G[top_by_P] >= g_cut)
    corr = np.corrcoef(P, G)[0,1]
    return prec, corr
print("Selecting top-10% by a proxy P=G+lambda*g; lambda = gameability/optimization pressure:")
print(" lambda   proxy-G corr   precision(selected are truly top-10% by G)")
for lam in [0.0, 0.5, 1.0, 2.0, 4.0]:
    prec, corr = proxy_precision(lam)
    print(f"  {lam:.1f}      {corr:.2f}         {prec:.0%}")
print("As the proxy becomes more gameable/optimized, it correlates less with the goal and selects")
print("fewer truly-good items: 'when a measure becomes a target it ceases to be a good measure.'")
