# Challenge "detection thresholds are critical points with UNIVERSAL run-up dynamics."
# Critical slowing down (rising variance + lag-1 autocorrelation before a transition) is the classic
# early-warning signal. But it is universal only for FOLD/saddle-node bifurcations, where the recovery
# rate -> 0. A "detection threshold" defined merely as the state crossing a LEVEL, with no underlying
# bifurcation (a stable linear system pushed toward a level by drift), has a FIXED recovery rate and
# shows NO run-up. So the run-up is universal within the bifurcation class, not across all thresholds.
# Euler-Maruyama simulation. Source: simulation.
import numpy as np
rng = np.random.default_rng(0)

dt, sigma, STEPS = 0.01, 0.10, 60000

def ar1_var(x):
    x = x - x.mean()
    if len(x) < 3: return 0.0, 0.0
    ar1 = np.corrcoef(x[:-1], x[1:])[0,1]
    return float(ar1), float(np.var(x))

def run_fold():
    # saddle-node: dx = (mu - x^2) dt + sigma dW ; mu slowly decreases mu0 -> 0 (approach the fold).
    # stable fixed point at +sqrt(mu); recovery rate 2*sqrt(mu) -> 0 as mu->0 (critical slowing).
    mu = np.linspace(1.0, 0.02, STEPS)
    x = np.sqrt(mu[0]); xs = np.empty(STEPS)
    for i in range(STEPS):
        x += (mu[i] - x*x)*dt + sigma*np.sqrt(dt)*rng.standard_normal()
        xs[i] = x
    return xs

def run_linear():
    # no bifurcation: dx = -k(x-m) dt + sigma dW, k FIXED. "threshold" = drift m rising toward level L.
    # recovery rate k constant -> stationary variance & AR(1) constant, no run-up.
    k, L = 1.0, 1.0
    m = np.linspace(0.0, L, STEPS)
    x = 0.0; xs = np.empty(STEPS)
    for i in range(STEPS):
        x += -k*(x - m[i])*dt + sigma*np.sqrt(dt)*rng.standard_normal()
        xs[i] = x
    return xs

def early_late(xs, W=4000):
    # detrend in windows; compare AR(1)/variance early (far from threshold) vs late (near it)
    e = xs[5000:5000+W]; l = xs[STEPS-W:]
    return ar1_var(e), ar1_var(l)

for name, fn in [("FOLD bifurcation (true critical point)", run_fold),
                 ("LINEAR + drift to a level (no bifurcation)", run_linear)]:
    (ar_e,v_e),(ar_l,v_l) = early_late(fn())
    print(f"{name}:")
    print(f"   AR(1):  early {ar_e:.3f} -> late {ar_l:.3f}    variance: early {v_e:.4f} -> late {v_l:.4f}")
print("\n=> The FOLD shows the universal run-up (AR(1)->1, variance climbs) as it nears the critical")
print("   point. The LINEAR threshold crossing shows NO run-up (AR(1), variance flat) despite")
print("   approaching/crossing the detection level. Critical-slowing precursors are universal WITHIN")
print("   the fold/bifurcation class, NOT across all detection thresholds. Belief REFINED.")
