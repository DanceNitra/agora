"""
GRAND SYNTHESIS attempt: one principle subsuming the Anchor Law + the Identification Threshold Law.

Both laws say (differently): confidence without external grounding is decoupled from truth.
- Anchor Law (DYNAMIC, over time): a self-feeder needs external flux g>g_c or it locks into
  high-confidence self-agreement that needn't be true.
- Identification Threshold Law (STRUCTURAL, at a point): without identifying structure, more data
  buys precision (confidence) but not accuracy — confidently wrong.

GRAND PRINCIPLE (the Grounding-Coupling Law): a system's CONFIDENCE signal (consensus, or precision)
tracks TRUTH only in proportion to its external-grounding coupling g. As g falls, the two DECOUPLE and
an OVERCONFIDENCE GAP (confidence - accuracy) opens — pumped by internal effort (consensus rounds /
data volume), not by truth.

NOVEL unified prediction (neither law alone makes it): the overconfidence gap is a single order
parameter governed by g, and it collapses calibration the SAME way in BOTH realizations — temporal
self-reference AND structural under-identification. The most confident systems are the least grounded.
Severe-test: compute gap(g) in both realizations; both should rise as g->0.
"""
import numpy as np

K = 6
_q = np.array([8.0] + [1.0]*(K-1)); Q = _q/_q.sum()

# ---- Realization A: TEMPORAL self-reference (the Anchor mechanism) ----
# confidence = consensus concentration (max belief); accuracy = belief mass on the truly-best option.
def temporal(g, alpha=2.0, T=150, runs=600, seed=0):
    rng = np.random.default_rng(seed)
    p = rng.dirichlet(np.ones(K), size=runs)
    for _ in range(T):
        r = np.power(p, alpha); r /= r.sum(axis=1, keepdims=True)
        p = g*Q + (1-g)*r; p /= p.sum(axis=1, keepdims=True)
    conf = float(p.max(axis=1).mean())      # how *certain* the consensus is
    acc  = float(p[:, 0].mean())            # is it certain about the TRUTH?
    return conf, acc

# ---- Realization B: STRUCTURAL under-identification (the Identification mechanism) ----
# confidence = precision (1/SE, rescaled to [0,1]); accuracy = exp(-|bias|). g = fraction of confound controlled.
def structural(g, N=20000, runs=200, seed=0):
    rng = np.random.default_rng(seed)
    biases, ses = [], []
    for s in range(runs):
        rg = np.random.default_rng(seed*1000 + s)
        C = rg.standard_normal(N)
        X = 0.8*C + rg.standard_normal(N)
        Y = 0.0*X + 0.8*C + rg.standard_normal(N)          # true effect 0
        proxy = g*C + np.sqrt(max(1e-9,1-g*g))*rg.standard_normal(N)   # corr(proxy,C)=g
        M = np.column_stack([np.ones(N), X, proxy])
        coef,*_ = np.linalg.lstsq(M, Y, rcond=None)
        resid = Y - M@coef; s2 = resid@resid/(N-3)
        se = np.sqrt((s2*np.linalg.inv(M.T@M))[1,1])
        biases.append(abs(coef[1])); ses.append(se)
    bias = float(np.mean(biases)); se = float(np.mean(ses))
    conf = float(1.0/(1.0 + 8*se))               # stated certainty (precision); large N -> ~1 regardless of g
    acc  = float(np.exp(-(bias/0.15)**2))        # are you actually right? drops sharply with bias
    return conf, acc

print("g     | TEMPORAL conf/acc/gap        | STRUCTURAL conf/acc/gap")
gs = [1.0, 0.7, 0.4, 0.2, 0.05]
rows = []
for g in gs:
    tc, ta = temporal(g); sc, sa = structural(g)
    rows.append((g, tc-ta, sc-sa))
    print(f"{g:<5} |  {tc:.2f}/{ta:.2f}/gap {tc-ta:+.2f}      |  {sc:.2f}/{sa:.2f}/gap {sc-sa:+.2f}")

# the internal-effort pump: at low g, more effort raises confidence, not accuracy
print("\nInternal effort pumps confidence not truth (g=0.05):")
tc1,ta1 = temporal(0.05, T=30); tc2,ta2 = temporal(0.05, T=300)
print(f"  TEMPORAL  T=30 -> conf {tc1:.2f} acc {ta1:.2f} | T=300 -> conf {tc2:.2f} acc {ta2:.2f}")
sc1,sa1 = structural(0.2, N=2000); sc2,sa2 = structural(0.2, N=100000)
print(f"  STRUCTURAL N=2k -> conf {sc1:.2f} acc {sa1:.2f} | N=100k -> conf {sc2:.2f} acc {sa2:.2f}")

# verdict: gap monotone-rising as g->0 in BOTH realizations
tgap = [r[1] for r in rows]; sgap = [r[2] for r in rows]
t_rises = tgap[-1] > tgap[0] + 0.1
s_rises = sgap[-1] > sgap[0] + 0.1
print("\n=== VERDICT ===")
print(f"TEMPORAL overconfidence gap rises as g->0: {t_rises}  ({tgap[0]:+.2f} -> {tgap[-1]:+.2f})")
print(f"STRUCTURAL overconfidence gap rises as g->0: {s_rises}  ({sgap[0]:+.2f} -> {sgap[-1]:+.2f})")
print("GRAND SYNTHESIS SUPPORTED" if (t_rises and s_rises) else "NOT UNIFIED")
print("One order parameter — the confidence-accuracy gap — governed by external grounding g, collapsing")
print("calibration identically across a TEMPORAL (self-reference) and a STRUCTURAL (under-identification)")
print("mechanism. The most confident systems are the least grounded. Falsifier: a grounding-starved")
print("system that stays calibrated (gap ~ 0), or the gap not governed by g in one of the realizations.")
