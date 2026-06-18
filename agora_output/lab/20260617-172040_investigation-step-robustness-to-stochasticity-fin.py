
import numpy as np
K=6; _q=np.array([8.0]+[1.0]*(K-1)); Q=_q/_q.sum(); CH=1/K; QB=Q[0]
tau=lambda pb: float(np.clip((pb-CH)/(QB-CH),0,1))
def run(phi,alpha,N=200,T=180,trials=120,seed=0):
    rng=np.random.default_rng(seed); p=rng.dirichlet(np.ones(K),size=trials)
    for _ in range(T):
        r=np.power(p,alpha); r/=r.sum(axis=1,keepdims=True)
        m=phi*Q+(1-phi)*r; m/=m.sum(axis=1,keepdims=True)
        p=np.array([rng.multinomial(N,mm)/N for mm in m])      # FINITE-SAMPLE noise
        p=np.clip(p,1e-9,None); p/=p.sum(axis=1,keepdims=True)
    return float(p[:,0].mean())
phic=lambda a: next((float(x) for x in np.linspace(0,0.6,31) if tau(run(float(x),a))>=0.5),None)
res={a:phic(a) for a in [1.0,2.0,3.0]}
print("finite-N phi_c vs alpha:",res)
ok=res[1.0] is not None and res[3.0] is not None and res[3.0]>res[1.0]
print("ROBUST_NOISE" if ok else "NOT_ROBUST")
