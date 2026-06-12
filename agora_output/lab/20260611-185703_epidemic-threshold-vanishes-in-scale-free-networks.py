import random, statistics as st
random.seed(42)

# Claim (Pastor-Satorras & Vespignani 2001): in scale-free networks the epidemic threshold VANISHES
# as N grows. Heterogeneous mean-field: SIS threshold lambda_c = <k>/<k^2>. For a power-law degree
# distribution <k^2> diverges with N, so lambda_c -> 0 (no safe transmission rate). For a homogeneous
# (Erdos-Renyi) network <k^2> is finite, so lambda_c stays put. Smallest model: build BA vs ER at the
# same mean degree, measure <k>, <k^2>, lambda_c across sizes. Source: simulation.

def ba_degrees(N, m):
    deg=[0]*N; repeated=[]
    for i in range(m): deg[i]=m-1 if m>1 else 0
    for src in range(m,N):
        chosen=set()
        while len(chosen)<m:
            chosen.add(random.choice(repeated) if repeated else random.randrange(src))
        for t in chosen:
            deg[src]+=1; deg[t]+=1; repeated += [t,src]
    return deg

def er_degrees(N, m):
    # Erdos-Renyi with mean degree ~2m (match BA's <k>=2m); Poisson-like degrees
    p = (2*m)/(N-1)
    deg=[0]*N
    # sample expected degree via binomial approx: each node ~ Binomial(N-1,p)
    for i in range(N):
        d=0
        # cheap: draw from normal approx of Binomial then clamp
        mu=(N-1)*p; sd=(mu*(1-p))**0.5
        d=max(0,int(round(random.gauss(mu,sd))))
        deg[i]=d
    return deg

def lam_c(deg):
    k1=st.mean(deg); k2=st.mean(d*d for d in deg)
    return k1/k2 if k2 else 0, k1, k2

print("SIS threshold lambda_c = <k>/<k^2>, mean degree ~4 (m=2)\n")
print(f"{'N':>7} {'BA <k^2>':>9} {'BA lam_c':>9}   {'ER <k^2>':>9} {'ER lam_c':>9}")
for N in (500, 2000, 8000, 20000):
    lb,k1b,k2b = lam_c(ba_degrees(N,2))
    le,k1e,k2e = lam_c(er_degrees(N,2))
    print(f"{N:7d} {k2b:9.1f} {lb:9.4f}   {k2e:9.1f} {le:9.4f}")
print("\nBA (scale-free): <k^2> grows with N -> lambda_c shrinks toward 0 (threshold VANISHES).")
print("ER (homogeneous): <k^2> ~ const -> lambda_c stays put. Reproduces Pastor-Satorras/Vespignani.")
