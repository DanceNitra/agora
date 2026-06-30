"""
Audit #8 full-panel severe-test: quantify (a) the drawdown stop vs the MVT-OPTIMAL (oracle, full-info)
rule the post calls 'textbook-optimal', and (b) the multi-seed distribution of the lift (the published
+239% is a single seed). Same depleting-veins model as the original lab.

Three policies, same domains+seed, fixed budget T:
  - deplete-to-dry baseline (leave only when a vein is exhausted)
  - drawdown stop (model-free: leave when recent 25-window yield falls theta below its in-vein peak)
  - MVT-oracle (full information: KNOWS the true marginal yield p=rem/rich, leaves when p < gamma;
    gamma swept to the optimum -> this is the exact-assessment upper bound the drawdown proxy approximates)
"""
import numpy as np

M, T, WIN = 40, 4000, 25
THETAS = [0.4, 0.5, 0.6, 0.7, 0.8]
GAMMAS = [round(g, 3) for g in np.arange(0.02, 0.41, 0.02)]


def domains(seed):
    return np.random.default_rng(seed).integers(20, 200, M)


def run_drawdown(rich, seed, theta):
    rng = np.random.default_rng(seed * 100 + 1)
    rem = rich.copy().astype(float); found = 0; di = 0; peak = 0.0; win = []
    for _ in range(T):
        if di >= M: break
        p = rem[di] / rich[di] if rich[di] else 0
        hit = rng.random() < p
        if hit: found += 1; rem[di] -= 1
        win.append(1 if hit else 0)
        if len(win) > WIN: win.pop(0)
        rate = sum(win) / len(win); peak = max(peak, rate)
        exhausted = rem[di] <= 0.5
        ddx = theta is not None and len(win) >= WIN and peak > 0 and rate < (1 - theta) * peak
        if exhausted or ddx:
            di += 1; peak = 0.0; win = []
    return found


def run_mvt_oracle(rich, seed, gamma):
    # full information: leaves a vein when its TRUE marginal yield p=rem/rich drops below gamma
    rng = np.random.default_rng(seed * 100 + 1)
    rem = rich.copy().astype(float); found = 0; di = 0
    for _ in range(T):
        if di >= M: break
        p = rem[di] / rich[di] if rich[di] else 0
        if p < gamma:                      # exact-assessment leave rule
            di += 1; continue
        if rng.random() < p:
            found += 1; rem[di] -= 1
        if rem[di] <= 0.5:
            di += 1
    return found


SEEDS = list(range(40))
base_l, dd_l, mvt_l, gap_l = [], [], [], []
for s in SEEDS:
    rich = domains(s)
    base = run_drawdown(rich, s, None)
    dd = max(run_drawdown(rich, s, th) for th in THETAS)
    mvt = max(run_mvt_oracle(rich, s, g) for g in GAMMAS)
    base_l.append(base); dd_l.append(dd); mvt_l.append(mvt)
    gap_l.append(100 * (mvt - dd) / dd if dd else 0)

base_a, dd_a, mvt_a = map(np.array, (base_l, dd_l, mvt_l))
lift_dd = 100 * (dd_a - base_a) / base_a          # drawdown vs deplete-to-dry (the published +239%)
lift_mvt = 100 * (mvt_a - base_a) / base_a         # MVT-oracle vs deplete-to-dry
gap = np.array(gap_l)                              # how far drawdown is BELOW the oracle

def stat(x): return f"median {np.median(x):.0f}%  mean {np.mean(x):.0f}%  range [{x.min():.0f}%, {x.max():.0f}%]"

print(f"=== {len(SEEDS)} seeds, M={M} veins, budget T={T} ===")
print(f"drawdown vs deplete-to-dry (published as +239%):   {stat(lift_dd)}")
print(f"MVT-oracle vs deplete-to-dry:                       {stat(lift_mvt)}")
print(f"--- THE MISSING NUMBER: drawdown's SHORTFALL vs the MVT-oracle (exact-assessment) ---")
print(f"oracle beats drawdown by:                           {stat(gap)}")
print(f"  i.e. the cheap model-free proxy reaches ~{100 - np.median(gap):.0f}% of the full-information optimum (median)")
print(f"single-seed (seed=3) drawdown lift = {lift_dd[SEEDS.index(3)] if 3 in SEEDS else 'NA'}  (the published number's seed)")
