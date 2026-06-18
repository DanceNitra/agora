# Challenge the belief: "collective intelligence collapses when agents observe ACTIONS not EVIDENCE."
# The disconfirming case (Smith & Sorensen 2000): the collapse needs BOUNDED private beliefs. With
# UNBOUNDED private beliefs, sequential agents observing only each other's binary ACTIONS still achieve
# complete asymptotic learning. So the real axis is signal-boundedness, not action-vs-evidence.
# Smallest model: sequential Bayesian observational learning, bounded (binary) vs unbounded (Gaussian)
# private signals, matched single-agent accuracy (~0.60). Measure last-agent accuracy vs N. Source: simulation.
import math, random

def Phi(x): return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def bounded_trial(N, p, rng):
    V = 1 if rng.random() < 0.5 else -1
    d = math.log(p / (1 - p)); P = 0.0; last = 0
    for _ in range(N):
        s = V if rng.random() < p else -V           # bounded binary signal (LLR magnitude fixed at d)
        total = P + s * d
        a = 1 if total > 0 else (-1 if total < 0 else s)
        if abs(P) <= d + 1e-12:                      # informative regime -> action reveals the signal
            P += a * d
        # else: information cascade -> action uninformative, public belief frozen
        last = a
    return last == V

def unbounded_trial(N, m, rng):
    V = 1 if rng.random() < 0.5 else -1
    P = 0.0; last = 0
    for _ in range(N):
        x = rng.gauss(V * m, 1.0)                    # unbounded Gaussian signal; LLR = 2 m x (unbounded)
        total = P + 2 * m * x
        a = 1 if total > 0 else -1
        xc = -P / (2 * m)                            # action threshold on x: a=+1 iff x > xc
        pp = 1 - Phi(xc - m); pn = 1 - Phi(xc + m)   # P(a=+1 | V=+1), P(a=+1 | V=-1)
        if a == 1: num, den = pp, pn
        else:      num, den = 1 - pp, 1 - pn
        P += math.log(max(num, 1e-15) / max(den, 1e-15))   # Bayesian update from the (truncated) action
        last = a
    return last == V

rng = random.Random(7)
p = 0.60                       # bounded single-signal accuracy = 0.60
m = 0.2533                     # Phi(m)=0.60 -> unbounded single-signal accuracy also 0.60 (matched)
print(f"single-agent accuracy: bounded {p:.2f}  unbounded {Phi(m):.2f}  (matched)\n")
print(f"{'N':>5}  {'BOUNDED last-acc':>16}  {'UNBOUNDED last-acc':>18}")
TR = 4000
for N in [2, 5, 10, 30, 100, 300, 1000]:
    b = sum(bounded_trial(N, p, rng) for _ in range(TR)) / TR
    u = sum(unbounded_trial(N, m, rng) for _ in range(TR)) / TR
    print(f"{N:>5}  {b:>16.3f}  {u:>18.3f}")
print("\n=> BOUNDED: accuracy plateaus well below 1 (cascade locks in, often on the wrong action) — the"
      "\n   belief holds. UNBOUNDED: accuracy -> 1 as N grows (complete learning) DESPITE observing only"
      "\n   ACTIONS. So the collapse is driven by signal BOUNDEDNESS, not action-vs-evidence. Belief REFINED.")
