"""
CHALLENGE (severe test): belief "synthetic control beats DiD for one treated unit ONLY with ENOUGH
pre-periods; at short pre-periods SC's edge collapses (weight-fitting noise rivals bias reduction)."
(insight-when-synthetic-control-beats-did, Labs 13dbc2/606f02/a81de8.)

The belief's own falsifier: "until a setup shows SC dominating even with SHORT, well-matched pre-data."
So ATTACK that: a single treated unit with a SYSTEMATIC pre-trend gap (DiD biased), but SHORT pre-periods
(T_pre=3,4) AND clean, well-matching donors (low idiosyncratic noise -> high pre-fit signal-to-noise).
If SC still beats DiD there, the rule "needs enough PRE-PERIODS" is too crude — the real condition is
pre-fit SIGNAL-TO-NOISE (achievable with FEW clean periods), refining the belief. If SC collapses at short
pre regardless of cleanliness, the belief SURVIVES.
"""
import numpy as np

RNG = np.random.default_rng(0)


def proj_simplex(v):
    n = len(v); u = np.sort(v)[::-1]; css = np.cumsum(u)
    rho = np.nonzero(u * np.arange(1, n + 1) > (css - 1))[0][-1]
    theta = (css[rho] - 1) / (rho + 1.0)
    return np.maximum(v - theta, 0)


def sc_weights(Dpre, ypre, iters=3000):
    n = Dpre.shape[1]; w = np.ones(n) / n
    lr = 1.0 / (np.linalg.norm(Dpre, 2) ** 2 + 1e-9)
    for _ in range(iters):
        w = proj_simplex(w - lr * (Dpre.T @ (Dpre @ w - ypre)))
    return w


def one_trial(T_pre, sigma, tau=2.0, N=20, K=3, T_post=8, pretrend_gap=0.06, rng=None):
    rng = rng or RNG
    T = T_pre + T_post
    # common factors (smooth random walks) + a DEDICATED gap-factor the treated loads on but donors barely do
    F = np.cumsum(rng.normal(0, 1, (T, K)), axis=0)
    gap = np.arange(T) * pretrend_gap                      # systematic divergence over time -> breaks parallel trends
    Ld = rng.uniform(0, 1, (N, K))                         # donor loadings
    # treated loadings = convex combo of a few donors (so SC CAN match) — well-matched donor pool
    base = np.zeros(N); base[rng.choice(N, 4, replace=False)] = rng.uniform(0.5, 1.5, 4)
    wtrue = base / base.sum()
    Lt = wtrue @ Ld
    donors = Ld @ F.T + rng.normal(0, sigma, (N, T))       # (N, T)
    treated = Lt @ F.T + gap + rng.normal(0, sigma, T)     # treated has the systematic gap (DiD-violating)
    treated[T_pre:] += tau                                 # the real treatment effect, post only

    Dpre, Dpost = donors[:, :T_pre].T, donors[:, T_pre:].T  # (T_pre,N),(T_post,N)
    tpre, tpost = treated[:T_pre], treated[T_pre:]
    # DiD (treated vs donor average)
    did = (tpost.mean() - tpre.mean()) - (Dpost.mean() - Dpre.mean())
    # Synthetic control: fit simplex weights on the pre-period, apply post
    w = sc_weights(Dpre, tpre)
    sc = tpost.mean() - (Dpost @ w).mean()
    return abs(did - tau), abs(sc - tau)


print("=== Challenge: does SC's edge REALLY need many pre-periods, or just clean pre-fit? ===")
print(f"  {'T_pre':>6} {'sigma':>6} {'DiD |bias|':>11} {'SC |bias|':>10} {'winner':>8}")
for sigma in (0.1, 0.6):
    for T_pre in (3, 4, 6, 24):
        ds, ss = [], []
        for r in range(300):
            d, s = one_trial(T_pre, sigma, rng=np.random.default_rng(1000 + r))
            ds.append(d); ss.append(s)
        db, sb = np.mean(ds), np.mean(ss)
        win = "SC" if sb < db - 0.02 else ("DiD" if db < sb - 0.02 else "tie")
        print(f"  {T_pre:>6} {sigma:>6.1f} {db:>11.3f} {sb:>10.3f} {win:>8}")

# the decisive cell: SHORT pre (3) + CLEAN donors (low sigma) + a real pre-trend gap
ds = [one_trial(3, 0.1, rng=np.random.default_rng(2000 + r)) for r in range(400)]
db = np.mean([d for d, s in ds]); sb = np.mean([s for d, s in ds])
print(f"\nMEASURED (decisive cell — T_pre=3, sigma=0.1, systematic pre-trend gap): "
      f"DiD |bias|={db:.3f} vs SC |bias|={sb:.3f}  -> SC is {'BETTER' if sb < db - 0.02 else 'NOT better'} "
      f"with only 3 CLEAN pre-periods.")
print()
if sb < db - 0.02:
    print("VERDICT: belief REFINED (challenge partially succeeds). SC dominates DiD even with only 3 pre-periods "
          "WHEN the donors are clean and well-matching — so the gating condition is pre-fit SIGNAL-TO-NOISE, not "
          "the pre-period COUNT per se. The original 'needs enough pre-periods' collapses to a special case of "
          "low signal-to-noise; with few but clean periods SC still wins. Core claim (SC beats DiD under a "
          "systematic, matchable pre-trend gap) HOLDS; the 'short-pre-period collapse' is really a noise effect.")
else:
    print("VERDICT: belief SURVIVES. Even with clean donors, 3 pre-periods are too few for SC to beat DiD — "
          "the pre-period-count dependency stands as stated.")
