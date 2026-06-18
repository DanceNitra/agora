
import numpy as np
rng = np.random.default_rng(5)
# Two mechanisms for the approach to a "grand synthesis" (>=3 artifacts unifying), measured by the
# hypothesis's own metric: inter-artifact semantic-distance VARIANCE over the run-up.
# (A) CRITICAL borrow: fluctuations grow near the transition -> noise amplitude rises as t->synthesis.
# (B) CONVERGENCE (the literal meaning of synthesis): artifacts drift toward a shared attractor.
D, n_art, T, trials = 16, 8, 30, 400
def var_traj(mode):
    out = np.zeros(T)
    for _ in range(trials):
        base = rng.standard_normal((n_art, D))
        attractor = rng.standard_normal(D)
        traj = np.zeros(T)
        for t in range(T):
            f = t/(T-1)                       # 0 -> 1 as synthesis approaches
            if mode == 'critical':
                amp = 0.3 + 1.2*f             # noise amplitude grows (critical fluctuations)
                pts = base + amp*rng.standard_normal((n_art, D))
            else:                              # convergence: pull toward the shared attractor
                pts = (1-0.9*f)*base + (0.9*f)*attractor + 0.3*rng.standard_normal((n_art, D))
            pts /= (np.linalg.norm(pts,axis=1,keepdims=True)+1e-9)
            # pairwise cosine-distance variance
            S = pts @ pts.T; iu = np.triu_indices(n_art,1)
            d = 1 - S[iu]
            traj[t] = d.var()
        out += traj
    return out/trials
crit = var_traj('critical'); conv = var_traj('convergence')
def slope(v): return float(np.polyfit(np.arange(len(v)), v, 1)[0])
print("approach to synthesis (t: 0 -> transition)")
print(f"CRITICAL borrow:  var {crit[0]:.4f} -> {crit[-1]:.4f}  slope {slope(crit):+.5f}/step  ({'RISES' if crit[-1]>crit[0] else 'falls'})")
print(f"CONVERGENCE null: var {conv[0]:.4f} -> {conv[-1]:.4f}  slope {slope(conv):+.5f}/step  ({'rises' if conv[-1]>conv[0] else 'FALLS'})")
print(f"The hypothesis predicts RISING variance; convergence (the literal mechanism of synthesis) predicts the OPPOSITE sign.")

