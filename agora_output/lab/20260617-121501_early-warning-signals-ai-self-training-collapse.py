"""
Forge analogy (severe-test): do critical-slowing-down EARLY-WARNING signals from phase-transition
theory transfer to AI self-training collapse?

Source mechanism: near a CONTINUOUS critical transition, a system's recovery from perturbations
slows ("critical slowing down"), so the lag-1 autocorrelation and variance of an observable RISE
before the tipping point — a universal early-warning signal (ecology: Scheffer et al.; same skeleton
across magnets, ecosystems, neural avalanches).

Target: a recursive self-training loop (a model repeatedly fit to its own outputs, mixed with a
fraction f of real anchor data). As f -> 0 the loop approaches model collapse (variance -> 0).

STRUCTURAL MAP (same skeleton, different flesh):
  control parameter   = real-data anchor fraction f   (vs temperature / nutrient load)
  order parameter     = retained variance sigma^2     (vs magnetization / biomass)
  restoring force     = mixing in real data           (vs physical relaxation)
  critical point      = f -> 0 (no anchor)            (vs T_c)
HYPOTHESIS: collapse is approached continuously, so as f -> 0 the lag-1 autocorrelation AR(1) and the
coefficient of variation (CV) of sigma^2 RISE monotonically toward 1 — i.e. collapse is forecastable
from the self-training telemetry BEFORE it happens.
FALSIFIER: if AR(1)/CV stay flat and collapse is abrupt with no pre-rise, the early-warning map fails.
"""
import numpy as np


def run_loop(f, n=400, T=600, seed=0):
    """Recursive Gaussian self-training with a real-anchor fraction f. Returns the sigma^2 series."""
    rng = np.random.default_rng(seed)
    s2 = 1.0
    series = []
    n_real = max(1, int(round(f * n)))
    n_own = n - n_real
    for _ in range(T):
        own = rng.normal(0.0, np.sqrt(max(s2, 1e-12)), n_own)      # samples from own (degrading) model
        real = rng.normal(0.0, 1.0, n_real)                         # real anchor data (true variance 1)
        pooled = np.concatenate([own, real])
        s2 = float(np.var(pooled))                                  # refit -> next generation's variance
        series.append(s2)
    return np.array(series)


def ar1(x):
    x = x - x.mean()
    denom = np.sum(x * x)
    return float(np.sum(x[1:] * x[:-1]) / denom) if denom > 1e-12 else 0.0


def recovery_time(f, n=400, knock=0.3, T=200, reps=200, seed=1):
    """Perturb sigma^2 down to `knock`, measure generations to recover halfway back to the fixed point."""
    rng = np.random.default_rng(seed)
    n_real = max(1, int(round(f * n))); n_own = n - n_real
    times = []
    for r in range(reps):
        s2 = knock
        target = 1.0; half = knock + 0.5 * (target - knock)
        for t in range(T):
            own = rng.normal(0, np.sqrt(max(s2, 1e-12)), n_own)
            real = rng.normal(0, 1.0, n_real)
            s2 = float(np.var(np.concatenate([own, real])))
            if s2 >= half:
                times.append(t + 1); break
        else:
            times.append(T)
    return float(np.mean(times))


print("f (anchor)   AR(1)    CV(sigma^2)   recovery_time   mean sigma^2")
fs = [0.5, 0.3, 0.15, 0.08, 0.04, 0.02, 0.01]
rows = []
for f in fs:
    # average telemetry over several seeds at the stable regime (after burn-in)
    a_list, cv_list, m_list = [], [], []
    for sd in range(6):
        s = run_loop(f, seed=100 + sd)[100:]      # burn-in
        a_list.append(ar1(s)); cv_list.append(s.std() / max(s.mean(), 1e-9)); m_list.append(s.mean())
    a, cv, m = np.mean(a_list), np.mean(cv_list), np.mean(m_list)
    rt = recovery_time(f)
    rows.append((f, a, cv, rt, m))
    print(f"{f:<11} {a:>6.3f}   {cv:>9.3f}   {rt:>11.2f}   {m:>10.3f}")

# verdict: early-warning works if AR(1), CV, recovery_time all RISE as f -> 0 (monotone-ish)
import numpy as np
ar_vals = [r[1] for r in rows]; cv_vals = [r[2] for r in rows]; rt_vals = [r[3] for r in rows]
def rising(v):  # allow tiny non-monotonicity from sampling noise
    return all(v[i+1] >= v[i] - 0.03 for i in range(len(v)-1)) and (v[-1] - v[0] > 0.1)
ar_rise, cv_rise, rt_rise = rising(ar_vals), rising([c for c in cv_vals]), (rt_vals[-1] > 2*rt_vals[0])
print("\n=== VERDICT ===")
print(f"AR(1) rises toward 1 as f->0: {ar_rise}  ({ar_vals[0]:.2f} -> {ar_vals[-1]:.2f})")
print(f"CV rises as f->0: {cv_rise}  ({cv_vals[0]:.3f} -> {cv_vals[-1]:.3f})")
print(f"recovery time lengthens (critical slowing down): {rt_rise}  ({rt_vals[0]:.1f} -> {rt_vals[-1]:.1f} gens)")
if ar_rise and rt_rise:
    print("SUPPORTED: critical-slowing-down early-warning signals DO transfer — collapse is forecastable")
    print("from self-training telemetry (rising AR(1)+recovery time) before variance hits zero.")
else:
    print("FAILED / forced: no usable pre-collapse early-warning signal in the telemetry.")
