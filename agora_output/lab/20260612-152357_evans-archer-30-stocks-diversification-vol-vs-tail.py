"""
Replication: Evans & Archer (1968) / textbook canon — "a portfolio of ~20-30 stocks achieves
practically complete diversification" (the marginal benefit of adding stocks beyond ~30 is
negligible).

The claim's mechanism: idiosyncratic risk scales as 1/N, so by N~30 nearly all diversifiable
risk is gone. That is TRUE for VARIANCE under thin-tailed, weakly-correlated returns — but the
canonical generalization ("30 stocks ~ fully diversified") is used for RISK writ large.
We test the mechanism at its stated scope and at realistic scope:

  (1) Thin tails (normal idio), single-factor correlation  -> variance ratio vs N
  (2) Heavy tails: idio returns Student-t(2.5) (finite variance barely; realistic for equities)
  (3) Very heavy tails: alpha-stable-like via t(1.8) (infinite variance regime proxy)

Measured quantity: the fraction of ACHIEVABLE risk reduction (vs the N=500 fully-diversified
portfolio) that a 30-stock portfolio actually captures — for volatility AND for tail risk
(99% expected shortfall). Claim canon says ~95%+ captured at N=30.

VERDICT RULE:
  REPRODUCED -- N=30 captures >=90% of achievable reduction for BOTH vol and ES99 across regimes
  FAILED     -- N=30 leaves a materially large gap (captures <90%) in any realistic regime,
                i.e. the textbook generalization breaks where it is most needed (tails).
"""
import numpy as np

rng = np.random.default_rng(20260612)

M = 500          # investable universe
T = 40000        # return draws per portfolio evaluation
NS = [1, 2, 5, 10, 20, 30, 50, 100, 200, 500]
REPORT_N = 30


def es99(x):
    """99% expected shortfall (mean loss beyond the 1% worst quantile), positive number."""
    q = np.quantile(x, 0.01)
    tail = x[x <= q]
    return -tail.mean()


def run_regime(name, idio_draw, beta_sd=0.25, factor_sd=0.045, idio_sd=0.08):
    betas = 1.0 + beta_sd * rng.standard_normal(M)
    out = {}
    for N in NS:
        # average over several random N-stock portfolios for stability
        reps = 12 if N < 500 else 1
        vols, tails = [], []
        for _ in range(reps):
            idx = rng.choice(M, N, replace=False)
            w = np.full(N, 1.0 / N)
            F = factor_sd * rng.standard_normal(T)
            eps = idio_sd * idio_draw((T, N))
            r = F[:, None] * betas[idx][None, :] + eps
            rp = r @ w
            vols.append(rp.std())
            tails.append(es99(rp))
        out[N] = (np.mean(vols), np.mean(tails))
    return out


def captured(out, metric):
    """Fraction of achievable reduction (N=1 -> N=500) captured at N=30."""
    i = 0 if metric == "vol" else 1
    x1, x30, xF = out[1][i], out[REPORT_N][i], out[500][i]
    return (x1 - x30) / (x1 - xF) if x1 > xF else float("nan")


regimes = [
    ("normal idio + 1-factor", lambda s: rng.standard_normal(s)),
    ("Student-t(2.5) idio + 1-factor", lambda s: rng.standard_t(2.5, s) / np.sqrt(2.5 / 0.5)),
    ("Student-t(1.8) idio + 1-factor (near-infinite var)", lambda s: rng.standard_t(1.8, s)),
]

print("=== Evans-Archer '30 stocks ~ fully diversified': captured fraction of achievable reduction at N=30 ===")
results = {}
for name, draw in regimes:
    out = run_regime(name, draw)
    cv = captured(out, "vol")
    ct = captured(out, "es99")
    results[name] = (cv, ct)
    print(f"\n[{name}]")
    print(f"  vol:   N=1 {out[1][0]:.4f}  N=30 {out[30][0]:.4f}  N=500 {out[500][0]:.4f}  -> captured {cv*100:.1f}%")
    print(f"  ES99:  N=1 {out[1][1]:.4f}  N=30 {out[30][1]:.4f}  N=500 {out[500][1]:.4f}  -> captured {ct*100:.1f}%")
    # how many stocks to capture 90% of the ES99 reduction?
    x1, xF = out[1][1], out[500][1]
    need = next((N for N in NS if (x1 - out[N][1]) / (x1 - xF) >= 0.90), None)
    print(f"  stocks needed to capture 90% of achievable ES99 reduction: {need}")

print("\n=== Verdict ===")
worst = min(min(v) for v in results.values())
ok = all(cv >= 0.90 and ct >= 0.90 for cv, ct in results.values())
if ok:
    print("REPRODUCED: N=30 captures >=90% of achievable vol AND tail-risk reduction in all regimes.")
else:
    print(f"FAILED (in stated generality): N=30 leaves a material gap (worst captured fraction "
          f"{worst*100:.1f}%). The 1/N variance argument holds for VOLATILITY under thin tails, "
          f"but the textbook generalization breaks for TAIL RISK under realistic heavy-tailed "
          f"returns - where diversification is needed most.")
