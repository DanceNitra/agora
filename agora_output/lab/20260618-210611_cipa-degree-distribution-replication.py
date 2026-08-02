import numpy as np

# Crucible replication: "degree distribution obeys a power law up to a finite threshold and
# decays exponentially above it" -- Competition-Induced Preferential Attachment (Berger, Borgs,
# Chayes, D'Souza 2005). Faithful minimal model: vertices arrive on [0,1]; new vertex i connects to
# the earlier vertex j minimizing cost = |x_i - x_j| + alpha * depth_j (geographic distance vs
# hop-distance to root). This competition is known to induce tempered PA = power law w/ exp cutoff.
# Test: does the tail decay EXPONENTIALLY (cutoff, claim) rather than as a pure power law (BA)?

def build_cipa(N, alpha, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.random(N)
    depth = np.zeros(N); parent = -np.ones(N, dtype=int); deg = np.zeros(N)
    for i in range(1, N):
        cost = np.abs(x[i] - x[:i]) + alpha * depth[:i]
        j = int(np.argmin(cost))
        parent[i] = j; depth[i] = depth[j] + 1
        deg[j] += 1; deg[i] += 1
    return deg

def tail_fit(deg, kmin):
    # for degrees >= kmin: compare power-law (log P vs log k) vs exponential (log P vs k) by R^2
    ks = np.arange(deg.max() + 1)
    cnt = np.bincount(deg.astype(int), minlength=len(ks)).astype(float)
    p = cnt / cnt.sum()
    m = (ks >= kmin) & (p > 0)
    if m.sum() < 4: return None
    k = ks[m]; lp = np.log(p[m])
    def r2(xv):
        A = np.vstack([xv, np.ones_like(xv)]).T
        coef, *_ = np.linalg.lstsq(A, lp, rcond=None)
        pred = A @ coef; ss = 1 - ((lp - pred)**2).sum() / ((lp - lp.mean())**2).sum()
        return ss, coef
    r2_pow, c_pow = r2(np.log(k))      # power law: log P linear in log k
    r2_exp, c_exp = r2(k.astype(float))# exponential: log P linear in k
    return r2_pow, r2_exp, c_pow[0], c_exp[0]

for alpha in [0.02, 0.05, 0.10]:
    deg = build_cipa(20000, alpha)
    kmax = int(deg.max()); kmean = deg.mean()
    # body (small k) and tail (large k) split at ~ the 90th percentile of degree
    ksplit = max(4, int(np.percentile(deg, 90)))
    body = tail_fit(deg, 2); tail = tail_fit(deg, ksplit)
    print(f'alpha={alpha}: N=20000 max_deg={kmax} mean_deg={kmean:.2f} ksplit={ksplit}')
    if body: print(f'   BODY(k>=2):  R2_powerlaw={body[0]:.3f} (slope {body[2]:.2f})  R2_exp={body[1]:.3f}')
    if tail: print(f'   TAIL(k>={ksplit}): R2_powerlaw={tail[0]:.3f}  R2_exp={tail[1]:.3f} (rate {tail[3]:.3f})  -> exp wins => CUTOFF' if tail[1]>tail[0] else f'   TAIL(k>={ksplit}): R2_pow={tail[0]:.3f} R2_exp={tail[1]:.3f} -> power wins (no cutoff)')
print()
print('CLAIM: power-law body + EXPONENTIAL tail (cutoff). REPRODUCED if body fits power-law AND tail')
print('decays exponentially (R2_exp > R2_pow in the tail) for an intermediate alpha.')
