import numpy as np
rng = np.random.default_rng(11)

# Critical Transitions -> Knowledge Debt.
# A vault is N belief-nodes on a random graph; an edge = "these two cohere".
# Knowledge debt = a fraction q of edges silently flip to CONTRADICTION, severing coherence.
# Q: does the largest mutually-coherent component shrink GRADUALLY with debt, or COLLAPSE
# abruptly at a critical debt fraction (a phase transition)? Percolation predicts a threshold.
N, K = 400, 6                       # 400 notes, avg degree 6
N_SIM = 40

def giant_component_frac(q):
    # Erdos-Renyi-ish graph, keep each edge with prob (1-q) (debt severs the rest)
    p_edge = K / (N - 1)
    A = (rng.random((N, N)) < p_edge)
    A = np.triu(A, 1); A = A | A.T
    keep = (rng.random((N, N)) >= q)
    keep = np.triu(keep, 1); keep = keep | keep.T
    A = A & keep
    # largest connected component via BFS
    seen = np.zeros(N, bool); best = 0
    for s in range(N):
        if seen[s]: continue
        stack=[s]; seen[s]=True; size=0
        while stack:
            u=stack.pop(); size+=1
            for v in np.nonzero(A[u])[0]:
                if not seen[v]: seen[v]=True; stack.append(v)
        best=max(best,size)
    return best/N

print("Critical Transitions -> Knowledge Debt: largest coherent component vs debt fraction")
print(f"(N={N} notes, avg degree {K}, {N_SIM} graphs/point)\n")
print(f"{'debt q':>7} {'coherent_frac':>14} {'drop':>7}")
prev=None
for q in [0.0,0.2,0.4,0.5,0.6,0.7,0.8,0.83,0.86,0.9,0.95]:
    fr=np.mean([giant_component_frac(q) for _ in range(N_SIM)])
    drop = "" if prev is None else f"{(prev-fr):+.2f}"
    print(f"{q:7.2f} {fr:14.3f} {drop:>7}")
    prev=fr
print("\nReading: percolation predicts an ABRUPT collapse near a critical debt fraction, not a")
print("linear decline. The steepest single-step drop marks the knowledge-debt phase transition.")
