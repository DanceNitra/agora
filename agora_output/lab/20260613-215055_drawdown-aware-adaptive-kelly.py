
import numpy as np
rng = np.random.default_rng(2)
# Repeated favorable bet: win +b w.p. p, lose -1 w.p. (1-p). Edge>0. Stake fraction f of wealth.
# Compare full Kelly, half Kelly, and a DRAWDOWN-AWARE adaptive Kelly that cuts the fraction as
# wealth falls toward a stop (the team's "adjust f by real-time stop-loss proximity" idea).
p, b = 0.55, 1.0
fstar = (p*b - (1-p))/b                      # full-Kelly fraction
T, paths = 250, 4000
def run(mode):
    logterm=[]; maxdd=[]; ruin=0
    for _ in range(paths):
        w=1.0; peak=1.0; dd=0.0; hit=False
        for _t in range(T):
            if mode=='full': f=fstar
            elif mode=='half': f=0.5*fstar
            else:                                # adaptive: scale f down by current drawdown
                f=fstar*max(0.15, 1.0 - dd*1.5)  # deeper drawdown -> smaller fraction
            x = b if rng.random()<p else -1.0
            w *= (1 + f*x)
            if w<=0.02: hit=True; w=0.02; break
            peak=max(peak,w); dd=1-w/peak; maxdd.append(dd) if _t==T-1 else None
        logterm.append(np.log(max(w,1e-9))); 
        if hit: ruin+=1
        maxdd.append(1-w/peak)
    return np.median(logterm), np.percentile(maxdd,95), ruin/paths
print(f"full-Kelly f*={fstar:.2f}, p={p}, edge per bet={(p*b-(1-p)):.2f}")
print(" strategy     median_log_growth   95p_max_drawdown   ruin_rate")
for m in ['full','half','adaptive']:
    g,dd,r=run(m)
    print(f" {m:<10}   {g:+.3f}            {dd:.0%}            {r:.1%}")
