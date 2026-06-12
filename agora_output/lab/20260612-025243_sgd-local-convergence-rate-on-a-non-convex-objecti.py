"""
Replicate Fehrman, Gess & Jentzen — 'Convergence rates for SGD for non-convex objective functions':
SGD LOCALLY converges to a minimum of a non-convex objective, with a quantifiable RATE.

Smallest model: the classic NON-convex double well  f(x) = (x^2 - 1)^2  — two minima at x=±1, a
maximum at 0 (so it is genuinely non-convex). SGD with noisy gradients and step gamma_t = c/(t+t0),
started inside the basin of x*=+1. Measure E[(x_t - 1)^2] across many seeds and fit its decay.

Theory: near the local min the objective is locally strongly convex (f''(1)=8), so SGD with
gamma_t = c/t gives E[(x_t - x*)^2] = O(1/t) -> log-log slope ~ -1; a constant step instead stalls at
a variance floor. Reproduced if it converges to x*=1 at the ~1/t rate while the constant-step control
does not.
"""
import numpy as np

rng = np.random.default_rng(0)
XSTAR = 1.0
SIGMA = 0.25          # gradient noise sd
SEEDS, T, T0 = 5000, 6000, 20


def fprime(x):
    return 4.0 * x * (x * x - 1.0)          # d/dx (x^2-1)^2


def run(step_mode, c=3.0):
    X = np.full(SEEDS, 1.4)                  # inside the basin of x*=+1
    msd = np.zeros(T)
    for t in range(1, T):
        g = fprime(X) + rng.normal(0, SIGMA, SEEDS)
        gamma = (c / (t + T0)) if step_mode == "decay" else (c / 200.0)
        X = X - gamma * g
        msd[t] = np.mean((X - XSTAR) ** 2)
    return msd


msd = run("decay")
lo, hi = 300, 5500
slope = np.polyfit(np.log(np.arange(lo, hi)), np.log(msd[lo:hi] + 1e-15), 1)[0]
print("DECAYING step gamma_t = c/(t+t0):")
print(f"  E[(x-1)^2]: {msd[300]:.2e} (t=300) -> {msd[-1]:.2e} (t={T}) — converging to x*=1")
print(f"  fitted decay exponent: {slope:.2f}   (theory O(1/t) => -1.0)")

msd_c = run("const")
print("\nCONSTANT step (control):")
print(f"  E[(x-1)^2]: {msd_c[300]:.2e} (t=300) -> {msd_c[-1]:.2e} — stalls at a variance floor")

ok = (msd[-1] < 1e-2) and (-1.3 < slope < -0.7) and (msd_c[-1] > 5 * msd[-1])
print(f"\nLocal convergence to the non-convex minimum + ~1/t rate reproduced: {ok}")
