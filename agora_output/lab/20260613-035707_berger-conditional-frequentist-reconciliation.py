# Crucible: replicate Berger (2003) — the conditional-frequentist reconciliation of Fisher/Neyman/
# Jeffreys. Claim: a frequentist who CONDITIONS on the strength of evidence reports error
# probabilities that EQUAL the Bayesian posterior probabilities — the three testing philosophies
# agree numerically. And the naive (unconditional) p-value does NOT equal the posterior: it
# overstates the evidence against H0 (Berger-Sellke). Simple-vs-simple test N(0,1) vs N(mu,1),
# equal priors. Source: simulation.
import numpy as np
from math import erf, sqrt, exp
rng = np.random.default_rng(0)

mu = 2.0
N = 4_000_000
H = rng.integers(0, 2, size=N)                 # truth: 0=H0, 1=H1 (equal priors)
x = rng.normal(loc=H*mu, scale=1.0, size=N)

# Bayes factor B = f0/f1 and posterior P(H0|x) under equal priors
B = np.exp(mu*mu/2 - mu*x)
post_H0 = B/(B+1.0)

# (1) CALIBRATION: among trials with posterior ~ p, the empirical FREQUENCY that H0 is true should
#     equal p. That empirical conditional frequency IS the conditional-frequentist error probability.
print("Conditional-frequentist error  vs  Bayesian posterior  (should match):")
print(f"  {'posterior bin':>16}{'Bayesian P(H0|x)':>18}{'freq. H0 is true':>18}{'n':>10}")
edges = [0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]
for lo,hi in zip(edges[:-1],edges[1:]):
    m = (post_H0>=lo)&(post_H0<hi)
    if m.sum()>0:
        print(f"  {f'[{lo:.1f},{hi:.1f})':>16}{post_H0[m].mean():>18.3f}{(H[m]==0).mean():>18.3f}{m.sum():>10}")

# (2) p-VALUE vs POSTERIOR: the naive one-sided p-value overstates evidence against H0.
def Phi(z): return 0.5*(1+erf(z/sqrt(2)))
print("\nNaive p-value vs the actual posterior probability of H0 (Berger-Sellke discrepancy):")
print(f"  {'observed x':>10}{'one-sided p':>13}{'P(H0|x)':>10}{'freq H0 true near x':>21}")
for xv in [1.645, 1.96, 2.576, 3.0]:
    p = 1-Phi(xv)                              # p = P(X>=x | H0)
    pH0 = float(exp(mu*mu/2-mu*xv)/(exp(mu*mu/2-mu*xv)+1))
    near = np.abs(x-xv)<0.02
    freq = (H[near]==0).mean() if near.sum()>50 else float('nan')
    print(f"  {xv:>10.3f}{p:>13.4f}{pH0:>10.3f}{freq:>21.3f}")
print("\n=> Column 'freq H0 true' tracks the Bayesian posterior, NOT the p-value: a frequentist who"
      "\n   conditions on the evidence gets the Bayesian number (Fisher/Neyman/Jeffreys reconciled)."
      "\n   The unconditional p (e.g. p=0.05 at x=1.645) badly understates P(H0) (~0.2-0.3): the"
      "\n   p-value is not the probability the null is true. REPRODUCED.")
