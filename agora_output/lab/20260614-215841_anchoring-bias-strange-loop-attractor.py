import random, statistics

# Minimal computational model: anchoring bias as a STRANGE LOOP.
# An agent estimates a truth t from a stream of unbiased noisy signals s_n ~ N(t, sigma^2),
# starting from a biased anchor a (a != t). Each round it forms a convex update
#       e_{n+1} = rho_n * e_n + (1 - rho_n) * s_n
# where rho_n is how much it trusts its OWN prior estimate vs the fresh signal.
#
# The signals are UNBIASED, so any persistent bias can only come from the self-trust schedule
# (the loop where the agent's prior feeds itself). Two regimes:
#   HEALTHY running mean:      rho_n = n/(n+1)              (correct unbiased averaging)
#   SELF-CONFIRMING loop:      rho_n = 1 - 1/(n+1)**p       (self-trust inflates with exponent p)
#
# CLAIM (strange-loop attractor): when self-confidence grows super-linearly (p>1), the product
# of (1-...) converges to a POSITIVE constant, so a fixed fraction of the initial anchor bias is
# NEVER washed out by evidence -> a permanent self-locked bias. Boundary is p=1 (the healthy mean).
# Falsifier: if measured residual bias at p>1 -> 0 as horizon N grows, the strange-loop claim FAILS.

random.seed(7)  # fixed seed: no Math.random reliance, reproducible

def run(p, t, a, sigma, N, trials):
    biases = []
    for _ in range(trials):
        e = a
        for n in range(1, N + 1):
            s = random.gauss(t, sigma)
            if p is None:               # healthy running mean
                rho = n / (n + 1.0)
            else:                        # self-confirming loop
                rho = 1.0 - 1.0 / (n + 1.0) ** p
            e = rho * e + (1.0 - rho) * s
        biases.append(e - t)
    return statistics.mean(biases)      # mean signed bias toward the anchor

t, a, sigma, trials = 0.0, 10.0, 5.0, 4000   # anchor 10 units above truth; signal noise 5

print("mean residual bias toward anchor (a-t = +10); should ->0 if evidence wins")
print(f"{'regime':>22} | {'N=20':>8} {'N=100':>8} {'N=500':>8}")
for label, p in [("healthy mean (rho=n/n+1)", None), ("loop p=0.5", 0.5),
                 ("loop p=1.0 (boundary)", 1.0), ("loop p=1.5", 1.5), ("loop p=2.0", 2.0)]:
    row = [run(p, t, a, sigma, N, trials) for N in (20, 100, 500)]
    print(f"{label:>22} | {row[0]:8.3f} {row[1]:8.3f} {row[2]:8.3f}")

# Deterministic anchor-decay fraction = product_{n=1..N} rho_n  (signals unbiased -> only anchor persists)
print("\nanalytic residual anchor fraction = prod rho_n (confirms permanence at p>1):")
for p in (0.5, 1.0, 1.5, 2.0, 3.0):
    prod = 1.0
    for n in range(1, 100000):
        prod *= (1.0 - 1.0 / (n + 1.0) ** p)
    print(f"  p={p:>3}: limiting fraction = {prod:.4f}  ({'PERMANENT lock' if prod>0.01 else 'washes out'})")

# Verdict: locked bias appears for p>1 and is stable as N grows (does NOT ->0).
b500_p2 = run(2.0, t, a, sigma, 500, trials)
b20_p2 = run(2.0, t, a, sigma, 20, trials)
b500_healthy = run(None, t, a, sigma, 500, trials)
print(f"\nstrange-loop signature: p=2 bias at N=20 ({b20_p2:.3f}) ~= N=500 ({b500_p2:.3f}) [does NOT decay]")
print(f"contrast: healthy bias at N=500 = {b500_healthy:.3f} [washed out]")
locked = abs(b500_p2) > 1.0 and abs(b500_healthy) < 0.5
print("VERDICT_STRANGE_LOOP =", "CONFIRMED" if locked else "NOT_CONFIRMED")
