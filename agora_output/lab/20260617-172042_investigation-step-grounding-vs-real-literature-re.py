
import numpy as np
K=6; _q=np.array([8.0]+[1.0]*(K-1)); Q=_q/_q.sum(); CH=1/K; QB=Q[0]
tau=lambda pb: float(np.clip((pb-CH)/(QB-CH),0,1))
def run(phi,alpha=2.0,T=250,trials=200,seed=0):
    rng=np.random.default_rng(seed); p=rng.dirichlet(np.ones(K),size=trials)
    for _ in range(T):
        r=np.power(p,alpha); r/=r.sum(axis=1,keepdims=True)
        p=phi*Q+(1-phi)*r; p/=p.sum(axis=1,keepdims=True)
    return float(p[:,0].mean())
rep=tau(run(0.02)); acc=tau(run(0.30))
print(f"REPLACE phi=0.02 (Shumailov-like, synthetic replaces): tau={rep:.2f} -> collapse/lock")
print(f"ACCUMULATE phi=0.30 (real data accumulates, Gerstgrasser-like): tau={acc:.2f} -> truth preserved")
print("MATCHES_LIT" if (rep<0.5 and acc>0.5) else "MISMATCH")
