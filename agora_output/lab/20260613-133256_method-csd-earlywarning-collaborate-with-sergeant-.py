
import numpy as np
rng = np.random.default_rng(7)
substrate, sigma = "bifurcation", 0.1
def ac1(x):
    x = x - x.mean()
    return 0.0 if np.allclose(x, 0) else float(np.corrcoef(x[:-1], x[1:])[0, 1])
if substrate == "bifurcation":
    vs, asn = [], []
    for r in [-1.0, -0.5, -0.25, -0.12, -0.06, -0.03]:
        x = 0.0; xs = np.empty(120000); sdt = sigma*0.1
        noise = rng.standard_normal(120000)
        for t in range(120000):
            x += (-(x**3) + r*x)*0.01 + sdt*noise[t]; xs[t] = x
        seg = xs[60000:]; vs.append(seg.var()); asn.append(ac1(seg[::20]))
    blow = vs[-1]/vs[0]
    print(f"MEASURED: variance x{blow:.1f} ; AC1 {asn[0]:.3f}->{asn[-1]:.3f} approaching the critical point")
    print(f"VERDICT: {'CSD PRESENT - precursor forecasting is justified' if blow>3 and asn[-1]>asn[0] else 'NO CSD'}")
else:
    mu = 0.05; curves = []
    for _ in range(40):
        x = mu + rng.standard_normal(20000); S = np.cumsum(x)
        z = S/np.sqrt(np.arange(1, 20001)); hit = np.argmax((z >= 5.0) & (np.arange(20000) > 1000))
        nstar = hit if hit > 0 else 20000
        incr = np.diff(S[:nstar]); w = max(50, nstar//20)
        curves.append([np.var(incr[max(0,int(f*nstar))-w:int(f*nstar)]) for f in np.linspace(0.5, 0.98, 8)])
    m = np.mean(curves, axis=0)
    print(f"MEASURED: order-parameter variance ratio last/first = {m[-1]/m[0]:.2f} on the run-up to the threshold")
    print(f"VERDICT: {'NO CSD - level-crossing thresholds are NOT forecastable from precursors' if m[-1]/m[0]<1.5 else 'CSD-like rise found'}")
