
import numpy as np
from math import comb
rng = np.random.default_rng(11)
def cascade(N,p,trials=20000):
    lo=np.log(p/(1-p)); ok=0
    for _ in range(trials):
        pub=0.0; plus=0
        for i in range(N):
            sig=+1 if rng.random()<p else -1
            post=pub+sig*lo
            a=1 if post>0 else (0 if post<0 else (1 if rng.random()<0.5 else 0))
            plus+=a; pub+=lo if a==1 else -lo
        ok+=(plus>N/2)
    return ok/trials
def condorcet(N,p):
    s=sum(comb(N,k)*p**k*(1-p)**(N-k) for k in range(N//2+1,N+1))
    if N%2==0: s+=0.5*comb(N,N//2)*p**(N//2)*(1-p)**(N//2)
    return s
def n_eff(acc,p):                      # equivalent independent-voter count for a cascade's accuracy
    for n in range(1,200,2):
        if condorcet(n,p)>=acc: return n
    return ">199"
print("Wisdom of crowds vs information cascade — does collective accuracy grow with N?")
print(f"{'N':>5} | {'cascade p=.6':>12} | {'independent p=.6':>16} | {'cascade N_eff':>13}")
for N in (1,3,11,51,201,1001):
    c=cascade(N,0.60); ind=condorcet(N,0.60)
    print(f"{N:>5} | {c:>12.3f} | {ind:>16.3f} | {n_eff(c,0.60):>13}")
print()
print("Same at marginal competence p=0.55:")
for N in (11,201,1001):
    c=cascade(N,0.55)
    print(f"  N={N:<5} cascade={c:.3f}  independent={condorcet(N,0.55):.3f}  cascade N_eff={n_eff(c,0.55)}")
