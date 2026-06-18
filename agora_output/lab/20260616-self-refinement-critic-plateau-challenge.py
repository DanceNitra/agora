# Challenge (A13) to the belief "self-refinement amplifies the critic - above a=0.5 it compounds
# toward EXCELLENCE (->1)" (lab ea3869). That result assumes a CONSTANT critic accuracy a. Real
# critics decay toward chance as the answer nears optimal (gross errors are easy to flag; near-perfect
# answers are hard to judge). Test: with a quality-dependent critic a(q) that fades to 0.5 as q->1,
# does refinement still reach excellence, or does it PLATEAU where the critic becomes uninformative?
import random, statistics

def refine(a_func, T, s=0.03, q0=0.5, trials=20000, seed=42):
    rng = random.Random(seed)
    finals = []
    for _ in range(trials):
        q = q0
        for _ in range(T):
            a = a_func(q)
            q = min(1.0, q + s) if rng.random() < a else max(0.0, q - s)
        finals.append(q)
    return statistics.mean(finals)

# 1) ANCHOR: reproduce the belief's constant-critic result (should rise toward ~1 for a>0.5).
print("ANCHOR (constant critic) - reproduce belief ea3869:")
print(f"{'a':>6}{'T=5':>9}{'T=20':>9}{'T=50':>9}")
for a in [0.30, 0.50, 0.70]:
    row = [refine(lambda q, a=a: a, T) for T in (5, 20, 50)]
    print(f"{a:>6}{row[0]:>9.3f}{row[1]:>9.3f}{row[2]:>9.3f}")

# 2) CHALLENGE: quality-dependent critic that decays to chance as q->1.
#    a(q) = 0.5 + (a0 - 0.5) * (1 - q)^gamma   (at q=0 -> a0; at q=1 -> 0.5)
print("\nCHALLENGE (critic decays to chance as quality rises), gamma=1:")
print(f"{'a0':>6}{'T=5':>9}{'T=20':>9}{'T=50':>9}{'T=200':>10}")
for a0 in [0.55, 0.70, 0.80, 0.95]:
    af = lambda q, a0=a0: 0.5 + (a0 - 0.5) * (1 - q)
    row = [refine(af, T) for T in (5, 20, 50, 200)]
    print(f"{a0:>6}{row[0]:>9.3f}{row[1]:>9.3f}{row[2]:>9.3f}{row[3]:>10.3f}")

# 3) Where does the plateau sit? Analytic fixed point: drift = 0 when a(q*) = 0.5, i.e. q* = 1
#    in the limit, BUT the random walk stalls earlier where step-up prob ~ step-down. Report the
#    measured asymptote (T=200) vs the belief's claimed near-1.
print("\nBelief claims a>0.5 compounds toward EXCELLENCE (~0.96-0.98 by T=50).")
print("If the decaying-critic asymptote sits well below 1, the 'toward excellence' claim is refuted")
print("for realistic critics - refinement plateaus at the critic's competence ceiling.")
