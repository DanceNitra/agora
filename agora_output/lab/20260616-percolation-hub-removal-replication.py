# Crucible replication (A24) of: "For BA networks with N=2,000 and m=2, removing the top 10%
# of nodes by degree raises the bond-percolation threshold from p_c=0.174 to 0.776."
# Source: Cachero Sanchez (2026), "Simultaneous Degradation of Percolation and Cascade
# Robustness Under Targeted Hub Removal".
# Smallest model: the standard Molloy-Reed criterion p_c = <k> / (<k^2> - <k>) on the intact
# network vs the residual after deleting the top-10%-degree nodes, plus a Monte-Carlo
# bond-percolation cross-check (occupy edges w.p. p; threshold = p where the giant component
# first spans an O(1) fraction). 30 BA replicas, seeded.
import numpy as np

try:
    import networkx as nx
    HAVE_NX = True
except Exception:
    HAVE_NX = False


def ba_graph(n, m, seed):
    """Barabasi-Albert via preferential attachment (networkx if present, else manual)."""
    if HAVE_NX:
        G = nx.barabasi_albert_graph(n, m, seed=seed)
        return {i: set(G.neighbors(i)) for i in G.nodes()}
    rng = np.random.default_rng(seed)
    adj = {i: set() for i in range(n)}
    targets = list(range(m))
    repeated = []                                   # preferential-attachment urn
    for v in range(m, n):
        chosen = set()
        while len(chosen) < m:
            chosen.add(repeated[rng.integers(len(repeated))] if repeated else int(rng.integers(v)))
        for t in chosen:
            adj[v].add(t); adj[t].add(v)
            repeated += [t, v]
    return adj


def molloy_reed_pc(adj):
    k = np.array([len(s) for s in adj.values()], dtype=float)
    k1, k2 = k.mean(), (k ** 2).mean()
    return k1 / (k2 - k1) if (k2 - k1) > 0 else float("inf")


def remove_top_hubs(adj, frac=0.10):
    n_rm = int(frac * len(adj))
    top = set(sorted(adj, key=lambda u: -len(adj[u]))[:n_rm])
    return {u: (adj[u] - top) for u in adj if u not in top}


def mc_bond_threshold(adj, ps, seed):
    """Monte-Carlo: for each p, occupy edges w.p. p, return p where the largest component first
    exceeds 1% of nodes (an operational giant-component onset)."""
    rng = np.random.default_rng(seed)
    nodes = list(adj)
    edges = [(u, v) for u in adj for v in adj[u] if u < v]
    nN = len(nodes)
    for p in ps:
        keep = rng.random(len(edges)) < p
        parent = {u: u for u in nodes}
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        for (u, v), k in zip(edges, keep):
            if k:
                ru, rv = find(u), find(v)
                if ru != rv:
                    parent[ru] = rv
        from collections import Counter
        big = max(Counter(find(u) for u in nodes).values())
        if big >= 0.01 * nN:
            return p
    return ps[-1]


N, M, REPS = 2000, 2, 30
intact_mr, removed_mr = [], []
for r in range(REPS):
    adj = ba_graph(N, M, seed=r)
    intact_mr.append(molloy_reed_pc(adj))
    removed_mr.append(molloy_reed_pc(remove_top_hubs(adj, 0.10)))

# MC cross-check on a few replicas (cheaper)
ps = np.round(np.arange(0.02, 1.0, 0.02), 2)
intact_mc = [mc_bond_threshold(ba_graph(N, M, seed=r), ps, seed=100 + r) for r in range(5)]
removed_mc = [mc_bond_threshold(remove_top_hubs(ba_graph(N, M, seed=r), 0.10), ps, seed=200 + r) for r in range(5)]

print(f"BA N={N}, m={M}, {REPS} replicas | networkx={HAVE_NX}")
print(f"{'':<22}{'CLAIMED':>10}{'Molloy-Reed':>14}{'MC (1% giant)':>15}")
print(f"{'intact p_c':<22}{0.174:>10}{np.mean(intact_mr):>14.3f}{np.mean(intact_mc):>15.3f}")
print(f"{'top-10% hubs removed':<22}{0.776:>10}{np.mean(removed_mr):>14.3f}{np.mean(removed_mc):>15.3f}")
print(f"\nrise (Molloy-Reed): {np.mean(intact_mr):.3f} -> {np.mean(removed_mr):.3f} "
      f"({np.mean(removed_mr)/np.mean(intact_mr):.1f}x)")
print(f"claimed rise:        0.174 -> 0.776 (4.5x)")


# --- Refined: susceptibility-peak threshold on the ACTUAL BA network (captures correlations
#     the Molloy-Reed config-model estimate misses). Threshold = p maximizing mean 2nd-largest
#     cluster size. This is the standard finite-size simulation method the paper likely used.
def susceptibility_threshold(adj, ps, reps, seed0):
    nodes = list(adj); edges = [(u, v) for u in adj for v in adj[u] if u < v]
    from collections import Counter
    mean_s2 = []
    for p in ps:
        s2s = []
        for rr in range(reps):
            rng = np.random.default_rng(seed0 + 1000 * int(p * 100) + rr)
            keep = rng.random(len(edges)) < p
            parent = {u: u for u in nodes}
            def find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]; x = parent[x]
                return x
            for (u, v), k in zip(edges, keep):
                if k:
                    ru, rv = find(u), find(v)
                    if ru != rv:
                        parent[ru] = rv
            sizes = sorted(Counter(find(u) for u in nodes).values(), reverse=True)
            s2s.append(sizes[1] if len(sizes) > 1 else 0)
        mean_s2.append(np.mean(s2s))
    return ps[int(np.argmax(mean_s2))]

ps2 = np.round(np.arange(0.04, 0.96, 0.02), 2)
it = [susceptibility_threshold(ba_graph(N, M, seed=r), ps2, 8, 7000 + r) for r in range(6)]
rm = [susceptibility_threshold(remove_top_hubs(ba_graph(N, M, seed=r), 0.10), ps2, 8, 8000 + r) for r in range(6)]
print(f"\n--- susceptibility-peak (finite-size MC on actual BA) ---")
print(f"intact  p_c: {np.mean(it):.3f} (claimed 0.174)")
print(f"removed p_c: {np.mean(rm):.3f} (claimed 0.776)")
