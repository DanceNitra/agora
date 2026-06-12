"""
Insight 'Statistics Is Complexity Science With the Dynamics Removed': a STATIC statistical snapshot
of a DYNAMICALLY controlled system can erase the very causal structure that drives it. Measured via
Friedman's-thermostat: a feedback loop where the control input H fully determines the output T, yet
the cross-sectional corr(H, T) -> 0 as control tightens.

Model: dT = -k(T - T_ext_t) + a*H_t + noise ;  controller H_t = -Kp*(T_t - setpoint).
H CAUSES T (coefficient a). Measure the static (cross-sectional) Pearson corr(H, T) over the run,
sweeping the controller gain Kp. Prediction: better control (higher Kp) -> tighter T -> corr(H,T)
collapses toward 0 (or sign-flips), even though the dynamic causal effect a is unchanged.
"""
import numpy as np

rng = np.random.default_rng(1)
T_steps, dt = 30000, 0.02          # smaller dt -> stable up to higher controller gain
k, a, setpoint = 1.0, 1.0, 20.0


def run(Kp):
    T = setpoint
    Hs, Ts = np.empty(T_steps), np.empty(T_steps)
    T_ext = setpoint
    for i in range(T_steps):
        T_ext += dt * (-0.5 * (T_ext - setpoint)) + rng.normal(0, 0.6)   # wandering disturbance
        H = -Kp * (T - setpoint)                                          # proportional controller
        T += dt * (-k * (T - T_ext) + a * H) + rng.normal(0, 0.05)
        Hs[i], Ts[i] = H, T
    return float(np.corrcoef(Hs, Ts)[0, 1]), float(Ts.std())


print(f"Dynamic causal effect of H on T is FIXED (a = {a}). Varying only the controller gain Kp:\n")
print(f"{'Kp':>6} {'T std (control)':>16} {'static corr(H,T)':>18}")
for Kp in (0.5, 2.0, 10.0, 40.0, 90.0):
    c, tsd = run(Kp)
    note = "loose control" if Kp <= 2 else ("tight control" if Kp >= 40 else "")
    print(f"{Kp:>6.1f} {tsd:>16.3f} {c:>18.3f}   {note}")

print("\nH CAUSES T throughout, yet as the controller tightens (Kp up), T's variance collapses and the")
print("STATIC correlation between cause (H) and effect (T) goes to ~0 — the dynamics held the structure;")
print("removing them (a cross-sectional snapshot) erases it. Statistics = complexity minus the dynamics.")
