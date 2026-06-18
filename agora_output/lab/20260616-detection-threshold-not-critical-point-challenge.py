# Challenge (A13) to the (already-strained) belief: "Detection thresholds are critical points with
# UNIVERSAL run-up dynamics across substrates - critical slowing, diverging fluctuation variance,
# matching exponents - so physics 5-sigma discovery, absorbing-state transitions, and knowledge-base
# 'discovery' all share the same precursor signature."
#
# Disconfirming thesis: the belief CONFLATES two opposite things.
#  - A TRUE critical point / bifurcation: approaching it, the order parameter's fluctuation variance
#    DIVERGES and the system's recovery slows (lag-1 autocorr -> 1). [Scheffer early-warning signals]
#  - An EVIDENCE-ACCUMULATION detection threshold (5-sigma, a sharpening posterior): approaching it,
#    the estimate's variance SHRINKS (~ sigma^2/n) - the system gets SHARPER, not slower. No critical
#    slowing. The opposite signature.
# If so, "universal run-up dynamics across substrates" is false: the precursors are inverted.
import numpy as np

rng = np.random.default_rng(42)

# --- TRUE critical transition: OU process whose restoring rate lambda -> 0 (approaching a critical
#     point). Stationary variance = sigma^2/(2*lambda - lambda^2) -> diverges; lag-1 autocorr -> 1-lambda -> 1.
def ou_ensemble(lmbda, trials=40000, burn=3000, sigma=1.0):
    x = np.zeros(trials)
    for _ in range(burn):
        x = x - lmbda * x + rng.normal(0, sigma, trials)   # relax to stationary
    x_next = x - lmbda * x + rng.normal(0, sigma, trials)   # one more step for AR1
    return x.var(), float(np.corrcoef(x, x_next)[0, 1])

# --- EVIDENCE ACCUMULATION toward a detection threshold: running-mean estimate of a real signal of
#     size mu. Control parameter = n (data / integrated luminosity / corroborating findings).
def accum_ensemble(n, trials=40000, mu=0.2, sigma=1.0):
    return rng.normal(mu, sigma, (trials, n)).mean(axis=1).var()

print("TRUE CRITICAL (OU, restoring rate lambda -> 0 == approaching the critical point):")
print(f"  {'lambda':>8}{'ensemble var':>15}{'lag-1 autocorr':>16}")
for lmbda in [0.50, 0.20, 0.10, 0.05, 0.02]:
    v, a = ou_ensemble(lmbda)
    print(f"  {lmbda:>8.2f}{v:>15.2f}{a:>16.3f}")
print("  -> variance DIVERGES, autocorr -> 1 : critical slowing-down signature PRESENT.")

print("\nEVIDENCE ACCUMULATION (n -> threshold == detecting a real signal):")
print(f"  {'n':>8}{'ensemble var of estimate':>26}")
for n in [10, 40, 100, 400, 1600]:
    print(f"  {n:>8d}{accum_ensemble(n):>26.5f}")
print("  -> variance SHRINKS (~ sigma^2/n) : the estimate gets SHARPER, no critical slowing.")

print("\nVERDICT: approaching the threshold the two substrates show OPPOSITE precursors")
print("(variance diverges vs vanishes). Detection-by-accumulation is a level-crossing of a")
print("sharpening estimate, NOT a critical point - the 'universal run-up dynamics' claim is FALSE.")
