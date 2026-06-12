"""
Insight test: does adding REALIZED SKEWNESS to a GARCH-style volatility model improve OUT-OF-SAMPLE
volatility forecasting? Honest severe test: sweep a coupling kappa that controls whether past
realized skewness GENUINELY leads next-period volatility in the data-generating process.

DGP: h_t = omega + a*r^2_{t-1} + b*h_{t-1} + kappa*max(0, -skew_{t-1})   (downside skew -> higher vol)
     r_t = sqrt(h_t)*z_t,  z ~ N(0,1);  skew_{t-1} = sample skewness of the last m returns.
Models (fit by OLS predicting r^2_t on a train split, evaluated OOS):
  BASE : r^2_t ~ 1 + r^2_{t-1} + r^2_{t-2} + r^2_{t-3}      (ARCH-lag GARCH proxy)
  +SKEW: BASE + realized_skew_{t-1}
Prediction: +SKEW beats BASE out-of-sample ONLY when kappa>0 (skew really leads vol); at kappa=0 it
just adds a parameter and overfits, so OOS does not improve (and can worsen).
"""
import numpy as np

rng = np.random.default_rng(7)
T, M = 6000, 20          # series length, rolling window for realized skewness
OMEGA, A, B = 0.05, 0.08, 0.88


def roll_skew(x):
    x = x - x.mean()
    s = x.std()
    return float((x**3).mean() / s**3) if s > 1e-9 else 0.0


def simulate(kappa):
    r = np.zeros(T); h = np.zeros(T); h[0] = OMEGA / (1 - A - B)
    sk = np.zeros(T)
    for t in range(1, T):
        if t > M:
            sk[t-1] = roll_skew(r[t-M:t])
        h[t] = OMEGA + A * r[t-1]**2 + B * h[t-1] + kappa * max(0.0, -sk[t-1])
        r[t] = np.sqrt(max(h[t], 1e-8)) * rng.standard_normal()
    return r, sk


def oos_rmse(r, sk, use_skew):
    # features predicting r^2_t
    y = r[M+3:]**2
    cols = [np.ones_like(y), (r[M+2:-1]**2), (r[M+1:-2]**2), (r[M:-3]**2)]
    if use_skew:
        cols.append(sk[M+2:-1])
    X = np.vstack(cols).T
    n = len(y); cut = int(n * 0.6)
    beta, *_ = np.linalg.lstsq(X[:cut], y[:cut], rcond=None)   # fit on train
    pred = X[cut:] @ beta                                       # forecast OOS
    return float(np.sqrt(np.mean((pred - y[cut:])**2)))


print(f"{'kappa (skew->vol)':>18} {'BASE rmse':>10} {'+SKEW rmse':>11} {'improvement':>12}")
for kappa in (0.0, 0.3, 0.8, 1.5):
    r, sk = simulate(kappa)
    base = oos_rmse(r, sk, False)
    skew = oos_rmse(r, sk, True)
    imp = 100 * (base - skew) / base
    tag = "skew is noise" if kappa == 0 else "skew leads vol"
    print(f"{kappa:>18.1f} {base:>10.4f} {skew:>11.4f} {imp:>10.1f}%   {tag}")

print("\n+SKEW helps OOS only when skewness genuinely leads volatility (kappa>0);")
print("at kappa=0 the extra regressor adds no OOS gain (overfitting risk) — not a free lunch.")
