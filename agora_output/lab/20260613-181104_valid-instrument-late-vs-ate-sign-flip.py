
import numpy as np
rng = np.random.default_rng(4)
# A PERFECTLY VALID instrument (randomly assigned Z, affects D, excludable) — yet IV estimates the
# compliers' effect (LATE), not the population ATE. With effect heterogeneity correlated to
# compliance type, LATE can differ in SIGN from the ATE. So "valid instrument" != "the effect you want".
N = 200000
# types: 40% compliers (D=Z), 35% always-takers (D=1), 25% never-takers (D=0)
u = rng.random(N)
typ = np.where(u<0.40,'C', np.where(u<0.75,'A','N'))
Z = rng.integers(0,2,N)
D = np.where(typ=='C', Z, np.where(typ=='A',1,0))
# heterogeneous effects by type: compliers HELPED (-1 cost? say +? ) — make signs opposite
tau = np.where(typ=='C', -1.0, np.where(typ=='A', +3.0, +2.0))   # compliers: -1 ; takers: positive
base = rng.standard_normal(N)
Y = base + tau*D + rng.standard_normal(N)*0.5
# Wald / 2SLS with binary instrument
num = Y[Z==1].mean() - Y[Z==0].mean()
den = D[Z==1].mean() - D[Z==0].mean()
late_hat = num/den
ate = tau.mean()                       # population average treatment effect
late_true = tau[typ=='C'].mean()       # compliers' effect
naive = Y[D==1].mean() - Y[D==0].mean()  # naive OLS (confounded)
print(f"instrument strength (first stage E[D|Z=1]-E[D|Z=0]) = {den:.3f}  (STRONG, valid)")
print(f"IV/Wald estimate        = {late_hat:+.3f}")
print(f"true LATE (compliers)   = {late_true:+.3f}   <- what IV identifies")
print(f"population ATE          = {ate:+.3f}   <- what a policymaker usually wants")
print(f"naive OLS (confounded)  = {naive:+.3f}")
print(f"SIGN FLIP: IV says {('negative' if late_hat<0 else 'positive')}, ATE is {('positive' if ate>0 else 'negative')} -> opposite-signed: {late_hat*ate<0}")
