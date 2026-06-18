
import random, math
random.seed(11)   # independent seed/impl from Lab 678a9c

def collective_accuracy(N, k, w, p=0.60, trials=300, disc=1.0):
    """Sequential Bayesian-ish herding. truth=1. Each agent: private signal correct w.p. p,
    observes k random EARLIER actions, sums log-evidence (own weighted by w, each observed action
    weighted by `disc`), acts by sign. disc<1 = rational discount for action redundancy.
    Returns P(majority of N actions correct)."""
    L = math.log(p/(1-p))
    good = 0
    for _ in range(trials):
        acts = []
        for i in range(N):
            s = 1 if random.random() < p else 0
            llr = w * (L if s else -L)
            if i and k:
                for a in random.sample(acts, min(k, i)):
                    llr += disc * (L if a else -L)
            acts.append(1 if llr > 0 else (0 if llr < 0 else (1 if random.random()<.5 else 0)))
        m = sum(acts)
        good += 1 if m > N/2 else (1 if m*2==N and random.random()<.5 else 0)
    return good/trials

def first_collapse_k(w, p=0.60, thresh=0.75, N=401):
    """smallest k at which accuracy drops below `thresh` (collapse onset)."""
    for k in range(1, 9):
        if collective_accuracy(N, k, w, p) < thresh:
            return k
    return None

print("A) accuracy vs k  (w=1, N=401, p=0.60):")
for k in (0,1,2,3,5,100):
    print(f"   k={k:>3}: {collective_accuracy(401,k,1):.3f}")

print("\nB) collapse-onset k_c vs own-weight w  (predict k_c = w+1):")
for w in (1,2,4):
    kc = first_collapse_k(w)
    print(f"   w={w}: k_c={kc}   (w+1={w+1}) {'OK' if kc==w+1 else 'MISS'}")

print("\nC) RED-TEAM 1 — is k_c=w+1 p-independent? (derivation says yes):")
for p in (0.55, 0.60, 0.75):
    kc = first_collapse_k(1, p=p)
    print(f"   p={p}: k_c(w=1)={kc}  (expect 2)")

print("\nD) RED-TEAM 2 — rational redundancy discount (observed action worth disc<1 of a signal):")
print("   if agents discount correlated actions, collapse should push to higher k:")
for disc in (1.0, 0.5):
    accs = [round(collective_accuracy(401,k,1,disc=disc),3) for k in (2,4,6)]
    print(f"   disc={disc}: acc at k=2,4,6 = {accs}")
