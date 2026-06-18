# Replicate Derenyi, Palla, Vicsek (2005): k-clique percolation in Erdos-Renyi graphs occurs at
#   p_c(k) = 1 / [ (k-1) N ]^(1/(k-1))
# (two k-cliques are adjacent if they share k-1 nodes; a giant k-clique community emerges at p_c).
# k=2 recovers the standard ER giant component p_c=1/N. Test k=3: predicted p_c = 1/sqrt(2N), so the
# scaled threshold p_c * sqrt(2N) should be ~1 across N. Smallest model: ER graph -> enumerate
# triangles -> union triangles sharing an edge -> giant-community onset. Source: simulation.
import numpy as np, networkx as nx
from collections import defaultdict
rng = np.random.default_rng(3)

def giant_triangle_frac(N, p, seed):
    G = nx.erdos_renyi_graph(N, p, seed=seed)
    # enumerate triangles
    tris = []
    adj = {u: set(G[u]) for u in G}
    for u, v in G.edges():
        for w in adj[u] & adj[v]:
            if w > v > u or (w>u and w>v and v>u):   # ordered to dedup
                tris.append((u, v, w))
    tris = list({tuple(sorted(t)) for t in tris})
    if len(tris) < 2:
        return 0.0, len(tris)
    # union-find over triangles sharing an edge (k-1=2 nodes)
    parent = list(range(len(tris)))
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[ra]=rb
    edge_to_tri = defaultdict(list)
    for i,(a,b,c) in enumerate(tris):
        for e in [(a,b),(a,c),(b,c)]:
            edge_to_tri[e].append(i)
    for e,lst in edge_to_tri.items():
        for j in lst[1:]:
            union(lst[0], j)
    comp = defaultdict(int)
    for i in range(len(tris)): comp[find(i)] += 1
    giant = max(comp.values())
    return giant/len(tris), len(tris)

print("k=3 clique percolation: predicted p_c = 1/sqrt(2N). Empirical p_c (giant triangle-community onset):")
print(f"  {'N':>6}{'predicted p_c':>15}{'empirical p_c':>15}{'p_c*sqrt(2N)':>14}")
for N in [400, 800, 1600]:
    pc_pred = 1/np.sqrt(2*N)
    ps = np.linspace(0.45*pc_pred, 2.0*pc_pred, 22)
    pc_emp = None
    for p in ps:
        fr = np.mean([giant_triangle_frac(N, p, s)[0] for s in range(4)])
        if fr >= 0.5 and pc_emp is None:        # giant community spans >=50% of triangles
            pc_emp = p; break
    scaled = pc_emp*np.sqrt(2*N) if pc_emp else float('nan')
    print(f"  {N:>6}{pc_pred:>15.4f}{(pc_emp if pc_emp else float('nan')):>15.4f}{scaled:>14.3f}")
print("\n=> If empirical p_c tracks 1/sqrt(2N) (scaled column ~1, roughly constant across N), the DPV"
      "\n   k-clique percolation threshold is reproduced. (k=2 special case is the textbook ER 1/N.)")
