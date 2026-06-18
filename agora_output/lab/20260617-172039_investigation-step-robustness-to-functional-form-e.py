
import numpy as np
K=6; _q=np.array([8.0]+[1.0]*(K-1)); Q=_q/_q.sum(); CH=1/K; QB=Q[0]
tau=lambda pb: float(np.clip((pb-CH)/(QB-CH),0,1))
def run(phi,beta,T=250,trials=200,seed=0):
    rng=np.random.default_rng(seed); p=rng.dirichlet(np.ones(K),size=trials)
    for _ in range(T):
        r=np.exp(beta*p); r/=r.sum(axis=1,keepdims=True)      # EXPONENTIAL tilt (different form)
        p=phi*Q+(1-phi)*r; p/=p.sum(axis=1,keepdims=True)
    return float(p[:,0].mean())
phic=lambda b: next((float(x) for x in np.linspace(0,0.6,61) if tau(run(float(x),b))>=0.5),None)
res={b:phic(b) for b in [2,5,10,20]}
print("exp-tilt phi_c vs beta:",res)
ok=all(res[b] is not None for b in [5,10,20]) and res[20]>res[5]
print("ROBUST_FORM" if ok else "NOT_ROBUST")
