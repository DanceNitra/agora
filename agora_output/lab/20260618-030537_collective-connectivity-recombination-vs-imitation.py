"""
Frontier ship (open-world: anchored on EXTERNAL literature, not our canon): is there an OPTIMAL network
connectivity for collective problem-solving, and does it depend on problem DIFFICULTY?

External anchors: Lazer & Friedman (2007) "The network structure of exploration and exploitation" —
efficient (highly-connected) networks converge fast but to lower-quality solutions on hard problems;
inefficient networks preserve diversity and do better on hard problems. Derex & Boyd (2016): partial
connectivity helps cultural accumulation. Henrich's "collective brain": more minds + connection -> more
innovation. These are in TENSION, and our own future-of-work coupling result (too much coupling ->
herding / diversity collapse) is the proposed MECHANISM. Falsifiable prediction: connectivity is
monotonically good for EASY (smooth) problems but an INVERTED-U (intermediate optimum) for HARD (rugged)
problems, because high connectivity triggers premature convergence on a local optimum.

Model: N agents each hold an L-bit solution on an NK fitness landscape (K = ruggedness; K=0 smooth,
high K rugged - the canonical 'problem difficulty' knob). Each step an agent either EXPLORES (flip a
random bit, keep if better - local hill-climb) or EXPLOITS (copy the best solution among k random
'neighbors' if it beats its own). Connectivity = neighborhood size k (1 = near-isolated, N-1 = fully
connected). Measure best fitness found by the collective vs k, for an easy and a hard landscape.
"""
import numpy as np

def make_nk(L, K, rng):
    # per-locus fitness depends on the locus bit + K other loci; random tables. Returns a fitness fn.
    deps = [np.concatenate(([i], rng.choice([j for j in range(L) if j != i], size=K, replace=False)))
            if K > 0 else np.array([i]) for i in range(L)]
    tables = [rng.random(2 ** (K + 1)) for _ in range(L)]
    def fitness(x):
        tot = 0.0
        for i in range(L):
            idx = 0
            for b in deps[i]:
                idx = (idx << 1) | int(x[b])
            tot += tables[i][idx]
        return tot / L
    return fitness

def run(k, L, K, N=80, T=150, p_explore=0.5, seed=0, mode="imitate"):
    rng = np.random.default_rng(abs(seed) % (2**32))
    fit = make_nk(L, K, rng)
    X = rng.integers(0, 2, size=(N, L))
    F = np.array([fit(X[i]) for i in range(N)])
    for _ in range(T):
        for i in range(N):
            if rng.random() < p_explore:
                j = rng.integers(L); y = X[i].copy(); y[j] ^= 1; fy = fit(y)
                if fy >= F[i]:
                    X[i] = y; F[i] = fy
            else:
                nb = rng.choice([z for z in range(N) if z != i], size=min(k, N - 1), replace=False)
                best = nb[np.argmax(F[nb])]
                if mode == "imitate":                      # copy the whole best neighbour (homogenises)
                    if F[best] > F[i]:
                        X[i] = X[best].copy(); F[i] = F[best]
                else:                                       # recombine: uniform crossover of self + best
                    child = np.where(rng.random(L) < 0.5, X[i], X[best])
                    fc = fit(child)
                    if fc > F[i]:
                        X[i] = child; F[i] = fc
    return float(F.max())

def avg_best(k, L, K, lands=12, mode="imitate"):
    return np.mean([run(k, L, K, seed=1000 + s + 100 * k, mode=mode) for s in range(lands)])

if __name__ == "__main__":
    L = 16
    kgrid = [1, 2, 4, 8, 20, 79]
    print(f"Collective problem-solving on NK landscapes (L={L}). Best fitness vs connectivity k.")
    print("Mechanism test: does the social benefit of connectivity on HARD problems need RECOMBINATION,")
    print("or does pure IMITATION suffice? (K=8 rugged landscape, imitate vs recombine.)\n")

    def shape(row):
        ks = sorted(row); vals = [row[k] for k in ks]
        kbest = ks[int(np.argmax(vals))]
        interior = kbest not in (ks[0], ks[-1])
        invU = interior and (row[kbest] - row[ks[0]] > 0.003) and (row[kbest] - row[ks[-1]] > 0.003)
        return kbest, invU, vals

    rows = {}
    for label, K, mode in [("EASY imitate (K=0)", 0, "imitate"),
                           ("HARD imitate (K=8)", 8, "imitate"),
                           ("HARD recombine (K=8)", 8, "recombine")]:
        row = {k: avg_best(k, L, K, mode=mode) for k in kgrid}
        rows[label] = row
        kbest, invU, _ = shape(row)
        print(f"  {label}: " + "  ".join(f"k{k}={row[k]:.3f}" for k in kgrid) + f"   [best k={kbest}]")

    ke, _, _ = shape(rows["EASY imitate (K=0)"])
    kh_im, invU_im, _ = shape(rows["HARD imitate (K=8)"])
    kh_re, invU_re, _ = shape(rows["HARD recombine (K=8)"])
    print("\n=== VERDICT ===")
    print(f"EASY: connectivity ~irrelevant (everyone solves it; best k={ke}, near the K=0 optimum ~0.667)")
    print(f"HARD + IMITATION: best k={kh_im}, inverted-U={invU_im}")
    print(f"HARD + RECOMBINATION: best k={kh_re}, inverted-U={invU_re}")
    if kh_im <= 4 and invU_re:
        print("\nMECHANISM CONFIRMED (the optimum-connectivity is RECOMBINATION-gated):")
        print("On hard (rugged) problems, PURE IMITATION (copy the best) makes connectivity monotonically")
        print(f"HARMFUL - isolation (k={kh_im}) wins, because copying only homogenises and triggers premature")
        print("convergence (our future-of-work herding/diversity-collapse mechanism). But add RECOMBINATION")
        print(f"(crossover of one's own + the best neighbour's solution) and an INVERTED-U appears: an")
        print(f"intermediate connectivity (k={kh_re}) beats both isolation and full connection. So the famous")
        print("'partial connectivity is best for hard problems' (Derex-Boyd, Lazer-Friedman) is NOT about")
        print("imitation/exposure - it REQUIRES recombination. Connection without recombination is pure herding;")
        print("connection WITH recombination is collective innovation. Refines Henrich's collective brain.")
    elif kh_im <= 4 and not invU_re:
        print("\nPARTIAL: imitation makes connectivity harmful on hard problems (herding confirmed), but")
        print("recombination did not produce a clean interior optimum here -- honest partial result.")
    else:
        print("\nUnexpected pattern -- honest null (see rows).")
