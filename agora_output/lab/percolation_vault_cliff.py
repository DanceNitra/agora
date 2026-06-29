"""Does a note-vault's connectivity collapse ABRUPTLY (percolation cliff) or gracefully as links are lost?
Test the claim behind 'your-second-brain-is-dying-of-maintenance'. Model the vault as a random graph at
the measured params (mean degree ~13), then remove a fraction q of edges (bond percolation) and measure
the giant-component fraction. A cliff = abrupt drop near a critical q_c; graceful = linear-ish.
Pure stdlib. MIT."""
import random
random.seed(7)

def giant_frac(n, adj):
    seen=[False]*n; best=0
    for s in range(n):
        if seen[s]: continue
        stack=[s]; seen[s]=True; sz=0
        while stack:
            u=stack.pop(); sz+=1
            for v in adj[u]:
                if not seen[v]: seen[v]=True; stack.append(v)
        best=max(best,sz)
    return best/n

def er_graph(n, mean_deg):
    m=int(n*mean_deg/2); edges=set()
    while len(edges)<m:
        a=random.randrange(n); b=random.randrange(n)
        if a!=b: edges.add((min(a,b),max(a,b)))
    return list(edges)

n=2000; mean_deg=13.0
edges=er_graph(n, mean_deg)
print(f"model: ER graph n={n}, mean degree={mean_deg} (vault: ~13 links/note)")
print("Molloy-Reed / ER: giant component vanishes around mean degree 1.0 (q_c = 1 - 1/<k>)")
print(f"predicted edge-removal critical point q_c = 1 - 1/{mean_deg:.0f} = {1-1/mean_deg:.3f}\n")
print(" frac_links_removed   remaining_mean_deg   giant_component_frac")
prev=None
for q in [0.0,0.2,0.4,0.6,0.8,0.85,0.90,0.92,0.94,0.96,0.98,1.0]:
    adj=[[] for _ in range(n)]
    for (a,b) in edges:
        if random.random()>q:
            adj[a].append(b); adj[b].append(a)
    gf=giant_frac(n, adj)
    drop="" if prev is None else f"   (d={gf-prev:+.3f})"
    print(f"   {q:5.2f}              {mean_deg*(1-q):6.2f}              {gf:.3f}{drop}")
    prev=gf
print("\nINTERPRETATION: the giant component stays HIGH until remaining mean degree approaches ~1")
print("(q ~ 0.92 here), then drops abruptly -> a percolation CLIFF exists. BUT a vault at 13 links/note")
print("sits far ABOVE it: you must lose ~90% of links to fall off. So the cliff is real (theory: Molloy-Reed)")
print("yet a well-linked vault is far from it; the actionable risk is DRIFT of mean degree toward the threshold.")
