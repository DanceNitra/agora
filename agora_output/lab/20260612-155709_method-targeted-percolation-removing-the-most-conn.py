
import numpy as np
rng = np.random.default_rng(7)
n, m, q = 1000, 2, 0.05
# build BA
targets = list(range(m)); deg = np.zeros(n, int); edges = []
for v in range(m, n):
    chosen = set()
    while len(chosen) < m:
        chosen.add(targets[rng.integers(len(targets))])
    for u in chosen:
        edges.append((u, v)); deg[u] += 1; deg[v] += 1; targets += [u, v]
edges = np.array(edges)
def threshold(mask_nodes):
    keep = np.array([not (mask_nodes[u] or mask_nodes[v]) for u, v in edges])
    E = edges[keep]
    if len(E) == 0: return 1.0
    for phi in np.linspace(0.02, 1.0, 50):
        sel = E[rng.random(len(E)) < phi]
        parent = np.arange(n)
        def find(a):
            while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
            return a
        for u, v in sel: parent[find(u)] = find(v)
        roots, counts = np.unique([find(i) for i in range(n) if not mask_nodes[i]], return_counts=True)
        if counts.max() > 0.5*(n - mask_nodes.sum()): return phi
    return 1.0
none = np.zeros(n, bool)
top = np.zeros(n, bool); top[np.argsort(deg)[::-1][:int(q*n)]] = True
rnd = np.zeros(n, bool); rnd[rng.choice(n, int(q*n), replace=False)] = True
t0, tt, tr = threshold(none), threshold(top), threshold(rnd)
print(f"MEASURED: phi_c intact={t0:.3f} targeted(top {q:.0%})={tt:.3f} random={tr:.3f} -> targeted multiplies threshold {tt/max(t0,1e-9):.1f}x (random {tr/max(t0,1e-9):.1f}x)")
print(f"VERDICT: {'HUB REMOVAL DOMINATES - targeted attack is categorically worse' if tt > 2*tr else 'no strong hub effect at these parameters'}")
