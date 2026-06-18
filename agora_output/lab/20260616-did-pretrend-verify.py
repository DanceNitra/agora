# Verify the DiD assumption-violation note (lab 2b7e05, rotated out of the store)
# before citing its numbers in a public press piece.
# Model per the source note: 1 treated + 20 controls, 6 pre / 4 post, true effect 2.0, seed 42.
import numpy as np

rng = np.random.default_rng(42)
NCTRL, TPRE, TPOST = 20, 6, 4
T = TPRE + TPOST
TRUE = 2.0
SIGMA = 1.0
NDRAWS = 2000

def panel():
    unitFE = rng.normal(0, 1, NCTRL + 1)
    timeFE = rng.normal(0, 1, T)
    Y = unitFE[:, None] + timeFE[None, :] + rng.normal(0, SIGMA, (NCTRL + 1, T))
    Y[0, TPRE:] += TRUE  # treatment effect on treated unit, post periods
    return Y

def did_and_pretrend(Y, normal_cutoff=False):
    t_pre, t_post = Y[0, :TPRE].mean(), Y[0, TPRE:].mean()
    c_pre, c_post = Y[1:, :TPRE].mean(), Y[1:, TPRE:].mean()
    did = (t_post - t_pre) - (c_post - c_pre)
    # pre-trend test: regress treated-minus-control-mean gap on linear time, pre only
    gap = Y[0, :TPRE] - Y[1:, :TPRE].mean(axis=0)
    x = np.arange(TPRE); xm = x.mean(); sxx = ((x - xm) ** 2).sum()
    slope = ((x - xm) * (gap - gap.mean())).sum() / sxx
    resid = gap - (gap.mean() + slope * (x - xm))
    s2 = (resid ** 2).sum() / (TPRE - 2)
    se = np.sqrt(s2 / sxx)
    tstat = slope / se
    crit = 1.96 if normal_cutoff else 2.776  # 2.776 = t_4 at 5% two-sided
    return did, abs(tstat) > crit

def run(violation, mag):
    biases, det_t, det_z = [], 0, 0
    for _ in range(NDRAWS):
        Y = panel()
        if violation == "trend":
            Y[0, :] += mag * np.arange(T)
        elif violation == "anticipation":
            Y[0, TPRE - 1] += mag
        elif violation == "composition":
            Y[0, TPRE // 2:] += mag
        did, hit_t = did_and_pretrend(Y)
        _, hit_z = did_and_pretrend(Y, normal_cutoff=True)
        biases.append(did - TRUE); det_t += hit_t; det_z += hit_z
    return np.mean(biases), det_t / NDRAWS, det_z / NDRAWS

print(f"DiD verify | {NCTRL} controls, {TPRE} pre / {TPOST} post, true={TRUE}, sigma={SIGMA}, {NDRAWS} draws")
print(f"{'violation':<22}{'bias':>8}{'%true':>8}{'det@t_4':>9}{'det@z':>8}")
conds = [("trend", 0.3), ("trend", 0.6), ("anticipation", 1.0), ("anticipation", 2.0),
         ("composition", 1.0), ("composition", 2.0), ("trend", 0.0)]
for v, m in conds:
    b, dt, dz = run(v, m)
    print(f"{v+' '+str(m):<22}{b:>+8.3f}{100*b/TRUE:>7.0f}%{100*dt:>8.0f}%{100*dz:>7.0f}%")
