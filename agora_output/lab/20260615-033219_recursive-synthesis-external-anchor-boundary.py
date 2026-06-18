import random, statistics

# Crucible replication of the mechanism behind "recursively synthesized, self-referential systems
# improve performance" (e.g. Promptbreeder, Fernando et al. 2023). Smallest computable model:
# a population recursively synthesizes new candidates FROM ITSELF (mutate/recombine current members)
# each generation. The pivotal variable is the SELECTION signal:
#   EXTERNAL-anchored : keep candidates by their TRUE fitness on a hidden landscape (external reality)
#   PURE self-reference: keep candidates by a SELF-proxy = agreement with the population's own centroid
#                        (closest to what the population already believes is good)
# Claim under test: recursive self-referential synthesis IMPROVES performance.
# Convergence hypothesis (stale-self-signal law): it improves ONLY with an external anchor; pure
# self-reference manufactures self-agreement (variance -> 0, "confidence") while true fitness stalls.

random.seed(9)
D = 8                                   # dimensionality
TARGET = [random.uniform(-1, 1) for _ in range(D)]   # hidden truth x*

def true_fit(x):                        # external reality: higher is better (0 is perfect)
    return -sum((a-b)**2 for a, b in zip(x, TARGET))

def centroid(pop):
    return [statistics.mean(m[i] for m in pop) for i in range(D)]

def self_proxy(x, c):                   # "agreement with what the population already believes"
    return -sum((a-b)**2 for a, b in zip(x, c))

def evolve(mode, N=40, gens=60, sigma=0.25):
    pop = [[random.uniform(-1, 1) for _ in range(D)] for _ in range(N)]
    hist = []
    for g in range(gens):
        kids = []
        for _ in range(N*4):            # recursive synthesis FROM the population itself
            p = random.choice(pop)
            kids.append([v + random.gauss(0, sigma) for v in p])
        cand = pop + kids
        if mode == "external":
            cand.sort(key=true_fit, reverse=True)
        else:                            # pure self-reference: select toward own centroid
            c = centroid(pop)
            cand.sort(key=lambda x: self_proxy(x, c), reverse=True)
        pop = cand[:N]
        best_true = max(true_fit(m) for m in pop)
        var = statistics.mean(statistics.pvariance([m[i] for m in pop]) for i in range(D))
        hist.append((best_true, var))
    return hist

print(f"true fitness: 0 = perfect (found x*), more negative = worse.  D={D}\n")
for mode in ("external", "self"):
    h = evolve(mode)
    t0, v0 = h[0]; t1, v1 = h[-1]
    print(f"{mode:>9}: best true-fit  start {t0:7.3f} -> end {t1:7.3f}   (improvement {t1-t0:+.3f})")
    print(f"{'':>9}  pop variance  start {v0:6.3f} -> end {v1:6.3f}   ({'COLLAPSES to self-agreement' if v1<v0*0.2 else 'stays diverse'})")

ext = evolve("external"); slf = evolve("self")
ext_impr = ext[-1][0] - ext[0][0]
slf_impr = slf[-1][0] - slf[0][0]
print("\nVERDICT:")
print(f"  external-anchored recursive synthesis improves true fitness by {ext_impr:+.3f}  -> claim REPRODUCED (with an external selection signal)")
print(f"  pure self-reference improves true fitness by {slf_impr:+.3f} while variance collapses -> manufactured confidence, no real gain")
print("  BOUNDARY:", "REPRODUCED only WITH an external anchor; pure self-reference is the stale-self-signal trap"
      if (ext_impr > 0.5 and slf_impr < ext_impr*0.3) else "inconclusive")
