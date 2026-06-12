
import numpy as np
rng = np.random.default_rng(5)
dt=0.02; N=400000; a=1.0; sp=0.0; tau_u=2.0; sig_u=1.0; sig_e=1.0
def sim(Kp):
    T=0.0; u=0.0
    H=np.empty(N); Tc=np.empty(N); E=np.empty(N); dT=np.empty(N)
    for k in range(N):
        e=rng.normal(0,sig_e)
        u += dt*(-u/tau_u) + np.sqrt(dt)*sig_u*rng.normal()
        Hk = -Kp*(T-sp) + e
        dTk = dt*(a*Hk + u)
        H[k]=Hk; Tc[k]=T; E[k]=e; dT[k]=dTk
        T += dTk
    H=H[2000:]; Tc=Tc[2000:]; E=E[2000:]; dT=dT[2000:]
    corr = np.corrcoef(H,Tc)[0,1]
    ols  = np.cov(H,Tc)[0,1]/np.var(H)
    a_iv = np.cov(E,dT)[0,1]/(dt*np.cov(E,H)[0,1])
    return corr, ols, a_iv
print(f"true causal a = {a} (H raises T)")
print(f"{'Kp':>6} | {'corr(H,T)':>10} | {'OLS T~H':>8} | {'IV a_hat':>9}")
for Kp in (0.2, 1.0, 5.0, 20.0, 80.0):
    c,o,iv = sim(Kp); print(f"{Kp:>6.1f} | {c:>10.3f} | {o:>8.3f} | {iv:>9.3f}")
