import random, statistics as st
random.seed(42)

# Claim (Cachero Sanchez 2026): BA network N=2000, m=2 — removing the top 10% of nodes by degree
# raises the bond-percolation threshold from p_c=0.174 to 0.776.
# Smallest model of the mechanism: Molloy-Reed threshold p_c = <k>/(<k^2> - <k>) on the empirical
# degree sequence (intact vs after targeted hub removal), cross-checked by a direct bond-percolation
# sweep with union-find. Source: simulation.

def ba_graph(N, m):
    # Barabasi-Albert preferential attachment
    adj = {i: set() for i in range(N)}
    targets = list(range(m))
    repeated = []                       # degree-proportional pool
    for src in range(m, N):
        chosen = set()
        while len(chosen) < m:
            chosen.add(random.choice(repeated) if repeated else random.randrange(src))
        for t in chosen:
            adj[src].add(t); adj[t].add(src)
            repeated.append(t); repeated.append(src)
    return adj

def moments(adj, alive):
    degs = [sum(1 for nb in adj[v] if nb in alive) for v in alive]
    k1 = st.mean(degs); k2 = st.mean(d*d for d in degs)
    return k1, k2

def molloy_reed_pc(k1, k2):
    return k1 / (k2 - k1) if (k2 - k1) > 0 else float('inf')

class UF:
    def __init__(s, n): s.p=list(range(n)); s.sz=[1]*n
    def f(s,x):
        while s.p[x]!=x: s.p[x]=s.p[s.p[x]]; x=s.p[x]
        return x
    def u(s,a,b):
        a,b=s.f(a),s.f(b)
        if a==b: return
        if s.sz[a]<s.sz[b]: a,b=b,a
        s.p[b]=a; s.sz[a]+=s.sz[b]; 

def giant_frac(adj, alive, p, trials=3):
    alive_l=list(alive); idx={v:i for i,v in enumerate(alive_l)}; n=len(alive_l)
    edges=[(idx[u],idx[v]) for u in alive for v in adj[u] if v in alive and u<v]
    best=[]
    for _ in range(trials):
        uf=UF(n)
        for a,b in edges:
            if random.random()<p: uf.u(a,b)
        best.append(max(uf.sz)/n)
    return st.mean(best)

def sim_pc(adj, alive):
    # threshold = smallest p where giant component exceeds 50% of the (sub)network
    for p in [i/100 for i in range(1,100)]:
        if giant_frac(adj, alive, p) > 0.5:
            return p
    return None

N, m = 2000, 2
adj = ba_graph(N, m)
alive = set(range(N))
k1, k2 = moments(adj, alive)
pc_intact = molloy_reed_pc(k1, k2)

# targeted hub removal: drop top 10% by degree
deg_intact = sorted(alive, key=lambda v: len(adj[v]), reverse=True)
n_remove = int(0.10 * N)
removed = set(deg_intact[:n_remove])
alive2 = alive - removed
k1b, k2b = moments(adj, alive2)
pc_removed = molloy_reed_pc(k1b, k2b)

print(f"N={N} m={m}")
print(f"INTACT:    <k>={k1:.2f} <k^2>={k2:.1f}  Molloy-Reed p_c={pc_intact:.3f}   claim 0.174")
print(f"HUBS -10%: <k>={k1b:.2f} <k^2>={k2b:.1f}  Molloy-Reed p_c={pc_removed:.3f}   claim 0.776")
print("--- direct bond-percolation sweep (giant>50%) ---")
print(f"INTACT sim p_c    = {sim_pc(adj, alive)}")
print(f"HUB-REMOVED sim p_c = {sim_pc(adj, alive2)}")
