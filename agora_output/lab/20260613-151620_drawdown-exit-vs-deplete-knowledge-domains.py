
import numpy as np
rng = np.random.default_rng(3)
# Knowledge domains as depletable pools; digging finds a NEW result with prob = remaining/richness
# (exhaustion: marginal yield falls as a domain is mined). Two effort-allocation strategies, same
# domains+seed, fixed dig budget T. Drawdown-exit = leave a domain once its discovery rate falls
# theta below its in-domain peak (a drawdown stop), reallocating effort to a fresh domain.
M, T = 40, 4000
rich = rng.integers(20, 200, M)                 # total discoverable findings per domain

def run(theta):
    rem = rich.copy().astype(float)
    found = 0; di = 0
    visited = [di]
    peak = 0.0; win = []                          # rolling recent yield
    for _ in range(T):
        if di >= M: break
        p = rem[di]/rich[di] if rich[di] else 0
        hit = rng.random() < p
        if hit: found += 1; rem[di] -= 1
        win.append(1 if hit else 0)
        if len(win) > 25: win.pop(0)
        rate = sum(win)/len(win)
        peak = max(peak, rate)
        exhausted = rem[di] <= 0.5
        drawdown_exit = theta is not None and len(win) >= 25 and peak > 0 and rate < (1-theta)*peak
        if exhausted or drawdown_exit:
            di += 1; peak = 0.0; win = []
            if di < M: visited.append(di)
    return found, len(visited)

# baseline: mine to depletion (theta=None)
base, base_dom = run(None)
# sweep drawdown thresholds
rows = []
for theta in [0.4, 0.5, 0.6, 0.7, 0.8]:
    f, dom = run(theta)
    rows.append((theta, f, dom))
best = max(rows, key=lambda r: r[1])
print(f"deplete-to-dry baseline: {base} findings across {base_dom} domains (budget {T} digs)")
print("theta  findings  domains_touched")
for th, f, dom in rows:
    print(f"{th:.1f}    {f:>5}     {dom}")
print(f"BEST drawdown-exit: theta={best[0]:.1f} -> {best[1]} findings ({best[2]} domains)")
print(f"LIFT vs depletion: {100*(best[1]-base)/base:+.1f}%")
print("HYP_SUPPORTED", best[1] > base)
