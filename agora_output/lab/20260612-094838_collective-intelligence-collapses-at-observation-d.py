
import numpy as np
rng = np.random.default_rng(23)
def cascade(N,k,w=1,p=0.60,trials=3000):
    lo=np.log(p/(1-p)); acts=np.zeros((trials,N)); plus=np.zeros(trials)
    for i in range(N):
        if i>0 and k>0:
            m=min(k,i); idx=rng.integers(0,i,size=(trials,m))
            pub=np.take_along_axis(acts,idx,axis=1).sum(axis=1)*lo
        else: pub=0.0
        sig=np.where(rng.random(trials)<p,1.0,-1.0)
        post=pub+sig*(w*lo)
        a=np.where(post>0,1.0,np.where(post<0,-1.0,np.where(rng.random(trials)<0.5,1.0,-1.0)))
        acts[:,i]=a; plus+=(a==1)
    return float(np.mean(plus>N/2))
print("A) Collective accuracy vs observation degree k (own-signal weight w=1, p=0.60)")
print(f"{'k':>3} | {'N=101':>6} {'N=501':>6} {'N=2001':>6}")
for k in (0,1,2,3,5,15,100):
    print(f"{k:>3} | "+" ".join(f"{cascade(N,min(k,N)):6.3f}" for N in (101,501,2001)))
print()
print("B) Critical degree k_c shifts as k_c = w+1 (N=501): cascade begins once observed actions > own-signal trust")
print(f"{'k':>3} | {'w=1':>5} {'w=2':>5} {'w=4':>5}")
for k in (0,1,2,3,4,5,6):
    print(f"{k:>3} | "+" ".join(f"{cascade(501,k,w):5.3f}" for w in (1,2,4)))
