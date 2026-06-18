# Challenge to the belief "the cure for a herding crowd is expensive — you need ~80%
# forced-independent voices" (lab aa23bf). The note's OWN falsifier names the weak point:
# order-of-arrival. Test: place a small fraction of independents FIRST (a sealed-vote
# vanguard) vs interspersed at random. If a small early fraction restores accuracy, the
# "~80%" threshold is an artifact of WHEN independence acts, not HOW MUCH.
# Model: classic BHW sequential information cascade, binary signal precision p=0.60.
import random

P = 0.60

def trial(N, alpha, placement, rng):
    omega = 1  # true state
    if placement == "random":
        indep = [rng.random() < alpha for _ in range(N)]
    else:  # "first": the alpha*N independents act before anyone can herd
        k = int(round(alpha * N))
        indep = [i < k for i in range(N)]
    up = down = 0
    for i in range(N):
        s = omega if rng.random() < P else 1 - omega
        if indep[i]:
            a = s  # acts on private signal only (blind / sealed vote)
        else:
            diff = up - down  # BHW rule: herd once net public actions reach +/-2
            a = 1 if diff >= 2 else (0 if diff <= -2 else s)
        if a == 1: up += 1
        else: down += 1
    return 1 if up > down else (0 if down > up else rng.randint(0, 1))

def accuracy(N, alpha, placement, trials=4000, seed=42):
    rng = random.Random(seed)
    return sum(trial(N, alpha, placement, rng) == 1 for _ in range(trials)) / trials

print(f"Sequential BHW cascade, p={P}, 4000 trials. Collective (majority) accuracy.")
print(f"{'alpha':>6} | {'random N=1001':>14} | {'INDEP-FIRST N=1001':>18}")
for a in [0.0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.80]:
    r = accuracy(1001, a, "random")
    f = accuracy(1001, a, "first")
    print(f"{a:>6.2f} | {r:>14.3f} | {f:>18.3f}")
