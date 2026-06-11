import numpy as np
rng = np.random.default_rng(41)

# Critical Slowing Down -> Knowledge Observability.
# CSD: near a critical point, a system's RECOVERY TIME from a small perturbation diverges
# (relaxation rate -> 0). Map: a knowledge base approaching a coherence reorganization should
# show a LENGTHENING recovery time after a contradiction is injected - a PASSIVELY measurable
# early-warning precursor (unlike a synthesis we have to request).
# Model: order parameter x (coherence) with restoring dynamics x' = -r*x + noise, where the
# restoring rate r -> 0 as the control parameter approaches the critical threshold. Measure the
# autocorrelation time (recovery time) of x vs distance-to-critical.

def recovery_time(r, n=20000, dt=0.05, sigma=0.1):
    # simulate OU-like relaxation; measure lag-1 autocorrelation -> recovery time tau = -dt/ln(ac1)
    x = np.empty(n); x[0] = 0.0
    for i in range(1, n):
        x[i] = x[i-1] - r * x[i-1] * dt + sigma * np.sqrt(dt) * rng.standard_normal()
    x = x[1000:]                      # burn-in
    x0, x1 = x[:-1], x[1:]
    ac1 = np.corrcoef(x0, x1)[0, 1]
    return -dt / np.log(ac1) if 0 < ac1 < 1 else np.nan

print("Critical Slowing Down -> Knowledge Observability: recovery time vs distance-to-critical")
print("(restoring rate r -> 0 at the critical threshold; recovery time should DIVERGE)\n")
print(f"{'r (dist-to-crit)':>16} {'recovery time tau':>18} {'~1/r predicted':>16}")
for r in [1.0, 0.5, 0.25, 0.12, 0.06, 0.03]:
    tau = np.mean([recovery_time(r) for _ in range(5)])
    print(f"{r:16.3f} {tau:18.2f} {1.0/r:16.2f}")

print("\nReading: recovery time rising as r->0 (distance-to-critical -> 0) IS critical slowing down.")
print("Mapped: a vault nearing reorganization shows LENGTHENING coherence-recovery after each")
print("contradiction - a passively measurable precursor (no synthesis needs to be requested).")
