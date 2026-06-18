# Challenge: "finance is formalized risk management BECAUSE wealth is MULTIPLICATIVE."
# The causal attribution is too narrow. What actually forces risk management is NON-ERGODICITY /
# path-dependence (ruin), and multiplicativity is only ONE route to it. Discriminating 3-way test at
# matched positive drift: (1) MULTIPLICATIVE (non-ergodic growth -> volatility drag), (2) ADDITIVE +
# absorbing RUIN barrier (non-ergodic via the barrier, NOT multiplicative), (3) ADDITIVE, no barrier
# (ergodic). Measure how much HALVING volatility improves the typical (median) long-run outcome.
# If risk management helps in (1) AND (2) but NOT (3), the cause is non-ergodicity, not multiplicativity.
# Source: simulation.
import numpy as np
rng = np.random.default_rng(0)
T, P = 250, 40000

def mult(sigma):
    mu = 0.02
    logW = np.zeros(P)
    for _ in range(T):
        r = rng.normal(mu, sigma, P)
        logW += np.log1p(np.maximum(r, -0.999))
    return np.median(np.exp(logW))                      # typical multiplicative wealth (W0=1)

def add_ruin(sigma):
    m = 0.05; W = np.full(P, 10.0); alive = np.ones(P, bool)
    for _ in range(T):
        W = W + rng.normal(m, sigma, P)*alive
        alive &= (W > 0)                                # absorbing ruin
        W = np.where(alive, W, 0.0)
    return np.median(W)                                 # ruined paths contribute 0

def add_noruin(sigma):
    m = 0.05; W = np.full(P, 10.0)
    for _ in range(T):
        W = W + rng.normal(m, sigma, P)
    return np.median(W)

print(f"{'process':<26}{'median @ high vol':>18}{'median @ half vol':>18}{'risk-mgmt gain':>16}")
for name, fn, hi in [("(1) MULTIPLICATIVE", mult, 0.20),
                     ("(2) ADDITIVE + RUIN", add_ruin, 1.5),
                     ("(3) ADDITIVE, no barrier", add_noruin, 1.5)]:
    h = fn(hi); l = fn(hi/2)
    gain = (l-h)/abs(h) if h!=0 else float('inf')
    print(f"{name:<26}{h:>18.3f}{l:>18.3f}{gain:>15.1%}")
print("\n=> Halving volatility sharply improves the typical outcome for MULTIPLICATIVE (drag removed)"
      "\n   AND for ADDITIVE+RUIN (ruin avoided) -- but barely moves ADDITIVE-no-barrier (ergodic)."
      "\n   So 'finance = risk management' is driven by NON-ERGODICITY (ruin / path-dependence), of"
      "\n   which multiplicativity is one instance, not THE cause. Belief REFINED.")
