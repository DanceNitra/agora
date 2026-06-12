
import numpy as np
rng=np.random.default_rng(31)
def acc(N, alpha, p=0.60, trials=4000):
    lo=np.log(p/(1-p)); ok=0
    for _ in range(trials):
        pub=0.0; plus=0
        for i in range(N):
            sig=+1 if rng.random()<p else -1
            if rng.random()<alpha:
                a=1 if sig>0 else 0
            else:
                post=pub+sig*lo
                a=1 if post>0 else (0 if post<0 else (1 if rng.random()<0.5 else 0))
            plus+=a; pub+=lo if a==1 else -lo
        ok+=(plus>N/2)
    return ok/trials
print("Collective accuracy vs forced-independence fraction alpha, p=0.60 (alpha=0 = pure cascade)")
print(f"{'alpha':>6} | {'N=101':>6} {'N=1001':>6}")
for al in (0.0,0.1,0.3,0.5,0.7,0.8,0.9,0.95,1.0):
    print(f"{al:>6.2f} | "+" ".join(f"{acc(N,al):6.3f}" for N in (101,1001)))
