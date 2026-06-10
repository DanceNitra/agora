import numpy as np
import math

rng = np.random.default_rng(42)

# Panel: 1 treated unit + N_ctrl controls, T periods, treatment at t = T_pre.
N_CTRL, T_PRE, T_POST = 20, 6, 4
T = T_PRE + T_POST
TRUE_EFFECT = 2.0
NOISE = 1.0
N_SIM = 2000

def simulate(violation, mag):
    """Returns (did_estimate, pretrend_p) for one panel draw under a given violation."""
    t = np.arange(T)
    time_trend = 0.3 * t                      # common to all units (DiD differences it out)
    ctrl = (rng.normal(0, 1, (N_CTRL, 1)) + time_trend
            + rng.normal(0, NOISE, (N_CTRL, T)))
    treated = rng.normal(0, 1) + time_trend + rng.normal(0, NOISE, T)
    treated[T_PRE:] += TRUE_EFFECT            # the real causal effect, post-treatment

    if violation == "parallel":               # treated drifts away at slope `mag` every period
        treated += mag * t
    elif violation == "anticipation":         # effect leaks `mag` into the last pre-period
        treated[T_PRE - 1] += mag
    elif violation == "composition":          # a level shift mid-pre-period (unstable unit)
        treated[T_PRE // 2:] += mag

    ctrl_mean = ctrl.mean(axis=0)
    # 2x2 DiD: (treated post-pre) - (control post-pre)
    did = ((treated[T_PRE:].mean() - treated[:T_PRE].mean())
           - (ctrl_mean[T_PRE:].mean() - ctrl_mean[:T_PRE].mean()))
    # pre-trend test: slope of (treated - control) gap over pre-periods, t-test vs 0
    gap = (treated - ctrl_mean)[:T_PRE]
    tt = np.arange(T_PRE)
    sx = tt - tt.mean()
    slope = (sx * (gap - gap.mean())).sum() / (sx**2).sum()
    resid = gap - (gap.mean() + slope * sx)
    se = np.sqrt((resid**2).sum() / (T_PRE - 2) / (sx**2).sum())
    p = 2 * (1 - _norm_cdf(abs(slope / se))) if se > 0 else 1.0
    return did, p

def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / np.sqrt(2)))

print("DiD bias and pre-trend detection under assumption violations")
print(f"(true effect={TRUE_EFFECT}, {N_CTRL} controls, {T_PRE} pre / {T_POST} post, {N_SIM} sims)\n")
print(f"{'violation':14} {'mag':>5} {'mean_est':>9} {'bias':>7} {'|bias|%':>8} {'detect@5%':>10}")

for violation, mags in [("parallel", [0.0, 0.3, 0.6]),
                        ("anticipation", [0.0, 1.0, 2.0]),
                        ("composition", [0.0, 1.0, 2.0])]:
    for mag in mags:
        ests, ps = np.empty(N_SIM), np.empty(N_SIM)
        for i in range(N_SIM):
            ests[i], ps[i] = simulate(violation, mag)
        bias = ests.mean() - TRUE_EFFECT
        detect = (ps < 0.05).mean()
        print(f"{violation:14} {mag:5.1f} {ests.mean():9.3f} {bias:7.3f} "
              f"{100*abs(bias)/TRUE_EFFECT:7.1f}% {100*detect:9.1f}%")

print("\nReading: bias is the systematic error in the DiD effect estimate; detect@5% is how")
print("often a pre-trend test flags the violation BEFORE you trust the estimate.")
