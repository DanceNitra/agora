"""
Crucible replication (simulation): k-clique percolation threshold in Erdos-Renyi graphs.

Claim (Derenyi, Palla, Vicsek, PRL 2005, "Clique Percolation in Random Networks"):
  In G(N, p), the k-clique percolation transition (giant k-clique community appears) occurs at
      p_c(k) = 1 / [ (k-1) * N ]^(1/(k-1)).
  k=2 reduces to ordinary ER component percolation: p_c = 1/N.

CPM mechanism: a k-clique community = k-cliques connected through sharing (k-1) nodes. We build the
smallest model of exactly that: enumerate k-cliques, union any two that share a (k-1)-clique, then
track the largest community as p sweeps through the predicted threshold.

Order parameter R(p) = (vertices in the largest k-clique community) / N. We locate the empirical
transition as the p where R crosses half its swept maximum, and compare to the formula. Finite-N
deviation is expected and is itself the interesting measurement (the formula is asymptotic).
"""
import numpy as np
from itertools import combinations


def er_adj(N, p, rng):
    """ER graph as adjacency sets."""
    adj = [set() for _ in range(N)]
    # vectorized upper-triangle draw
    iu, ju = np.triu_indices(N, 1)
    mask = rng.random(len(iu)) < p
    for a, b in zip(iu[mask], ju[mask]):
        adj[a].add(int(b)); adj[b].add(int(a))
    return adj


class UF:
    def __init__(s): s.p = {}
    def find(s, x):
        s.p.setdefault(x, x)
        while s.p[x] != x:
            s.p[x] = s.p[s.p[x]]; x = s.p[x]
        return x
    def union(s, a, b):
        ra, rb = s.find(a), s.find(b)
        if ra != rb: s.p[ra] = rb


def k_cliques(adj, k):
    """All k-cliques (sorted tuples). Triangle/4-clique scale: fine for N<=400 near threshold."""
    N = len(adj)
    if k == 2:
        return [(a, b) for a in range(N) for b in adj[a] if a < b]
    cliques = []
    # grow from triangles: candidate (k)-clique = a (k-1)-clique + a common neighbor of all its nodes
    if k < 2:
        return []
    # start: edges
    base = [(a, b) for a in range(N) for b in adj[a] if a < b]
    size = 2
    cur = base
    while size < k:
        nxt = []
        for clq in cur:
            common = set.intersection(*[adj[v] for v in clq])
            for w in common:
                if w > clq[-1]:
                    nxt.append(clq + (w,))
        cur = nxt
        size += 1
        if not cur:
            break
    return cur


def largest_community_fraction(adj, k):
    cliques = k_cliques(adj, k)
    if not cliques:
        return 0.0
    uf = UF()
    # map each (k-1)-subset -> a representative clique; union cliques sharing a (k-1)-subset
    sub_rep = {}
    for c in cliques:
        uf.find(c)
        for sub in combinations(c, k - 1):
            if sub in sub_rep:
                uf.union(c, sub_rep[sub])
            else:
                sub_rep[sub] = c
    # gather components -> vertices covered
    comp_vertices = {}
    for c in cliques:
        r = uf.find(c)
        comp_vertices.setdefault(r, set()).update(c)
    biggest = max(len(v) for v in comp_vertices.values())
    return biggest / len(adj)


def transition_point(N, k, reps=6, span=(0.4, 1.8), npts=13, seed=0):
    pc = ((k - 1) * N) ** (-1.0 / (k - 1))
    ps = np.linspace(span[0] * pc, span[1] * pc, npts)
    R = np.zeros(npts)
    for s in range(reps):
        rng = np.random.default_rng(1000 + s + 100 * k + N)
        for i, p in enumerate(ps):
            R[i] += largest_community_fraction(er_adj(N, float(p), rng), k)
    R /= reps
    # empirical threshold: where R crosses half its max (linear interp)
    half = R.max() / 2.0
    cross = None
    for i in range(1, npts):
        if R[i - 1] < half <= R[i]:
            t = (half - R[i - 1]) / (R[i] - R[i - 1] + 1e-12)
            cross = ps[i - 1] + t * (ps[i] - ps[i - 1])
            break
    return pc, cross, ps, R


print("k-clique percolation: predicted p_c(k) = [(k-1)N]^(-1/(k-1)) vs measured transition\n")
rows = []
for (k, N) in [(2, 600), (3, 220), (3, 400), (4, 130)]:
    pc, cross, ps, R = transition_point(N, k)
    ratio = (cross / pc) if cross else float('nan')
    rows.append((k, N, pc, cross, ratio))
    print(f"k={k} N={N:>4}: formula p_c={pc:.4f}  measured~{cross:.4f}  ratio={ratio:.2f}"
          f"   Rmax={R.max():.2f}")
    print(f"          R(p/pc): " + " ".join(f"{p/pc:.2f}:{r:.2f}" for p, r in zip(ps, R)))

# verdict: a clean reproduction has measured transitions tracking the formula (ratio ~ O(1),
# converging toward 1 as N grows). Large/systematic deviation that does NOT shrink with N = FAILED.
ratios = [r[4] for r in rows if not np.isnan(r[4])]
k3 = [r for r in rows if r[0] == 3]
converging = (len(k3) == 2 and abs(k3[1][4] - 1) <= abs(k3[0][4] - 1) + 0.15)  # k=3 ratio -> 1 as N up
in_band = all(0.6 <= r <= 1.6 for r in ratios)
print("\n=== VERDICT ===")
if in_band and converging:
    print("REPRODUCED")
elif in_band:
    print("REPRODUCED (order-of-magnitude; finite-N offset, convergence not cleanly shown)")
else:
    print("FAILED")
print(f"ratios measured/formula: {[round(r,2) for r in ratios]}")
print("note: DPV p_c is an asymptotic (large-N) result; finite-N transition sits near it and the")
print("k=2 case should match the exact ER giant-component threshold p_c=1/N as a built-in check.")
