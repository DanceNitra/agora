
import numpy as np
rng=np.random.default_rng(9)
T=252; PATHS=200000
def geo(mu,sig):
    r=rng.normal(mu,sig,size=(PATHS,T))
    mult=np.prod(1+r,axis=1)
    return np.median(mult), np.mean(np.log(np.maximum(mult,1e-9))), np.mean(np.sum(r,axis=1))
print("Panel A: fixed arithmetic mean mu=0.0004/day (~10.1%/yr), vary daily vol")
print(f"{'sigma/day':>9} | {'E[logW] geo':>11} | {'mean sum r':>10} | {'-sig^2/2*T':>11}")
for s in (0.004,0.008,0.012,0.020):
    w,g,a=geo(0.0004,s)
    print(f"{s:>9.3f} | {g:>11.4f} | {a:>10.4f} | {-s*s/2*T:>11.4f}")
print()
mw,mg,ma=geo(0.0004,0.008)
print(f"Panel B: RISK-MANAGER mu=.0004 sig=.008 -> geo growth {mg:.4f}")
print("vs RETURN-CHASER mu=.0006 (50% higher arith mean), rising vol:")
print(f"{'chaser sig':>10} | {'arith sum':>9} | {'geo growth':>10} | {'verdict':>7}")
for s in (0.012,0.020,0.026,0.030):
    w,g,a=geo(0.0006,s)
    print(f"{s:>10.3f} | {a:>9.4f} | {g:>10.4f} | {('WINS' if g>mg else 'LOSES'):>7}")
