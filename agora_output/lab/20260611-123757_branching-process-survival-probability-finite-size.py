import random, math, statistics as st
random.seed(42)

# Claim (Garcia-Millan, Font-Clos, Corral 2015): branching processes show finite-size scaling of
# the survival probability P_n as a function of the control parameter m (branching ratio) and the
# maximum number of generations n. At criticality (m=1), theory: P_n ~ 2/(sigma^2 * n) ~ C/n; and
# the data collapse n*P_n vs (m-1)*n onto a single scaling function. Smallest model: Galton-Watson
# with Poisson(m) offspring; survival = population still >0 at generation n. Source: simulation.

POP_CAP = 200000          # treat blow-up as 'survived' (supercritical realisations)

def poisson(lmbda):
    if lmbda > 30:        # normal approx for speed/stability at large mean
        return max(0, int(round(random.gauss(lmbda, math.sqrt(lmbda)))))
    L = math.exp(-lmbda); k = 0; p = 1.0
    while True:
        k += 1; p *= random.random()
        if p <= L: return k - 1

def survives(m, n):
    pop = 1
    for _ in range(n):
        if pop == 0: return False
        if pop >= POP_CAP: return True
        pop = poisson(pop * m)
    return pop > 0

def surv_prob(m, n, trials):
    return sum(1 for _ in range(trials) if survives(m, n)) / trials

print("Critical branching (m=1): theory P_n ~ 2/(sigma^2 n), sigma^2=1 -> n*P_n -> 2\n")
print(f"{'n':>5} {'P_n':>10} {'n*P_n':>8}")
for n in (10, 20, 40, 80, 160):
    tr = 40000 if n <= 40 else 80000
    p = surv_prob(1.0, n, tr)
    print(f"{n:5d} {p:10.4f} {n*p:8.3f}")

print("\nFinite-size-scaling collapse: n*P_n should match at equal x=(m-1)*n")
print(f"{'(m-1)*n':>8} {'m':>6} {'n':>5} {'n*P_n':>8}")
for x in (-2.0, 0.0, 2.0):
    for n in (40, 80):
        m = 1.0 + x / n
        tr = 60000
        p = surv_prob(m, n, tr)
        print(f"{x:8.1f} {m:6.3f} {n:5d} {n*p:8.3f}")
print("\nREPRODUCED iff (a) n*P_n -> const ~2 at m=1 (exponent -1) and (b) n*P_n collapses at equal (m-1)*n.")
