
import numpy as np
rng = np.random.default_rng(7)
# Staggered-adoption DiD under timing-correlated trends. Units adopt treatment at different times;
# we make adoption time correlate (strength rho) with each unit's OWN linear pre-trend slope.
# True treatment effect tau=2. Estimate via two-way fixed-effects (TWFE) and measure the bias as a
# function of rho. Claim: bias grows monotonically with the timing<->trend correlation.
N, Tt, tau = 300, 12, 2.0
def twfe_bias(rho, trials=120):
    biases=[]
    for _ in range(trials):
        slope = rng.standard_normal(N)                      # unit-specific linear trend slope
        # adoption period correlated with slope: high-slope units adopt earlier
        noise = rng.standard_normal(N)
        score = rho*slope + np.sqrt(max(1e-9,1-rho*rho))*noise
        adopt = 3 + (np.argsort(np.argsort(score))/N*6).astype(int)   # adopt in periods 3..9
        unit_fe = rng.standard_normal(N)*0.5
        rows_y=[]; rows_d=[]; rows_u=[]; rows_t=[]
        for i in range(N):
            for t in range(Tt):
                trend = slope[i]*t*0.1
                d = 1.0 if t>=adopt[i] else 0.0
                y = unit_fe[i] + 0.3*t + trend + tau*d + rng.standard_normal()*0.5
                rows_y.append(y); rows_d.append(d); rows_u.append(i); rows_t.append(t)
        y=np.array(rows_y); d=np.array(rows_d); u=np.array(rows_u); t=np.array(rows_t)
        # TWFE: demean by unit and by time (within transform), regress y~d
        def demean(v, g):
            out=v.copy().astype(float)
            for k in np.unique(g):
                m=g==k; out[m]-=out[m].mean()
            return out
        yd=demean(demean(y,u),t); dd=demean(demean(d,u),t)
        bhat = (dd*yd).sum()/(dd*dd).sum()
        biases.append(bhat-tau)
    return float(np.mean(biases))
print("staggered DiD (TWFE), true tau=2.0 — bias vs corr(adoption timing, unit trend):")
print(" rho    mean_bias")
for rho in [0.0, 0.3, 0.6, 0.9]:
    print(f"{rho:.1f}    {twfe_bias(rho):+.3f}")
