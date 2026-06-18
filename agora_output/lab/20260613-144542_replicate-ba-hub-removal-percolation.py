
import numpy as np
rng = np.random.default_rng(0)
N, m = 2000, 2
# Barabasi-Albert preferential attachment
repeated = list(range(m))
edges = []
deg = np.zeros(N, dtype=np.int64)
for src in range(m, N):
    chosen = set()
    while len(chosen) < m:
        chosen.add(repeated[rng.integers(len(repeated))])
    for t in chosen:
        edges.append((src, t)); deg[src]+=1; deg[t]+=1
        repeated.append(src); repeated.append(t)

def pc_cohen(degseq):
    # bond-percolation threshold for an uncorrelated net (Cohen et al. 2000): k1/(k2-k1)
    k = degseq[degseq > 0]
    k1 = k.mean(); k2 = (k*k).mean()
    return float(k1/(k2-k1)) if k2 > k1 else float('inf')

pc0 = pc_cohen(deg)
k1_0, k2_0 = deg.mean(), (deg.astype(float)**2).mean()

# remove the top 10% of nodes BY DEGREE (targeted hub attack)
order = np.argsort(-deg)
remove = set(order[:int(0.10*N)].tolist())
keep = np.array([i not in remove for i in range(N)])
deg2 = np.zeros(N, dtype=np.int64)
for a, b in edges:
    if keep[a] and keep[b]:
        deg2[a]+=1; deg2[b]+=1
res = deg2[keep]
pc1 = pc_cohen(res)
k1_1, k2_1 = res.mean(), (res.astype(float)**2).mean()

print(f"BEFORE: <k>={k1_0:.2f} <k^2>={k2_0:.1f}  p_c={pc0:.3f}   (claim 0.174)")
print(f"AFTER : <k>={k1_1:.2f} <k^2>={k2_1:.1f}  p_c={pc1:.3f}   (claim 0.776)")
print(f"DIRECTION: p_c rises x{pc1/pc0:.1f} on hub removal -> network far HARDER to percolate (more fragile to targeted attack)")
# verdict heuristic
near = lambda a,b: abs(a-b) <= 0.06 + 0.25*b
print("MATCH_before", near(pc0,0.174), "MATCH_after", near(pc1,0.776))
