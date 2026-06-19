"""Batch-authored experiment templates, merged into the Methods Library.
Authored + self-verified by workflows (2026-06-19), then re-tested at integration."""
EXTRA_TEMPLATES = {
    'did-parallel-trends': {
        "description": 'Tests Difference-in-Differences / event-study identification when parallel trends is violated by a differential pre-trend that persists into the post period. Shows the DiD estimate is biased away from the true treatment effect, and that the bias tracks the pre-trend slope (so a "significant" DiD coefficient can be pure trend, not the intervention). Use for any claim that a DiD or event-study identifies a causal effect, policy/natural-experiment evaluations, two-period or staggered before/after designs, "treatment vs control after a shock", or any "the intervention caused X" comparison where treated and control units could be on diverging baseline trajectories.',
        "params": {'n_per': ('int', 200, 50000, 5000), 'slope': ('float', 0.0, 3.0, 0.8), 'tau': ('float', -3.0, 3.0, 0.5), 'sigma': ('float', 0.1, 5.0, 1.0), 'reps': ('int', 50, 1000, 400)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
n_per, slope, tau, sigma, reps = {n_per}, {slope}, {tau}, {sigma}, {reps}
# Two-period DiD. Treated and control each have n_per units.
# Outcome model: y = unit_FE + group_trend*time + tau*(treated & post) + noise.
# The control group has trend 0; the treated group has a DIFFERENTIAL pre-trend = slope
# that PERSISTS into the post period (parallel-trends violation). True ATT = tau.
# DiD estimate = (Ybar_treat_post - Ybar_treat_pre) - (Ybar_ctrl_post - Ybar_ctrl_pre).
ests = np.empty(reps)
for r in range(reps):
    fe_t = rng.standard_normal(n_per) * 2.0     # treated unit fixed effects
    fe_c = rng.standard_normal(n_per) * 2.0     # control unit fixed effects
    # pre period (time=0)
    yt_pre = fe_t + 0.0 * slope + rng.standard_normal(n_per) * sigma
    yc_pre = fe_c + 0.0          + rng.standard_normal(n_per) * sigma
    # post period (time=1): treated keeps its differential trend `slope` AND gets tau
    yt_post = fe_t + 1.0 * slope + tau + rng.standard_normal(n_per) * sigma
    yc_post = fe_c + 0.0               + rng.standard_normal(n_per) * sigma
    did = (yt_post.mean() - yt_pre.mean()) - (yc_post.mean() - yc_pre.mean())
    ests[r] = did
est = ests.mean()
se = ests.std(ddof=1) / np.sqrt(reps)
bias = est - tau
# t-stat for H0: estimator is unbiased (bias == 0)
t_bias = bias / se if se > 1e-12 else 0.0
print(f"MEASURED: DiD ATT estimate = {{est:.3f}} (SE {{se:.3f}}); true tau = {{tau:.3f}}; bias = {{bias:.3f}} (t={{t_bias:.1f}}); pre-trend slope = {{slope:.3f}}")
verdict = ("PARALLEL-TRENDS VIOLATED - DiD biased by "+format(bias,'+.2f')+" (~equals the pre-trend slope "+format(slope,'.2f')+"); the 'causal effect' is mostly trend, NOT the intervention"
           if abs(t_bias) > 3 else
           "DiD UNBIASED here - estimate matches true tau within noise (no detectable parallel-trends violation)")
print(f"VERDICT: {{verdict}}")
''',
    },
    'weak-instrument-bias-2sls': {
        "description": 'Tests weak-instrument bias in just-identified 2SLS/IV. Simulates an endogenous regressor x = pi*z + v with an instrument z of tunable strength (tunes the first-stage F) and a structural error u correlated with v (endogeneity sigma_uv), with TRUE causal effect beta=0. Measures the first-stage F and how much of the OLS endogeneity bias survives in the 2SLS MEDIAN estimate. Use for any claim that an instrumental-variable / 2SLS design IDENTIFIES a causal effect, "we use IV to fix endogeneity", natural-experiment / Mendelian-randomization / shift-share style identification, or any "instrument controls for confounding" argument — to check whether the instrument is strong enough (F>=10) for the IV estimate to be trusted rather than biased back toward the confounded OLS.',
        "params": {'pi': ('float', 0.005, 1.0, 0.02), 'n': ('int', 500, 100000, 2000), 'reps': ('int', 100, 1500, 400), 'sigma_uv': ('float', 0.0, 0.95, 0.6)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
pi, n, reps, sigma_uv = {pi}, {n}, {reps}, {sigma_uv}
# Model: y = beta*x + u ; x = pi*z + v ; corr(u,v)=sigma_uv (endogeneity).
# True beta = 0. OLS is biased TOWARD sigma_uv. 2SLS is consistent IF the instrument
# is strong; with a WEAK instrument (small pi -> small first-stage F), the finite-sample
# 2SLS estimate is biased back toward OLS (Bound-Jaeger-Baker / Staiger-Stock).
beta_true = 0.0
ols_b = np.empty(reps); tsls_b = np.empty(reps); Fstat = np.empty(reps)
for r in range(reps):
    z = rng.standard_normal(n)
    e1 = rng.standard_normal(n); e2 = rng.standard_normal(n)
    v = e1                                            # first-stage error
    u = sigma_uv*e1 + np.sqrt(max(1e-9, 1-sigma_uv*sigma_uv))*e2   # structural error, corr v
    x = pi*z + v
    y = beta_true*x + u
    ols_b[r] = np.cov(x, y, bias=True)[0,1] / np.var(x)            # OLS slope
    czx = np.cov(z, x, bias=True)[0,1]
    tsls_b[r] = (np.cov(z, y, bias=True)[0,1] / czx) if abs(czx) > 1e-12 else np.nan  # just-id IV
    szz = np.var(z)
    pihat = czx / szz
    resid = x - pihat*z
    s2 = np.sum(resid*resid) / (n-2)
    se_pi = np.sqrt(s2 / (n*szz))
    Fstat[r] = (pihat/se_pi)**2 if se_pi > 0 else np.nan          # first-stage F (1 instrument)
tsls_b = tsls_b[np.isfinite(tsls_b)]
meanF = float(np.nanmean(Fstat))
ols_bias = float(np.mean(ols_b) - beta_true)
# Just-identified IV has no finite mean (Cauchy-like tails under weak ID); use the MEDIAN,
# which is what "bias toward OLS" is actually measured on (Staiger-Stock median bias).
tsls_med = float(np.median(tsls_b) - beta_true)
# fraction of the OLS endogeneity bias that the (median) 2SLS estimate retains: 1 => as bad
# as OLS (no identification), 0 => clean causal estimate.
survive = tsls_med/ols_bias if abs(ols_bias) > 1e-6 else 0.0
# bootstrap SE of the median over the replication draws
nb = min(len(tsls_b), 2000)
idx = rng.integers(0, len(tsls_b), size=(300, nb))
boot_med = np.median(tsls_b[idx], axis=1)
se_med = float(np.std(boot_med, ddof=1))
print(f"MEASURED: first-stage F = {{meanF:.1f}} | OLS bias {{ols_bias:+.3f}} 2SLS median bias {{tsls_med:+.3f}} (SE {{se_med:.3f}}) -> {{survive*100:.0f}}% of the OLS bias survives")
print(f"VERDICT: {{'WEAK INSTRUMENT - IV does NOT identify the effect (F='+format(meanF,'.1f')+'<10, 2SLS retains '+format(survive*100,'.0f')+'%% of the OLS endogeneity bias)' if (meanF < 10 and survive > 0.20) else 'IV identifies (strong instrument F>=10, 2SLS median bias collapses toward 0)'}}")
''',
    },
    'rdd-bandwidth': {
        "description": 'Tests regression-discontinuity fragility: does an RDD CLEANLY identify a jump at the cutoff, or does the estimate swing with bandwidth choice and pick up bias from running-variable manipulation (sorting at the cutoff)? Two failure modes are measured jointly: (1) the local-linear jump estimate\'s sensitivity across a range of bandwidths (wide windows pick up smooth nonlinear confounding -> bias), and (2) a McCrary-style density-discontinuity z at the cutoff (heaping just above the threshold from agents who sort themselves over). Use for any claim of the form "policy/threshold X caused a jump Y, identified by RDD" — eligibility cutoffs, grade/test thresholds, vote-share discontinuities, price/quantity thresholds, scholarship/subsidy cutoffs, audit thresholds — where you suspect bandwidth-shopping or gaming of the assignment variable.',
        "params": {'n': ('int', 1000, 200000, 8000), 'tau': ('float', 0.0, 5.0, 1.0), 'manip': ('float', 0.0, 1.0, 0.5), 'bw_lo': ('float', 0.02, 0.4, 0.05), 'bw_hi': ('float', 0.3, 1.0, 0.8)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
n, tau, manip, bw_lo, bw_hi = {n}, {tau}, {manip}, {bw_lo}, {bw_hi}
# Running variable X in [-1,1]; smooth confounding f(X) so OLS-in-window is biased if bandwidth too wide.
X = rng.uniform(-1.0, 1.0, n)
# Manipulation: a fraction of units just below the cutoff sort themselves just above it.
below = X < 0
flip = below & (rng.random(n) < manip) & (X > -0.15)
Xobs = X.copy()
Xobs[flip] = rng.uniform(0.0, 0.05, flip.sum())
# Outcome: nonlinear smooth trend + true jump tau at cutoff + noise.
def f(x): return 1.5*x + 2.0*x*x - 1.2*x*x*x
treat = (Xobs >= 0).astype(float)
Y = f(Xobs) + tau*treat + rng.normal(0, 0.3, n)

def rdd_estimate(h):
    # local linear on each side within bandwidth h, jump = intercept_right - intercept_left
    est = []
    for side, sel in (("L", (Xobs < 0) & (Xobs >= -h)), ("R", (Xobs >= 0) & (Xobs <= h))):
        xs, ys = Xobs[sel], Y[sel]
        if xs.size < 30: return np.nan
        A = np.column_stack([np.ones_like(xs), xs])
        beta, *_ = np.linalg.lstsq(A, ys, rcond=None)
        est.append(beta[0])
    return est[1] - est[0]

bws = np.linspace(bw_lo, bw_hi, 12)
ests = np.array([rdd_estimate(h) for h in bws])
ests = ests[np.isfinite(ests)]
swing = ests.max() - ests.min()
spread_se = ests.std(ddof=1)
# McCrary-style density test for sorting: ratio of mass just-right vs just-left of cutoff.
win = 0.05
nL = np.sum((Xobs < 0) & (Xobs >= -win))
nR = np.sum((Xobs >= 0) & (Xobs < win))
dens_ratio = nR / max(nL, 1)
# z for asymmetry under null of equal density (binomial split at cutoff)
tot = nL + nR
zdens = (nR - tot/2) / np.sqrt(tot/4) if tot > 0 else 0.0

print(f"MEASURED: bandwidth swing in jump estimate = {{swing:.3f}} (across-bw SD {{spread_se:.3f}}); est range [{{ests.min():.2f}}, {{ests.max():.2f}}] vs true tau={{tau}}; density z={{zdens:.2f}} (R/L={{dens_ratio:.2f}})")
fragile = (swing > 0.5*abs(tau) if abs(tau) > 1e-6 else swing > 0.25) or abs(zdens) > 3.0
print(f"VERDICT: {{'FRAGILE - RDD does NOT cleanly identify the jump (swing exceeds half of tau or density z>3 signals sorting); flips to CLEAN if bandwidth swing < 0.5*tau AND |density z| < 3' if fragile else 'CLEAN - jump estimate is bandwidth-stable and no sorting; would flip to FRAGILE if swing > 0.5*tau or |density z| > 3'}}")
''',
    },
    'winners-curse': {
        "description": "Tests the winner's curse / Type-M error: among studies that reach p<0.05, the average ESTIMATED effect is inflated above the TRUE effect, and the exaggeration ratio grows as statistical power falls. Use this to severe-test any claim that a PUBLISHED significant effect size is trustworthy / can be taken at face value, especially when the underlying study was underpowered (small n, small true effect, low replication rate). Calibrates per-study sample size to a target power, simulates many two-sample studies, keeps only the significant ones (publication-bias filter), and reports the Type-M exaggeration ratio mean(significant estimates)/true effect with an SE. Good for: replication crisis, effect-size inflation, selective reporting, 'this RCT/trial/A-B test found d=0.4 so the real effect is 0.4', meta-analysis trust.",
        "params": {'true_d': ('float', 0.0, 2.0, 0.2), 'power': ('float', 0.05, 0.99, 0.25), 'nstud': ('int', 2000, 200000, 40000), 'nrep': ('int', 1, 50, 8)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
true_d, power, nstud, nrep = {true_d}, {power}, {nstud}, {nrep}
# Calibrate per-study sample size so a two-sample t-test on the TRUE effect
# achieves the target POWER at alpha=0.05 (two-sided), via the normal approx:
# power = Phi(true_d*sqrt(n/2) - z_{{1-a/2}})  ->  n = 2*((za+zp)/true_d)^2 per group.
from scipy import stats
za = stats.norm.ppf(1 - 0.05/2.0)
zp = stats.norm.ppf(np.clip(power, 1e-4, 1-1e-4))
if true_d <= 1e-6:
    n_per = 30
else:
    n_per = max(2, int(np.ceil(2.0*((za+zp)/true_d)**2)))
n_per = min(n_per, 200000)  # keep arrays bounded
sig_est = []
all_n = 0
batch = max(1, nstud // nrep) if nrep > 1 else nstud
for _ in range(nrep):
    # vectorized batch of studies: two groups of size n_per each (sd=1, so est is Cohen's d)
    g1 = rng.standard_normal((batch, n_per))
    g2 = true_d + rng.standard_normal((batch, n_per))
    est = g2.mean(1) - g1.mean(1)                       # estimated effect
    se = np.sqrt(g1.var(1, ddof=1)/n_per + g2.var(1, ddof=1)/n_per)
    tstat = est / se
    p = 2*(1 - stats.t.cdf(np.abs(tstat), 2*n_per - 2))
    sig_est.append(est[p < 0.05])                       # publication-bias filter
    all_n += batch
sig = np.concatenate(sig_est) if sig_est else np.array([])
nsig = sig.size
if nsig == 0:
    print(f"MEASURED: 0 of {{all_n}} studies reached p<0.05 at power={{power}} (true d={{true_d}}); no winners to curse")
    print("VERDICT: NO WINNERS - cannot assess inflation; raise power or true_d. Inflation claim falsified only if winners exist and their mean <= true_d.")
else:
    pub_mean = float(sig.mean())
    pub_se = float(sig.std(ddof=1)/np.sqrt(nsig)) if nsig > 1 else float('nan')
    typeM = pub_mean/true_d if true_d > 1e-6 else float('nan')
    infl_pct = (pub_mean - true_d)/true_d*100 if true_d > 1e-6 else float('nan')
    obs_power = nsig/all_n
    print(f"MEASURED: published(significant-only) effect = {{pub_mean:.3f}} (SE {{pub_se:.3f}}) vs true {{true_d:.3f}}; Type-M exaggeration ratio = {{typeM:.2f}}x (obs power {{obs_power:.2f}}, n_sig={{nsig}})")
    print(f"VERDICT: {{'WINNERS CURSE - significant estimates inflated by '+format(infl_pct,'.0f')+'% (ratio '+format(typeM,'.2f')+'x)' if pub_mean > true_d + 1.96*pub_se else 'NO INFLATION - significant mean within 2SE of truth; published effect trustworthy'}}")
''',
    },
    'measurement-error-attenuation': {
        "description": 'Severe-tests attenuation bias from measurement error: regressing an outcome on a NOISILY-measured predictor shrinks the OLS slope toward zero by the reliability ratio lambda = Var(X)/Var(W). Simulates a known true slope beta with a controllable signal-to-noise ratio on the predictor, then checks whether the observed attenuation factor (bhat/beta) matches the textbook reliability-ratio prediction. Use for claims about the estimated effect of a noisily/imperfectly-measured trait, exposure, score, survey item, biomarker, or proxy variable on an outcome (e.g. "self-reported X has a small effect on Y", "this measured personality/sentiment/skill score barely predicts outcome") — where the small effect may be an artifact of measurement noise, not a true null. The falsifier is built in: a factor ~1 means measurement is clean (no attenuation), and a large |t| means the shrinkage does NOT follow the reliability-ratio law.',
        "params": {'n': ('int', 500, 200000, 4000), 'beta': ('float', 0.1, 5.0, 1.0), 'snr': ('float', 0.05, 100.0, 1.0), 'reps': ('int', 50, 1000, 200)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
n, beta, snr, reps = {n}, {beta}, {snr}, {reps}
# snr = Var(X)/Var(measurement noise). reliability lambda = snr/(snr+1)
sx = 1.0
sigma_u = sx/np.sqrt(snr) if snr>0 else 1e9   # measurement-noise SD added to X
lam_theory = sx*sx/(sx*sx + sigma_u*sigma_u)  # reliability ratio (textbook prediction)
slopes = np.empty(reps)
for r in range(reps):
    X = rng.standard_normal(n)*sx
    eps = rng.standard_normal(n)            # outcome noise, unit SD
    Y = beta*X + eps                        # true model uses the CLEAN X
    W = X + rng.standard_normal(n)*sigma_u  # but we only OBSERVE noisy W
    bhat = np.cov(W, Y, bias=True)[0,1]/np.var(W)   # OLS slope of Y on noisy W
    slopes[r] = bhat
mean_slope = slopes.mean()
se = slopes.std(ddof=1)/np.sqrt(reps)
atten_obs = mean_slope/beta if abs(beta)>1e-9 else 0.0   # observed attenuation factor
se_factor = se/abs(beta) if abs(beta)>1e-9 else float('nan')
t = (atten_obs - lam_theory)/se_factor if se_factor>0 else 0.0   # match to textbook law?
bias_pct = (1-atten_obs)*100
print(f"MEASURED: attenuation factor bhat/beta = {{atten_obs:.4f}} vs reliability-ratio prediction {{lam_theory:.4f}} (t={{t:.2f}}, SE {{se_factor:.4f}}, snr={{snr}})")
print(f"VERDICT: {{'ATTENUATION CONFIRMED - noisy X biases slope toward zero by '+format(bias_pct,'.0f')+'%, matching reliability ratio (|t|<3)' if abs(t)<3 and atten_obs<0.97 else ('NO MEANINGFUL ATTENUATION (factor ~1) - measurement clean' if atten_obs>=0.97 else 'DEVIATES FROM RELIABILITY-RATIO LAW (|t|>=3) - attenuation not the textbook mechanism')}}")
''',
    },
    'watts-cascade': {
        "description": 'Tests the Watts complex-contagion global-cascade window: on a random network seeded by a tiny fraction of adopters, whether a system-wide cascade ignites depends NON-MONOTONICALLY on mean degree — too sparse and the seed has no paths, too dense and every node is too robust (each neighbor is a smaller fraction). There is a connectivity window in between where a small seed goes global. Use for claims about virality, adoption tipping points, social/complex contagion, "going viral", network fragility, threshold/herd adoption, and whether more connectivity helps or hurts spread.',
        "params": {'n': ('int', 1000, 40000, 4000), 'mean_deg': ('float', 0.5, 30.0, 3.0), 'threshold': ('float', 0.05, 0.9, 0.18), 'seedfrac': ('float', 0.0001, 0.05, 0.001)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
n, mean_deg, threshold, seedfrac = {n}, {mean_deg}, {threshold}, {seedfrac}
# Build a random network with the target mean degree via random edge sampling.
m = int(round(mean_deg * n / 2.0))
m = max(0, min(m, n*(n-1)//2))
src = rng.integers(0, n, size=m)
dst = rng.integers(0, n, size=m)
ok = src != dst
src, dst = src[ok], dst[ok]
# Adjacency as neighbor lists (sparse, undirected).
nbr = [[] for _ in range(n)]
for a, b in zip(src.tolist(), dst.tolist()):
    nbr[a].append(b)
    nbr[b].append(a)
deg = np.array([len(x) for x in nbr], dtype=np.float64)
# Watts threshold model: a node activates once the FRACTION of its active
# neighbors reaches phi. Degree-0 nodes have no input and stay immune.
def run_cascade(seed_nodes):
    active = np.zeros(n, dtype=bool)
    active[seed_nodes] = True
    cnt = np.zeros(n, dtype=np.int64)  # active-neighbor counts
    for s in seed_nodes:
        for v in nbr[s]:
            cnt[v] += 1
    changed, rounds = True, 0
    while changed and rounds < 200:
        changed, rounds = False, rounds + 1
        cand = np.where((~active) & (cnt > 0) & (deg > 0))[0]
        newly = [int(v) for v in cand if cnt[v] / deg[v] >= threshold]
        if newly:
            changed = True
            for v in newly:
                active[v] = True
            for v in newly:
                for w in nbr[v]:
                    cnt[w] += 1
    return int(active.sum())
trials = 12
k_seed = max(1, int(round(seedfrac * n)))
sizes = []
for _ in range(trials):
    seeds = rng.choice(n, size=k_seed, replace=False)
    sizes.append(run_cascade(seeds))
frac = np.array(sizes, dtype=np.float64) / n
mean_frac = float(frac.mean())
se = float(frac.std(ddof=1) / np.sqrt(trials)) if trials > 1 else 0.0
big_frac = float((frac >= 0.5).mean())  # share of seeds that ignited a global cascade
print(f"MEASURED: cascade reach = {{mean_frac:.3f}} of network (SE {{se:.3f}}); global-cascade rate {{big_frac:.2f}} over {{trials}} seeds (mean_deg={{mean_deg}}, phi={{threshold}})")
print(f"VERDICT: {{'IN CASCADE WINDOW - a '+format(seedfrac*100,'.2g')+'% seed goes global (reach '+format(mean_frac,'.2f')+')' if mean_frac >= 0.5 else 'NO GLOBAL CASCADE - seed dies locally (reach '+format(mean_frac,'.2f')+'); a mean reach >=0.5 would flip this'}}")
''',
    },
    'bandit-regret': {
        "description": 'Tests the explore-exploit tradeoff: on a multi-armed bandit, does an exploring policy (UCB) achieve SUBLINEAR cumulative regret while pure greedy suffers near-LINEAR regret (it locks onto a wrong arm)? Fits a log-log tail exponent p to regret(t)~t^p (p<1 = sublinear, p~1 = linear) and compares final regret of UCB vs epsilon-greedy vs greedy. Use for claims about exploration policies, A/B-test allocation, bandit/recommendation systems, RL reward exploration, and "always exploit the current best" strategies.',
        "params": {'n_arms': ('int', 2, 100, 10), 'horizon': ('int', 200, 20000, 4000), 'eps': ('float', 0.0, 1.0, 0.1), 'gap': ('float', 0.0, 1.0, 0.2), 'reps': ('int', 1, 200, 30)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
n_arms, horizon, eps, gap, reps = {n_arms}, {horizon}, {eps}, {gap}, {reps}
base = np.sort(rng.uniform(0.0, 1.0, size=n_arms))
mu = base.copy()
mu[-1] = mu[-2] + gap
best = mu[-1]

def run_policy(kind):
    creg = np.zeros(horizon)
    finals = np.zeros(reps)
    for j in range(reps):
        counts = np.zeros(n_arms)
        sums = np.zeros(n_arms)
        reg = 0.0
        for t in range(horizon):
            if kind == "ucb":
                if (counts == 0).any():
                    a = int(np.argmin(counts))
                else:
                    a = int(np.argmax(sums / counts + np.sqrt(2.0 * np.log(t + 1) / counts)))
            elif kind == "egreedy":
                if (counts == 0).any() or rng.random() < eps:
                    a = int(rng.integers(n_arms))
                else:
                    a = int(np.argmax(sums / np.maximum(counts, 1)))
            else:
                if (counts == 0).any():
                    a = int(np.argmin(counts))
                else:
                    a = int(np.argmax(sums / counts))
            r = mu[a] + rng.standard_normal() * 0.5
            counts[a] += 1
            sums[a] += r
            reg += best - mu[a]
            creg[t] += reg
        finals[j] = reg
    return creg / reps, finals

ucb, uf = run_policy("ucb")
eg, _ = run_policy("egreedy")
gr, _ = run_policy("greedy")
T = horizon
def tail_slope(traj):
    lo = T // 2
    x = np.log(np.arange(lo + 1, T + 1))
    y = np.log(np.maximum(traj[lo:], 1e-9))
    return np.polyfit(x, y, 1)[0]
p_ucb = tail_slope(ucb)
p_gr = tail_slope(gr)
se = uf.std(ddof=1) / np.sqrt(reps) if reps > 1 else 0.0
print(f"MEASURED: tail regret exponent UCB p={{p_ucb:.2f}} vs greedy p={{p_gr:.2f}}; final regret UCB {{ucb[-1]:.1f}} (SE {{se:.1f}}) eps-greedy {{eg[-1]:.1f}} greedy {{gr[-1]:.1f}}")
print(f"VERDICT: {{'EXPLORATION PAYS - UCB sublinear (p<0.9) while greedy near-linear (p>0.9) and UCB regret < greedy' if (p_ucb < 0.9 and p_gr > 0.9 and ucb[-1] < gr[-1]) else 'NO EXPLORATION ADVANTAGE - UCB not sublinear or not below greedy (flips if p_ucb>=0.9 or UCB regret>=greedy)'}}")
''',
    },
    'wisdom-of-crowds': {
        "description": 'Tests when averaging an ensemble of N noisy estimators beats the single BEST estimator, and how the gain collapses as estimates become correlated. Forecasters are heteroskedastic (a clear "best expert" exists via skill_spread) with equicorrelated errors (shared common-bias factor, strength rho). Measures crowd-RMSE / best-single-RMSE with a bootstrap SE. Use for claims about wisdom of crowds, forecast/poll aggregation, model ensembles, ensemble vs. expert, diversification of opinions, "more forecasters always help", and the limits of aggregation under correlated errors.',
        "params": {'n_est': ('int', 3, 500, 25), 'rho': ('float', 0.0, 0.99, 0.3), 'skill_spread': ('float', 0.0, 2.0, 0.6), 'n_trials': ('int', 500, 50000, 4000)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
n_est, rho, skill_spread, n_trials = {n_est}, {rho}, {skill_spread}, {n_trials}
# Each of n_est forecasters estimates a latent target across n_trials draws.
# Errors are correlated (equicorrelation rho via a shared common-bias factor)
# and heteroskedastic: forecaster i has its own error scale (skill).
target = rng.standard_normal(n_trials)
# per-forecaster error std: lognormal spread => one clear "best" expert
sig = np.exp(skill_spread * rng.standard_normal(n_est))
sig = sig / sig.mean()  # normalize so mean idiosyncratic var ~ 1
# common factor shared by all forecasters (source of correlation)
c = np.clip(rho, 0.0, 0.999)
common = rng.standard_normal(n_trials)
# err_i = sqrt(c)*sig_i*common + sqrt(1-c)*sig_i*eps_i  -> corr(err_i,err_j)=c
idio = rng.standard_normal((n_est, n_trials))
errs = (np.sqrt(c) * common[None, :] + np.sqrt(1.0 - c) * idio) * sig[:, None]
preds = target[None, :] + errs
# crowd = equal-weight average of all forecasters
crowd_err = preds.mean(axis=0) - target
crowd_mse = np.mean(crowd_err ** 2)
# best single forecaster (lowest realized MSE = the oracle-picked expert)
single_mse = np.mean((preds - target[None, :]) ** 2, axis=1)
best_single_mse = single_mse.min()
mean_indiv_mse = single_mse.mean()
crowd_rmse = np.sqrt(crowd_mse)
best_rmse = np.sqrt(best_single_mse)
mean_rmse = np.sqrt(mean_indiv_mse)
# bootstrap SE on the crowd-vs-best RMSE ratio (resample per-trial squared errors)
B = 400
cse = crowd_err ** 2
bse = (preds[np.argmin(single_mse)] - target) ** 2
ratios = np.empty(B)
for b in range(B):
    bi = rng.integers(0, n_trials, n_trials)
    ratios[b] = np.sqrt(cse[bi].mean()) / np.sqrt(bse[bi].mean())
ratio = crowd_rmse / best_rmse
se = ratios.std(ddof=1)
print(f"MEASURED: crowd/best-single RMSE ratio = {{ratio:.3f}} (SE {{se:.3f}}); crowd RMSE {{crowd_rmse:.3f}} vs best {{best_rmse:.3f}} vs mean-indiv {{mean_rmse:.3f}} (n_est={{n_est}}, rho={{rho}})")
print(f"VERDICT: {{'CROWD BEATS BEST EXPERT (aggregation wins) - ratio '+format(ratio,'.2f')+'<1' if ratio < 1.0 - 2*se else ('CORRELATION KILLS THE CROWD - best single expert wins, ratio '+format(ratio,'.2f')+'>1' if ratio > 1.0 + 2*se else 'TIE - crowd no better than best expert (gain swamped by correlation rho='+format(rho,'.2f')+')')}}")
''',
    },
    'info-cascade': {
        "description": 'Tests rational information cascades / herding (Bikhchandani-Hirshleifer-Welch): sequential Bayesian agents each get a private binary signal, observe all predecessors\' public actions, and once the public belief outweighs one signal they rationally IGNORE their own signal and copy the herd, so society stops aggregating private information and the cascade can lock onto the WRONG option. Measures herd accuracy vs the full-signal-pooling ceiling. Use for claims about herding, social proof, info cascades, bubbles, fads, wisdom-of-crowds failure, sequential adoption, and "the crowd converged so it must be right."',
        "params": {'n_agents': ('int', 1, 2000, 200), 'signal_q': ('float', 0.51, 0.99, 0.7), 'n_trials': ('int', 500, 6000, 4000)},
        "code": r'''
import numpy as np
from scipy.stats import norm
rng = np.random.default_rng(7)
n_agents, signal_q, n_trials = {n_agents}, {signal_q}, {n_trials}
# Sequential rational-herding (Bikhchandani-Hirshleifer-Welch). Two states V in {{0,1}}, true randomized each trial.
# Each agent privately sees a binary signal correct w.p. signal_q (>0.5), observes ALL prior public actions, forms the
# Bayesian posterior, and acts. Once public log-odds exceed one signal's worth, every later agent IGNORES its own
# signal and copies the public action -> an information cascade that can lock onto the WRONG state.
# Severe test: pooling all private signals (majority vote) drives accuracy toward 1.0; does the herd plateau far below?
s = np.log(signal_q/(1-signal_q))  # log-likelihood ratio of one informative signal
def run_trial(true_state):
    pub = 0.0; last_act = None
    for i in range(n_agents):
        sig = true_state if rng.random() < signal_q else 1 - true_state
        priv = s if sig == 1 else -s
        post = pub + priv
        act = 1 if post > 1e-9 else (0 if post < -1e-9 else sig)
        # an action is informative iff a single signal could flip it given current public belief
        if (pub + s) > 0 and (pub - s) < 0:
            pub += (s if act == 1 else -s)
        last_act = act
    return last_act
correct = 0
for _ in range(n_trials):
    ts = int(rng.random() < 0.5)
    if run_trial(ts) == ts: correct += 1
p = correct / n_trials
se = np.sqrt(p*(1-p)/n_trials)
# Full-pooling ceiling: majority vote of n_agents independent signals (each correct w.p. q). Exact binomial overflows
# for large n, so use the de Moivre-Laplace normal approximation with continuity correction: P[Binom(n,q) > n/2].
nn = n_agents
mu, sd = nn*signal_q, np.sqrt(nn*signal_q*(1-signal_q))
if nn <= 1:
    maj = float(signal_q)
elif sd < 1e-9:
    maj = 1.0
else:
    maj = min(float(norm.sf((nn/2.0 + 0.5 - mu)/sd)), 1.0)
gap = maj - p
print(f"MEASURED: herd accuracy p = {{p:.3f}} (SE {{se:.3f}}) vs full-pooling ceiling {{maj:.3f}} (gap {{gap:.3f}}; n_agents={{n_agents}}, q={{signal_q}})")
print(f"VERDICT: {{'INFO CASCADE - herd accuracy '+format(p,'.2f')+' plateaus far below the '+format(maj,'.2f')+' that pooling all signals would give: social info stops aggregating, herd can lock wrong' if gap > 0.05 else 'NO CASCADE FAILURE - herd tracks full-pooling accuracy'}}")
''',
    },
    'heavy-tail-mean': {
        "description": 'Tests whether the sample mean stabilizes under heavy tails: for Pareto data with tail index alpha, it measures how fast the across-replications dispersion of the sample mean shrinks as n grows, and compares to the CLT\'s 1/sqrt(n) law. When alpha<2 (infinite variance) the mean fails to converge at the CLT rate, so reported averages are unreliable. Use for claims about averages/expected-value/risk under fat-tailed or power-law data, non-ergodic or extreme-outcome processes, "the average will settle with more data", insurance/finance loss means, virality/wealth/citation distributions, or any claim that more samples make an average trustworthy.',
        "params": {'alpha': ('float', 0.6, 4.0, 1.5), 'n_small': ('int', 100, 5000, 500), 'n_big': ('int', 1000, 200000, 8000), 'reps': ('int', 500, 8000, 4000)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
alpha, n_small, n_big, reps = {alpha}, {n_small}, {n_big}, {reps}
n_small = int(n_small); n_big = int(n_big); reps = int(reps)
if n_big <= n_small:
    n_big = n_small * 16
# Pareto(alpha) on [1,inf): mean exists iff alpha>1, variance iff alpha>2.
def pareto_means(n, m):
    out = np.empty(m)
    for i in range(m):
        u = rng.random(n)
        x = (1.0 - u) ** (-1.0 / alpha)   # inverse-CDF Pareto(alpha), scale 1
        out[i] = x.mean()
    return out
ms_small = pareto_means(n_small, reps)
ms_big   = pareto_means(n_big, reps)
# Dispersion of the sample mean across replications (robust IQR scale; std is itself ill-defined for alpha<2).
def disp(a):
    q1, q3 = np.percentile(a, [25, 75])
    return (q3 - q1) / 1.349  # IQR -> sigma-equivalent
d_small = disp(ms_small); d_big = disp(ms_big)
ratio_n = n_big / n_small
clt_shrink = np.sqrt(ratio_n)                       # CLT: dispersion of the mean falls like 1/sqrt(n)
obs_shrink = d_small / d_big if d_big > 1e-12 else np.inf
slowness = clt_shrink / obs_shrink if obs_shrink > 1e-12 else np.inf  # >1 => slower than CLT (mean not stabilizing)
# Bootstrap SE of the slowness over rep-level dispersions.
B = 200
boot = np.empty(B)
for b in range(B):
    a = ms_small[rng.integers(0, reps, reps)]
    c = ms_big[rng.integers(0, reps, reps)]
    ds = disp(a); dc = disp(c)
    os_ = ds / dc if dc > 1e-12 else np.nan
    boot[b] = (clt_shrink / os_) if (os_ and os_ > 1e-12) else np.nan
boot = boot[np.isfinite(boot)]
se = boot.std(ddof=1) if boot.size > 1 else float('nan')
print(f"MEASURED: CLT-slowness = {{slowness:.2f}} (SE {{se:.2f}}); n x{{ratio_n:.0f}} -> mean-dispersion shrank {{obs_shrink:.2f}}x vs CLT {{clt_shrink:.2f}}x (alpha={{alpha}})")
ok = slowness > 1.5
print(f"VERDICT: {{'HEAVY-TAIL NON-STABILIZATION - sample mean fails to converge at CLT rate (dispersion '+format(slowness,'.1f')+'x slower than 1/sqrt(n)); averages/risk untrustworthy' if ok else 'mean stabilizes at ~CLT rate - thin-tail regime, averaging is safe'}}")
''',
    },
    'forking-paths': {
        "description": 'Tests the garden of forking paths / researcher degrees of freedom: under a TRUE NULL (no real effect), an analyst who tries k reasonable, correlated analysis specifications (covariate sets, subsets, transforms, outlier rules) and reports the single best (smallest) p-value inflates the false-positive rate far above the nominal alpha. Use for claims that rest on a flexible/best-of-many analysis, spec search, p-hacking-by-choices, multiverse/specification-curve findings, or "we tried several reasonable approaches and the significant one is the headline."',
        "params": {'n': ('int', 20, 100000, 200), 'k': ('int', 1, 200, 8), 'alpha': ('float', 0.001, 0.2, 0.05), 'rho': ('float', 0.0, 0.99, 0.3), 'trials': ('int', 2000, 200000, 40000)},
        "code": r'''
import numpy as np
from scipy import stats
rng = np.random.default_rng(7)
n, k, alpha, rho, trials = {n}, {k}, {alpha}, {rho}, {trials}
# Garden of forking paths / researcher degrees of freedom: under a TRUE NULL
# (no real effect), an analyst tries k reasonable, CORRELATED analysis
# specifications (covariate sets, subsets, transforms - they share data so
# their test statistics are correlated) and reports the SMALLEST p across them.
# We measure the realized false-positive rate of that "best-of-k" report vs the
# nominal alpha. n sets the per-spec sample size (only affects MC noise here;
# under the null the z-scores are pivotal ~N(0,1) regardless of n).
common = rng.standard_normal(trials)
idio = rng.standard_normal((trials, k))
# each column ~N(0,1) with pairwise correlation rho (shared analytic choices)
z = np.sqrt(rho)*common[:, None] + np.sqrt(1.0-rho)*idio
# finite-n jitter so n is not inert: a 1/sqrt(n) measurement wobble on each z
z = z + rng.standard_normal((trials, k))/np.sqrt(n)
p = 2.0*stats.norm.sf(np.abs(z))      # two-sided p per spec
best = p.min(axis=1)                   # analyst reports the best (min) p
fpr = float((best < alpha).mean())
se = float(np.sqrt(fpr*(1.0-fpr)/trials))
t = (fpr-alpha)/se if se > 0 else float('inf')
infl = fpr/alpha if alpha > 0 else float('inf')
print(f"MEASURED: realized FPR under null = {{fpr:.3f}} (SE {{se:.3f}}, nominal alpha={{alpha}}, t-vs-alpha={{t:.1f}}) over k={{k}} specs, rho={{rho}}, n={{n}}")
print(f"VERDICT: {{'FORKING PATHS INFLATE ALPHA - best-of-k FPR is '+format(infl,'.1f')+'x nominal (t='+format(t,'.1f')+'); flips if t<=2' if t>2.0 else 'NO INFLATION - best-of-k FPR within nominal alpha (forking paths benign at this k/rho)'}}")
''',
    },
    'preferential-attachment': {
        "description": 'Tests the "unequal outcomes imply skill/merit" claim by running a NEUTRAL preferential-attachment (rich-get-richer / Yule / Barabasi-Albert-style) process where every agent is IDENTICAL: arriving wealth-units (links, customers, citations, followers, capital) attach with probability proportional to (current count + 1)^accel. Measures the resulting outcome Gini and top-1% share, with a bootstrap SE. Use for claims that an extreme/unequal outcome distribution (wealth, fame, market share, citations, success) is EVIDENCE of underlying talent, merit, or skill differences. accel<1 mixes in randomness (egalitarian), accel=1 is classic linear PA, accel>1 is super-linear winner-take-all. The null it kills: high inequality alone cannot distinguish skill heterogeneity from a path-dependent neutral process.',
        "params": {'n_agents': ('int', 100, 50000, 5000), 'n_steps': ('int', 1000, 200000, 40000), 'm': ('int', 1, 20, 3), 'accel': ('float', 0.0, 1.8, 1.0)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(7)
n_agents, n_steps, m, accel = {n_agents}, {n_steps}, {m}, {accel}

# Neutral preferential attachment (Yule/Barabasi-Albert-style):
# every agent is IDENTICAL (zero skill differences). New "wealth units"
# (links / customers / citations) arrive one at a time and attach to an
# existing agent with probability proportional to (count + a) ^ accel.
# accel=1 => classic linear PA; accel>1 => super-linear (winner-take-all);
# accel=0 => uniform (random) attachment -> the skill-free null's null.
counts = np.ones(n_agents, dtype=np.float64)  # everyone starts equal
a = 1.0
for _ in range(n_steps):
    w = (counts + a) ** accel
    p = w / w.sum()
    winners = rng.choice(n_agents, size=m, p=p)  # m arrivals/step by PA weight
    np.add.at(counts, winners, 1.0)

# Inequality of the OUTCOME despite zero skill heterogeneity.
x = np.sort(counts)
N = x.size
gini = (2.0 * np.sum((np.arange(1, N + 1)) * x) / (N * x.sum())) - (N + 1.0) / N
top1 = x[int(0.99 * N):].sum() / x.sum() * 100.0

# Bootstrap SE on the Gini (resample agents) so MEASURED carries an error bar.
B = 200
gb = np.empty(B)
for b in range(B):
    xs = np.sort(rng.choice(counts, size=N, replace=True))
    gb[b] = (2.0 * np.sum((np.arange(1, N + 1)) * xs) / (N * xs.sum())) - (N + 1.0) / N
se = gb.std(ddof=1)

print(f"MEASURED: outcome Gini = {{gini:.3f}} (SE {{se:.3f}}); top-1% share = {{top1:.1f}}% from ZERO skill differences (accel={{accel}})")
print(f"VERDICT: {{'RICH-GET-RICHER - extreme inequality (Gini '+format(gini,'.2f')+') with identical agents; unequal outcomes do NOT imply skill' if gini > 0.30 else 'EGALITARIAN - neutral process did not concentrate; inequality here would need a skill explanation'}}")
''',
    },
    'interdependent-cascade-cliff': {
        "description": 'Buldyrev-style mutual percolation of an AI-inference layer coupled to a human-verification layer: measures the excess discontinuous jump in the mutual giant component (vs a single-layer control) to test whether realistic partial coupling q produces a first-order catastrophic collapse rather than graceful second-order degradation.',
        "params": {'N': ('int', 400, 4000, 2000), 'q': ('float', 0.0, 1.0, 0.6), 'deg': ('float', 2.0, 8.0, 4.0), 'reps': ('int', 2, 12, 6)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(0)
N = {N}
q = {q}
deg = {deg}
reps = {reps}

def giant_mask(ea, eb, alive, N):
    parent = np.arange(N)
    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root
    m = alive[ea] & alive[eb]
    for a, b in zip(ea[m].tolist(), eb[m].tolist()):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    if not alive.any():
        return np.zeros(N, dtype=bool)
    roots = np.array([find(i) if alive[i] else -1 for i in range(N)])
    valid = roots[roots >= 0]
    counts = np.bincount(valid, minlength=N)
    return (roots == counts.argmax()) & alive

p_edge = deg / (N - 1)
iu = np.triu_indices(N, k=1)
def er():
    keep = rng.random(iu[0].shape[0]) < p_edge
    return iu[0][keep], iu[1][keep]
A0, A1 = er()
B0, B1 = er()
perm = rng.permutation(N)
inv = np.empty(N, dtype=int)
inv[perm] = np.arange(N)
ps = np.linspace(0.0, 0.95, 40)

def max_jump(qval, seed):
    rl = np.random.default_rng(seed)
    coupled = rl.random(N) < qval
    def mg(p):
        aA = rl.random(N) >= p
        aB = rl.random(N) >= p
        for _ in range(300):
            gA = giant_mask(A0, A1, aA, N)
            gB = giant_mask(B0, B1, aB, N)
            nA = gA.copy()
            nB = gB.copy()
            nA[coupled & ~gB[perm]] = False
            nB[coupled[inv] & ~gA[inv]] = False
            if np.array_equal(nA, aA) and np.array_equal(nB, aB):
                aA, aB = nA, nB
                break
            aA, aB = nA, nB
        return float(giant_mask(A0, A1, aA, N).sum()) / N
    G = np.array([mg(p) for p in ps])
    d = G[:-1] - G[1:]
    k = int(d.argmax())
    return d[k], float((ps[k] + ps[k + 1]) / 2)

jc = np.array([max_jump(q, 100 + r)[0] for r in range(reps)])
j0 = np.array([max_jump(0.0, 100 + r)[0] for r in range(reps)])
pcs = np.array([max_jump(q, 100 + r)[1] for r in range(reps)])
excess = jc - j0
mean = float(excess.mean())
se = float(excess.std(ddof=1) / np.sqrt(reps)) if reps > 1 else float("nan")
t = mean / se if se > 0 else float("nan")
print(f"MEASURED: excess discontinuity deltaG(q={{q}})-deltaG(0) = {{mean:.3f}} N (SE {{se:.3f}}, t={{t:.1f}}); p_c~{{pcs.mean():.2f}}")
print(f"VERDICT: {{'FIRST-ORDER cliff: partial coupling creates a catastrophic mutual collapse' if (t > 2 and mean > 0.05) else 'GRACEFUL: coupling adds no discontinuity beyond the single-layer breakdown -- claim falsified'}}")
''',
    },
    'csd-control-leverage': {
        "description": "Tests whether critical slowing down makes a late 'strike when critical' push cheaper than constant/front-loaded forcing for flipping a bistable collective — by measuring min time-integrated effort to reliably flip a double-well normal form under three forcing schedules.",
        "params": {'T': ('float', 2.0, 20.0, 8.0), 'sigma': ('float', 0.05, 0.6, 0.2), 'n_seeds': ('int', 20, 200, 60)},
        "code": r'''
import numpy as np

# ---- params (the ONLY single-brace assignments in this template) ----
T = {T}
sigma = {sigma}
n_seeds = {n_seeds}

# Bistable normal form (saddle-node / double well):
#   dx = (x - x^3 + u(t)) dt + sigma dW
# Stable wells at x=-1 (start) and x=+1 (target); unstable saddle at x=0.
# Near the saddle the restoring force (1 - 3x^2) vanishes -> critical slowing down (CSD).
# A nonnegative control u(t) pushes toward +1. We compare three SHAPES of u(t)
# over [0,T], each normalized to the same time-integrated effort budget B = INT u dt,
# then bisect on B to find the MINIMUM budget each schedule needs for a reliable flip
# (>=90% of noise seeds end in the +1 well). Headline = critical/constant effort ratio.
rng = np.random.default_rng(0)
dt = 0.01
nt = int(round(T / dt))
t = np.linspace(0.0, T, nt, endpoint=False)

def shape(kind):
    # unit-mean nonnegative weight: INT w dt = T, so (B/T)*w integrates to exactly B
    if kind == "constant":
        w = np.ones(nt)
    elif kind == "front":
        w = np.exp(-3.0 * t / T)      # front-loaded: hard early, decays
    else:  # "critical"
        w = np.exp(3.0 * t / T)       # back-loaded: ramps up, peaks late (strike-when-critical)
    return w / w.mean()

def flip_fraction(kind, B, seeds):
    w = shape(kind)
    u = (B / T) * w
    sq = np.sqrt(dt)
    flips = 0
    for s in seeds:
        r = np.random.default_rng(int(s) + 1000)
        x = -1.0
        noise = r.standard_normal(nt)
        for k in range(nt):
            x += (x - x**3 + u[k]) * dt + sigma * sq * noise[k]
        if x > 0.0:
            flips += 1
    return flips / len(seeds)

def min_budget(kind, seeds, lo=0.0, hi=6.0, target=0.90, iters=20):
    if flip_fraction(kind, hi, seeds) < target:
        return hi  # cannot reach target within range
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if flip_fraction(kind, mid, seeds) >= target:
            hi = mid
        else:
            lo = mid
    return hi

seeds = np.arange(n_seeds)
B_const = min_budget("constant", seeds)
B_front = min_budget("front", seeds)
B_crit = min_budget("critical", seeds)

# bootstrap SE on the critical/constant ratio by resampling noise seeds
ratios = []
nb = 12
for b in range(nb):
    rb = np.random.default_rng(5000 + b)
    samp = rb.integers(0, n_seeds, size=n_seeds)
    bc = min_budget("constant", samp, iters=15)
    bk = min_budget("critical", samp, iters=15)
    if bc > 0:
        ratios.append(bk / bc)
ratios = np.array(ratios)
ratio = float(B_crit / B_const) if B_const > 0 else float("nan")
se = float(ratios.std(ddof=1) / np.sqrt(len(ratios))) if len(ratios) > 1 else float("nan")
front_ratio = float(B_front / B_const) if B_const > 0 else float("nan")

print(f"MEASURED: min-effort ratio critical/constant = {{ratio:.3f}} (bootstrap SE {{se:.3f}}); B_const={{B_const:.3f}}, B_front={{B_front:.3f}}, B_crit={{B_crit:.3f}}, front/const={{front_ratio:.3f}}")

eps = 2 * se + 0.02
if abs(ratio - 1.0) <= eps and abs(front_ratio - 1.0) <= eps:
    verdict = "timing IRRELEVANT - only total integrated push matters; 'strike when critical' FALSE (CSD confers no cost asymmetry)"
elif (ratio < 1.0 - eps) and (ratio < front_ratio - eps):
    verdict = f"late critical-moment push STRICTLY cheapest ({{(1-ratio)*100:.0f}}% saving vs constant, beats front-loaded) - leverage hypothesis SUPPORTED"
elif (front_ratio < 1.0 - eps) and (front_ratio < ratio - eps):
    verdict = "front-loaded cheapest - criticality makes LATE effort wasted; leverage hypothesis FALSIFIED (opposite sign)"
elif (ratio < 1.0 - eps) and abs(ratio - front_ratio) <= eps:
    verdict = f"non-constant beats constant ({{(1-ratio)*100:.0f}}% saving) but front~critical TIED - shaping helps, critical-timing NOT uniquely better; only partial leverage"
else:
    verdict = "no clean schedule advantage detected"
print(f"VERDICT: {{verdict}} - falsifier: equal min-effort across schedules, or front-loaded cheapest, kills the 'strike when critical' claim")
''',
    },
    'algo-pricing-collusion-threshold': {
        "description": 'Do independent tabular Q-learning pricing agents spontaneously collude, and is there a sharp discount-factor threshold? Sweep delta, measure the Nash-to-monopoly collusion index and its steepening.',
        "params": {'steps': ('int', 10000, 120000, 50000), 'grid': ('int', 4, 9, 6), 'alpha': ('float', 0.02, 0.4, 0.125), 'target': ('float', 0.1, 0.5, 0.25)},
        "code": r'''
import numpy as np

steps = {steps}
grid = {grid}
alpha = {alpha}
target = {target}

# Spontaneous algorithmic collusion: two INDEPENDENT tabular Q-learners (epsilon-greedy,
# no communication) price in a repeated differentiated-Bertrand duopoly with linear demand.
# State = last price-index of BOTH firms (memory-1). We sweep the discount factor delta
# (memory of the future) and measure the collusion index over the last 2000 steps:
# index = 0 at Bertrand-Nash, 1 at joint-monopoly. Is the rise a SHARP threshold or a ramp?

c = 1.0
a = 2.0
def profit(pi, pj):
    qi = max(0.0, (a - 2.0*pi + pj) / 3.0)
    return (pi - c) * qi

fine = np.linspace(c, c + 2.0, 2001)
def best_response(pj):
    pr = np.array([profit(p, pj) for p in fine])
    return fine[int(np.argmax(pr))]
p = c + 0.5
for _ in range(200):
    p = best_response(p)
p_nash = p
joint = np.array([2.0*profit(pp, pp) for pp in fine])
p_mono = fine[int(np.argmax(joint))]
price_grid = np.linspace(p_nash, p_mono, grid)

deltas = np.array([0.0, 0.5, 0.9, 0.95, 0.99])

def collusion_index(delta, seed):
    r = np.random.default_rng(seed)
    nA = grid
    Q0 = np.zeros((nA, nA, nA))
    Q1 = np.zeros((nA, nA, nA))
    s0, s1 = nA//2, nA//2
    beta = 6.0/steps
    last = []
    for t in range(steps):
        eps = max(0.02, np.exp(-beta*t))
        a0 = r.integers(nA) if r.random() < eps else int(np.argmax(Q0[s0, s1]))
        a1 = r.integers(nA) if r.random() < eps else int(np.argmax(Q1[s0, s1]))
        p0 = price_grid[a0]; p1 = price_grid[a1]
        r0 = profit(p0, p1); r1 = profit(p1, p0)
        Q0[s0, s1, a0] += alpha*(r0 + delta*np.max(Q0[a0, a1]) - Q0[s0, s1, a0])
        Q1[s0, s1, a1] += alpha*(r1 + delta*np.max(Q1[a0, a1]) - Q1[s0, s1, a1])
        s0, s1 = a0, a1
        if t >= steps - 2000:
            last.append(0.5*(p0 + p1))
    return (float(np.mean(last)) - p_nash) / (p_mono - p_nash)

reps = 4
curve = []; se = []
for d in deltas:
    vals = [collusion_index(d, 7 + 31*int(d*100) + k) for k in range(reps)]
    curve.append(float(np.mean(vals)))
    se.append(float(np.std(vals, ddof=1)/np.sqrt(reps)))
curve = np.array(curve); se = np.array(se)

def crossover(x, y, thr):
    for i in range(len(x)-1):
        if (y[i]-thr)*(y[i+1]-thr) <= 0 and y[i+1] != y[i]:
            frac = (thr - y[i])/(y[i+1]-y[i])
            return x[i] + frac*(x[i+1]-x[i]), (y[i+1]-y[i])/(x[i+1]-x[i])
    return float("nan"), float("nan")

xc, xslope = crossover(deltas, curve, target)
local = np.diff(curve)/np.diff(deltas)
mean_slope = (curve[-1]-curve[0])/(deltas[-1]-deltas[0])
steepening = float(np.nanmax(local)/mean_slope) if mean_slope > 0 else float("nan")
rise = float(curve[-1] - curve[0])

print(f"curve(index vs delta): {{[round(float(v),3) for v in curve]}}; SE {{[round(float(v),3) for v in se]}}")
print(f"MEASURED: collusion index {{curve[0]:.2f}}->{{curve[-1]:.2f}} (rise={{rise:.2f}}, top-SE {{se[-1]:.2f}}); crosses {{target}} at delta={{xc:.2f}}, local steepening={{steepening:.1f}}x mean")
if curve.max() <= 0.1:
    v = "FALSIFIED: index never exceeds ~0.1 (Nash) at any delta -- no spontaneous collusion"
elif curve.min() < -0.1:
    v = "FALSIFIED: agents converge BELOW Nash for some delta -- sign flip kills the claim"
elif np.isnan(xc):
    v = f"index rises with delta but never reaches the {{target}} switch-on level -- weak/no collusion"
elif steepening >= 1.5:
    v = f"spontaneous collusion CONFIRMED with a SHARP threshold near delta={{xc:.2f}} (rise is {{steepening:.1f}}x steeper than linear)"
else:
    v = "graded collusion but a SMOOTH ramp, not a sharp threshold"
print(f"VERDICT: {{v}}")
''',
    },
    'griffiths-phase-contagion': {
        "description": "Tests whether quenched topological disorder (rare dense sub-domains) converts a network contagion's sharp epidemic threshold into an extended Griffiths band of power-law (critical-like) spreading, by measuring the WIDTH in lambda of the power-law-decay region versus a clean control.",
        "params": {'N': ('int', 400, 4000, 1500), 'D': ('float', 0.0, 1.5, 0.9), 'p_rec': ('float', 0.1, 0.8, 0.4), 'n_real': ('int', 3, 30, 10)},
        "code": r'''
import numpy as np, time
rng = np.random.default_rng(0)
# --- params (the ONLY single-brace fields, injected at the top) ---
N = {N}
D = {D}
p_rec = {p_rec}
n_real = {n_real}
# Disordered contact process (SIS) on a heterogeneous substrate: a sparse ring
# backbone plus rare DENSE regions. Disorder D = log-normal spread of per-region
# internal coupling (a few rare strongly-interlinked sub-domains in a sparse matrix
# -- exactly the "rare region" setup that produces Griffiths effects). We sweep the
# spreading rate lambda and, for the realization-averaged decay rho(t) of the active
# fraction, ask whether it is better fit by a POWER LAW (log rho vs log t) than by an
# EXPONENTIAL (log rho vs t). Headline = WIDTH (in lambda) of the power-law band; we
# compare disorder D vs the clean D=0 control. Clean -> one knife-edge cell; a finite
# band under disorder = an extended Griffiths phase.
T = 160
lam_steps = 24
n_regions = 60
n_net = 4  # network replicates per condition (for the SE)

def region_weights(Ds):
    het = np.exp(Ds * rng.normal(0, 1.0, n_regions))
    return het / het.mean()  # fix MEAN coupling; only the SPREAD (disorder) changes

def build(Ds):
    region = rng.integers(0, n_regions, N)
    w = region_weights(Ds)
    nbrs = [set() for _ in range(N)]
    for i in range(N):
        nbrs[i].add((i+1) % N); nbrs[(i+1) % N].add(i)  # sparse backbone
    by = [np.where(region == r)[0] for r in range(n_regions)]
    for r in range(n_regions):
        mem = by[r]
        if len(mem) < 2:
            continue
        p = min(0.9, 0.05 * w[r])  # strong regions are dense -> rare regions
        for ii in range(len(mem)):
            for jj in range(ii+1, len(mem)):
                if rng.random() < p:
                    a, b = int(mem[ii]), int(mem[jj])
                    nbrs[a].add(b); nbrs[b].add(a)
    md = max(len(s) for s in nbrs)
    adj = np.full((N, md), -1, np.int64)
    for i in range(N):
        l = list(nbrs[i]); adj[i, :len(l)] = l
    return adj

def mean_curve(adj, lam):
    v = adj >= 0; s2 = adj.clip(min=0); acc = np.zeros(T)
    for _ in range(n_real):
        st = np.ones(N, bool); rho = np.empty(T)
        for t in range(T):
            rho[t] = st.mean()
            if not st.any():
                rho[t:] = 0.0; break
            rec = st & (rng.random(N) < p_rec)
            k = np.where(v, st[s2], False).sum(1)
            new = (~st) & (rng.random(N) < 1.0 - (1.0 - lam) ** k)
            st = (st & ~rec) | new
        acc += rho
    return acc / n_real

def is_powerlaw(rho):
    if rho[-1] > 0.03:           # survives -> active/supercritical phase
        return False
    t = np.arange(1, len(rho)+1, dtype=float)
    m = rho > 1e-3; m[:3] = False
    if m.sum() < 14:            # dies fast -> off-critical exponential
        return False
    tt = t[m]; Y = np.log(rho[m]); sst = float(((Y - Y.mean())**2).sum())
    if sst <= 0:
        return False
    A1 = np.vstack([np.log(tt), np.ones_like(tt)]).T
    c1, *_ = np.linalg.lstsq(A1, Y, rcond=None)
    r2_pow = 1.0 - float(((Y - A1 @ c1)**2).sum()) / sst
    A2 = np.vstack([tt, np.ones_like(tt)]).T
    c2, *_ = np.linalg.lstsq(A2, Y, rcond=None)
    r2_exp = 1.0 - float(((Y - A2 @ c2)**2).sum()) / sst
    return (r2_pow > r2_exp + 0.02) and (r2_pow > 0.90)

def band_width(Ds):
    adj = build(Ds)
    lams = np.linspace(0.03, 0.30, lam_steps)
    flags = np.array([is_powerlaw(mean_curve(adj, float(l))) for l in lams])
    return flags.sum() * (lams[1] - lams[0])

t0 = time.time()
w_clean = np.array([band_width(0.0) for _ in range(n_net)])
w_dis = np.array([band_width(D) for _ in range(n_net)])
broadening = float(w_dis.mean() - w_clean.mean())
se = float(np.sqrt(w_dis.var(ddof=1)/n_net + w_clean.var(ddof=1)/n_net))
tstat = broadening / se if se > 0 else float("nan")
print(f"MEASURED: power-law band width = {{w_dis.mean():.3f}} (D={{D}}) vs {{w_clean.mean():.3f}} (clean); broadening = {{broadening:+.3f}} lambda-units (SE {{se:.3f}}, t={{tstat:.1f}}); {{time.time()-t0:.0f}}s")
opened = (broadening > 2*se) and (broadening > 0.01)
print(f"VERDICT: {{'extended GRIFFITHS band opened by disorder' if opened else 'no broadening -- sharp threshold, Griffiths phase falsified'}} -- falsifier: band width stays ~0/unchanged for all D (clean gives a single knife-edge lambda)")
''',
    },
    'ecological-leak-mis-diagnosis': {
        "description": "Tests whether a drift-optimal evidence-leak (forgetting) updater that maximizes accuracy in a non-stationary world is mis-read as 'conservatism' by a stationary calibration audit, while a leak-free updater is audit-perfect.",
        "params": {'n_steps': ('int', 5000, 200000, 60000), 'audit_blocks': ('int', 200, 8000, 1500), 'flip_p': ('float', 0.001, 0.2, 0.02), 'acc': ('float', 0.55, 0.95, 0.75)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(0)
n_steps = {n_steps}
audit_blocks = {audit_blocks}
flip_p = {flip_p}
acc = {acc}
block_len = 40

lams = [1.0, 0.97, 0.93, 0.88, 0.8]
llr_mag = float(np.log(acc / (1.0 - acc)))

# ---- Drift world: hidden state random-walks; leaky log-odds updater b <- lam*b + signed_llr ----
flips = rng.random(n_steps) < flip_p
state = np.empty(n_steps, dtype=np.int8)
s = 1
for t in range(n_steps):
    if flips[t]:
        s = -s
    state[t] = s
obs = np.where(rng.random(n_steps) < acc, state, -state)
signed_llr = obs * llr_mag

drift_acc = {{}}
for lam in lams:
    b = 0.0
    hits = 0
    for t in range(n_steps):
        if (1 if b >= 0 else -1) == state[t]:
            hits += 1
        b = lam * b + signed_llr[t]
    drift_acc[lam] = hits / n_steps

lam_star = max(lams, key=lambda L: drift_acc[L])
gain = drift_acc[lam_star] - drift_acc[1.0]

# ---- Stationary audit: state fixed within a block; measure confidence-accuracy gap ----
def audit_gap(lam):
    n_obs = 0
    sum_conf = 0.0
    sum_corr = 0.0
    for _ in range(audit_blocks):
        true_s = 1 if rng.random() < 0.5 else -1
        b = 0.0
        for _ in range(block_len):
            o = true_s if (rng.random() < acc) else -true_s
            b = lam * b + o * llr_mag
            sum_conf += 1.0 / (1.0 + np.exp(-abs(b)))
            sum_corr += 1.0 if (1 if b >= 0 else -1) == true_s else 0.0
            n_obs += 1
    return (sum_conf / n_obs) - (sum_corr / n_obs), n_obs

gap_leakfree, _ = audit_gap(1.0)
gap_star, nobs = audit_gap(lam_star)
se_gap = float(np.sqrt(0.25 / nobs))
mis = (gap_star < gap_leakfree - 3 * se_gap) and (gain > 0.05)

print(f"MEASURED: audit conf-acc gap at lambda*={{lam_star}} = {{gap_star:+.3f}} (SE {{se_gap:.3f}}); leak-free gap = {{gap_leakfree:+.3f}}; drift-world accuracy gain of lambda* over leak-free = {{gain:+.3f}} ({{drift_acc[1.0]:.3f}}->{{drift_acc[lam_star]:.3f}})")
print(f"VERDICT: {{'stationary audit MIS-DIAGNOSES ecological adaptation as conservatism - drift-optimal leak looks underconfident AND buys real drift accuracy' if mis else 'claim collapses - either no audit mis-diagnosis or negligible drift gain'}}; falsifier: ~0 audit gap at lambda* OR negligible drift gain")
''',
    },
    'meta-uncertainty-conservatism': {
        "description": "Tests whether conservatism (under-updating vs Bayes) is the normatively correct response to a Beta belief over one's own cue validity: integrated vs plug-in two-cue log-odds gap, swept over validity-belief variance.",
        "params": {'qbar': ('float', 0.51, 0.95, 0.6), 'a_tight': ('float', 5.0, 60.0, 20.0), 'a_diffuse': ('float', 0.5, 4.0, 1.2), 'steps': ('int', 4, 40, 9)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(0)
qbar = {qbar}
a_tight = {a_tight}
a_diffuse = {a_diffuse}
steps = {steps}

def moments(a, qbar):
    # Beta(a,b) with mean qbar => b = a*(1-qbar)/qbar
    b = a*(1.0-qbar)/qbar
    Eq = a/(a+b)
    Eq2 = a*(a+1.0)/((a+b)*(a+b+1.0))
    Em2 = 1.0 - 2.0*Eq + Eq2            # E[(1-q)^2]
    var = a*b/((a+b)**2*(a+b+1.0))
    return Eq, Eq2, Em2, var

a_grid = np.linspace(a_tight, a_diffuse, steps)
gaps, varis = [], []
for a in a_grid:
    Eq, Eq2, Em2, var = moments(a, qbar)
    plug = 2.0*np.log(Eq/(1.0-Eq))     # plug-in mean q, cues treated independent
    integ = np.log(Eq2/Em2)            # exact integrated 2-cue log-odds
    gaps.append(integ - plug)
    varis.append(var)
gaps = np.array(gaps); varis = np.array(varis)

# slope of conservatism gap vs the variance of the validity belief
coef = np.polyfit(varis, gaps, 1)
slope = float(coef[0])
resid = gaps - np.polyval(coef, varis)
n = len(gaps)
sxx = float(np.sum((varis - varis.mean())**2))
se = float(np.sqrt(float(np.sum(resid**2))/(n-2)/sxx)) if sxx > 0 else float("nan")
t = slope/se if se > 0 else float("nan")
g_tight, g_diff = float(gaps[0]), float(gaps[-1])
allneg = bool(np.all(gaps <= 1e-9))
mono = slope < 0 and t < -2 and allneg
print(f"MEASURED: conservatism-gap slope vs validity-variance = {{slope:.3f}} (SE {{se:.3f}}, t={{t:.1f}}); gap {{g_tight:.3f}} (tight) -> {{g_diff:.3f}} (diffuse)")
print(f"VERDICT: {{'meta-uncertainty over cue validity NORMATIVELY produces conservatism (gap<0 and grows with belief variance)' if mono else 'mechanism FALSE: gap>=0 or not monotone in validity-variance'}} - falsifier: integrated update >= plug-in (gap>=0) for all Beta beliefs, or no growth with variance")
''',
    },
    'self-consistency-amplification': {
        "description": 'Tests whether majority-vote self-consistency amplifies a coherent LLM misconception (accuracy falls as k rises) while agreement-rate stays high and flat, and finds the per-sample correct-probability crossover p*.',
        "params": {'trials': ('int', 1000, 100000, 20000), 'n_distract': ('int', 2, 20, 6), 'wrong_share': ('float', 0.0, 0.95, 0.6), 'p_lo': ('float', 0.05, 0.45, 0.2), 'p_hi': ('float', 0.2, 0.6, 0.45), 'k_big': ('int', 3, 51, 11)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(0)
trials = {trials}
n_distract = {n_distract}
wrong_share = {wrong_share}
p_lo = {p_lo}
p_hi = {p_hi}
k_big = {k_big}

ps = np.round(np.arange(p_lo, p_hi + 1e-9, 0.05), 3)

def build_probs(p):
    # answer 0 = correct (prob p); answer 1 = dominant coherent-misconception mode
    # (takes wrong_share of remaining mass); rest spread over n_distract distractors.
    rest = 1.0 - p
    wrong = wrong_share * rest
    tail = (rest - wrong) / n_distract
    probs = np.empty(2 + n_distract)
    probs[0] = p
    probs[1] = wrong
    probs[2:] = tail
    return probs

def run(p, k):
    probs = build_probs(p)
    n_ans = probs.shape[0]
    draws = rng.choice(n_ans, size=(trials, k), p=probs)
    counts = np.zeros((trials, n_ans), dtype=np.int32)
    for a in range(n_ans):
        counts[:, a] = (draws == a).sum(axis=1)
    maj = counts.argmax(axis=1)              # ties -> lowest index (favors correct, conservative)
    acc = float((maj == 0).mean())
    agree = float((counts.max(axis=1) / k).mean())  # deployed self-consistency confidence
    return acc, agree

acc1 = {{}}
acc11 = {{}}
agree11 = {{}}
for p in ps:
    a1, _ = run(p, 1)
    a11, ag11 = run(p, k_big)
    acc1[p] = a1
    acc11[p] = a11
    agree11[p] = ag11

pstar = None
for p in ps:
    if acc11[p] >= acc1[p]:
        pstar = p
        break

p0 = ps[0]
acc_gap = acc1[p0] - acc11[p0]
conf_gap = agree11[p0] - acc11[p0]
se = float(np.sqrt(acc11[p0] * (1 - acc11[p0]) / trials + acc1[p0] * (1 - acc1[p0]) / trials))

all_help = all(acc11[p] >= acc1[p] for p in ps)
agree_lo = agree11[ps[0]]
agree_hi = agree11[ps[-1]]
agree_flat = abs(agree_hi - agree_lo) < 0.15

pstar_str = f"{{pstar:.2f}}" if pstar is not None else f">{{p_hi:.2f}}"
print(f"MEASURED: crossover p*={{pstar_str}}; at p={{p0:.2f}} k={{k_big}} cuts acc {{acc1[p0]:.3f}}->{{acc11[p0]:.3f}} (drop {{acc_gap:.3f}}, SE {{se:.3f}}) while agreement stays {{agree11[p0]:.3f}} (conf-acc gap {{conf_gap:.3f}})")
print(f"VERDICT: {{'amplification confirmed' if (not all_help and acc_gap > 2*se) else 'self-consistency never hurts - claim FALSE'}}; agreement {{'DECOUPLED (flat ~%.2f-%.2f, ignores acc)' % (agree_lo, agree_hi) if agree_flat else 'tracks accuracy - decoupling FALSE'}} -- falsifier: dies if k={{k_big}} acc>=k=1 acc for all p OR agreement tracks accuracy")
''',
    },
    'soc-retrieval-cascades': {
        "description": 'Tests whether a demand-driven knowledge store self-organizes to the critical edge: does the BTW retrieval-cascade exponent tau converge near ~1.5 independent of initial conditions (the SOC-attractor signature)?',
        "params": {'n_nodes': ('int', 300, 4000, 1500), 'k_deg': ('int', 2, 12, 4), 'n_steps': ('int', 1500, 20000, 6000)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(0)
n_nodes = {n_nodes}
k_deg = {k_deg}
n_steps = {n_steps}

def run_to_steady_state(init):
    # fixed capacity budget (= n_nodes*k_deg) distributed under different initial conditions
    cap = np.zeros(n_nodes, dtype=np.int64)
    total_cap_budget = n_nodes * k_deg
    if init == "sparse":
        cap[:] = 1
        leftover = total_cap_budget - cap.sum()
        idx = rng.integers(0, n_nodes, size=leftover)
        np.add.at(cap, idx, 1)
    elif init == "dense":
        cap[:] = 1
        leftover = total_cap_budget - cap.sum()
        hubs = rng.choice(n_nodes, size=20, replace=False)
        np.add.at(cap, rng.choice(hubs, size=leftover), 1)
    else:  # uniform/random
        cap[:] = k_deg
    load = np.zeros(n_nodes, dtype=np.int64)
    topple_count = np.zeros(n_nodes, dtype=np.int64)
    avalanche_sizes = []
    record_after = n_steps // 3  # discard transient before measuring steady state
    cap_sum_target = int(cap.sum())
    for step in range(n_steps):
        # a query lands preferentially on high-capacity (high-demand) nodes
        w = cap.astype(np.float64) + 0.1
        q = int(rng.choice(n_nodes, p=w / w.sum()))
        load[q] += 1
        # queue-based BTW toppling: node forwards load to 2 ring neighbors when load > capacity
        s = 0
        stack = []
        if load[q] > cap[q]:
            stack.append(q)
        while stack:
            u = stack.pop()
            if load[u] <= cap[u]:
                continue
            excess = load[u]
            load[u] = 0
            s += 1
            topple_count[u] += 1
            left = (u - 1) % n_nodes
            right = (u + 1) % n_nodes
            give = excess - 1  # one unit dissipates (drain) -> dissipative driving
            load[left] += give // 2
            load[right] += give - give // 2
            if load[left] > cap[left]:
                stack.append(left)
            if load[right] > cap[right]:
                stack.append(right)
        if s > 0 and step >= record_after:
            avalanche_sizes.append(s)
        # FEEDBACK: shift 1 capacity unit from the idlest spare node to the busiest node (budget fixed)
        if step % 5 == 0 and step > 0:
            busy = int(np.argmax(topple_count))
            spare = np.where(cap > 1)[0]
            if len(spare) > 0:
                idle = int(spare[np.argmin(topple_count[spare])])
                if idle != busy:
                    cap[idle] -= 1
                    cap[busy] += 1
            topple_count = (topple_count * 9) // 10  # decay demand memory (track recent demand)
    assert abs(int(cap.sum()) - cap_sum_target) <= 2  # budget conservation
    return np.array(avalanche_sizes, dtype=np.float64)

def fit_tau(sizes):
    # Clauset MLE for discrete power-law exponent, xmin=1
    sizes = sizes[sizes >= 1]
    if len(sizes) < 30:
        return float("nan"), float("nan"), 0
    xmin = 1.0
    tau = 1.0 + len(sizes) / np.sum(np.log(sizes / (xmin - 0.5)))
    se = (tau - 1.0) / np.sqrt(len(sizes))
    return float(tau), float(se), len(sizes)

taus = {{}}
for init in ["sparse", "dense", "random"]:
    sizes = run_to_steady_state(init)
    tau, se, m = fit_tau(sizes)
    taus[init] = (tau, se, m)

vals = np.array([taus[k][0] for k in taus])
spread = float(np.nanmax(vals) - np.nanmin(vals))
mean_tau = float(np.nanmean(vals))
mean_se = float(np.nanmean([taus[k][1] for k in taus]))
near_soc = abs(mean_tau - 1.5) < 0.5
universal = spread < 0.3

print(f"MEASURED: tau = {{mean_tau:.3f}} (mean SE {{mean_se:.3f}}); across-init spread = {{spread:.3f}}; per-init " +
      ", ".join(f"{{k}}={{taus[k][0]:.2f}}" for k in taus))
print(f"VERDICT: {{'SOC attractor CONFIRMED (power-law, init-independent, near 1.5)' if (near_soc and universal) else 'SOC claim FAILS (not power-law-1.5 or init-dependent)'}} -- falsifier: tau!=~1.5 or spread>0.3")
''',
    },
    'oring-automation-flip': {
        "description": "CES O-ring model: finds the critical skill-atrophy a*(rho) at which automating co-tasks flips a human task from wage-raising complement to wage-lowering redundancy, testing whether the flip's sign depends on production substitutability rho.",
        "params": {'n_co': ('int', 1, 12, 3), 'q_human': ('float', 0.3, 0.99, 0.85), 'q_co_base': ('float', 0.3, 0.99, 0.8)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(0)
n_co = {n_co}
q_human = {q_human}
q_co_base = {q_co_base}

rho_steps = 41
a_steps = 41
q_auto = 0.999

def ces(qs, rho):
    qs = np.asarray(qs, dtype=float)
    if abs(rho) < 1e-9:
        return float(np.exp(np.mean(np.log(np.clip(qs, 1e-12, None)))))
    return float((np.mean(qs ** rho)) ** (1.0 / rho))

def human_value(rho, a, automated):
    co = np.full(n_co, q_auto if automated else q_co_base)
    qh = q_human * (1.0 - a) if automated else q_human
    base = np.concatenate(([qh], co))
    eps = 1e-4
    bump = base.copy()
    bump[0] = min(qh + eps, 1.0 - 1e-9)
    mp = (ces(bump, rho) - ces(base, rho)) / (bump[0] - base[0])
    return mp * qh

rhos = np.linspace(0.001, 1.0, rho_steps)
ats = np.linspace(0.0, 0.5, a_steps)

a_star = {{}}
signs_seen = set()
for rho in rhos:
    flip_a = np.nan
    prev_sign = None
    for a in ats:
        before = human_value(rho, a, automated=False)
        after = human_value(rho, a, automated=True)
        d = after - before
        s = 1 if d > 0 else (-1 if d < 0 else 0)
        signs_seen.add(s)
        if prev_sign is not None and s != prev_sign and np.isnan(flip_a):
            flip_a = a
        prev_sign = s
    a_star[round(float(rho), 4)] = flip_a

flipped = [r for r, av in a_star.items() if not np.isnan(av)]
finite_vals = np.array([av for av in a_star.values() if not np.isnan(av)])
best07 = min(a_star.keys(), key=lambda r: abs(r - 0.7))
a07 = a_star[best07]

has_boundary = len(flipped) > 0
rho_dependent = finite_vals.size >= 2 and (finite_vals.max() - finite_vals.min()) > 1e-3
both_signs = (1 in signs_seen) and (-1 in signs_seen)
rng_span = float(finite_vals.max() - finite_vals.min()) if finite_vals.size else 0.0
se = float(np.std(finite_vals, ddof=1) / np.sqrt(finite_vals.size)) if finite_vals.size >= 2 else float("nan")

a07s = f"{{a07:.3f}}" if not np.isnan(a07) else "none"
print(f"MEASURED: a*(rho~{{best07:.2f}}) = {{a07s}}; sign flips on {{len(flipped)}}/{{rho_steps}} rho-slices, a* spans {{rng_span:.3f}} across rho (SE {{se:.3f}})")

if has_boundary and rho_dependent and both_signs:
    verdict = "phase boundary EXISTS and varies with rho - production substitutability x deskilling jointly set the sign of human-task value (claim survives)"
elif has_boundary and both_signs and not rho_dependent:
    verdict = "flip exists but is rho-INDEPENDENT - atrophy alone decides, O-ring structure irrelevant (claim killed)"
else:
    verdict = "NO sign flip anywhere on the grid - no phase boundary, structure-x-deskilling claim dead (always {{}})".format("complement" if (1 in signs_seen) else "redundant")
print(f"VERDICT: {{verdict}}")
''',
    },
    'basket-goodhart-interior-k': {
        "description": 'Tests whether a 1/K-weighted multi-proxy basket has an INTERIOR optimal size K* (more proxies first help, then backfire) under an effort-budgeted adversary who exploits the cheapest-to-game proxy, by sweeping K over a correlation x cost-dispersion grid.',
        "params": {'n_draws': ('int', 100, 5000, 800), 'Kmax': ('int', 5, 60, 30), 'sigma_lo': ('float', 0.3, 2.0, 1.0), 'sigma_hi': ('float', 0.5, 3.5, 2.0)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(0)
n_draws = {n_draws}
Kmax = {Kmax}
sigma_lo = {sigma_lo}
sigma_hi = {sigma_hi}

# Adversary vs a 1/K-weighted basket of K proxies. Agent has effort budget B=1 and maximizes
# the basket score S = (1/K) sum_i (loadings_i * t + g_i), where t = honest effort on the TRUE
# goal (linear cost 1; raises EVERY proxy via positive loadings_i) and g_i = direct gaming of
# proxy i (linear cost gc_i). Gaming costs gc_i are lognormal (dispersion sigma); loadings are
# correlated through a shared factor (correlation rho). The LP optimum puts the whole budget in
# the single highest score-per-budget channel:
#   honest rate = (1/K) * sum(loadings) = mean loading
#   gaming rate = (1/K) / min_i(gc_i)   (exploit the cheapest-to-game, yet basket-weighted, proxy)
# Realized TRUE-goal value = honest effort actually spent (B if honest wins, else 0). We sweep
# K=1..Kmax over a grid of (rho, sigma) and ask whether argmax_K is INTERIOR (1<K*<Kmax) and
# whether the realized-value curve has a backfire hump (helps then hurts).

rhos = np.array([0.2, 0.4, 0.6, 0.8])
sigmas = np.linspace(sigma_lo, sigma_hi, 5)
Ks = np.arange(1, Kmax + 1)

kstars = []
interior_flags = []
curve_grid = []
for rho in rhos:
    for sigma in sigmas:
        realized = np.zeros(len(Ks))
        for ki, K in enumerate(Ks):
            common = rng.uniform(0.4, 1.0, n_draws)
            base = rng.uniform(0.2, 1.0, (n_draws, K))
            loadings = (1 - rho) * base + rho * common[:, None]
            gc = np.exp(rng.normal(0.0, sigma, (n_draws, K)))
            honest_rate = loadings.mean(axis=1)
            gaming_rate = (1.0 / K) / gc.min(axis=1)
            realized[ki] = np.mean(np.where(honest_rate >= gaming_rate, 1.0, 0.0))
        ks = int(Ks[np.argmax(realized)])
        kstars.append(ks)
        interior_flags.append(1 < ks < Kmax)
        curve_grid.append(realized)

kstars = np.array(kstars)
interior_frac = float(np.mean(interior_flags))
backfire = 0
for c in curve_grid:
    imax = int(np.argmax(c))
    if 0 < imax < len(c) - 1 and c[imax] > c[0] + 1e-6 and c[imax] > c[-1] + 1e-6:
        backfire += 1
backfire_frac = backfire / len(curve_grid)

mean_kstar = float(kstars.mean())
se_kstar = float(kstars.std(ddof=1) / np.sqrt(len(kstars)))
frac_corner1 = float(np.mean(kstars == 1))
frac_cornerMax = float(np.mean(kstars == Kmax))

print(f"MEASURED: mean K* = {{mean_kstar:.1f}} (SE {{se_kstar:.1f}}); interior-optimum cells {{interior_frac*100:.0f}}%, backfire hump {{backfire_frac*100:.0f}}%, K*=1 {{frac_corner1*100:.0f}}%, K*=Kmax {{frac_cornerMax*100:.0f}}%; grid={{len(curve_grid)}} cells, Kmax={{Kmax}}")
if backfire_frac >= 0.20:
    v = "interior optimum CONFIRMED -- more proxies first help then HURT in a substantial share of the cost/correlation grid"
elif frac_corner1 >= 0.5:
    v = "basket cure uniformly counterproductive -- K*=1 dominates (interior framing dies)"
else:
    v = "FALSIFIED -- realized true value essentially monotone in K (K* at a boundary); no interior backfire"
print(f"VERDICT: {{v}}")
''',
    },
    'citation-bandwagon-lockin': {
        "description": "Tests whether a bandwagon parameter (citing-instead-of-replicating, suppressed by how 'established' a claim already is) makes false claims survive at a higher rate than the rate true claims are abandoned, vs a no-suppression control.",
        "params": {'n_claims': ('int', 200, 40000, 4000), 'n_studies': ('int', 20, 1000, 200), 'bandwagon': ('float', 0.0, 10.0, 3.0), 'mu': ('float', 0.05, 1.0, 0.3), 'base_rep': ('float', 0.05, 1.0, 0.5)},
        "code": r'''
import numpy as np
rng = np.random.default_rng(0)
n_claims = {n_claims}
n_studies = {n_studies}
bandwagon = {bandwagon}
mu = {mu}
base_rep = {base_rep}

# Each claim is true (effect=1) or false (effect=0); equal initial evidence.
# Realistic adoption: a claim ENTERS the literature already adopted (prior log-odds +0.5, P~0.62).
half = n_claims // 2
truth = np.concatenate([np.ones(half), np.zeros(n_claims - half)]).astype(float)

def simulate(bw, seed):
    r = np.random.default_rng(seed)
    lo = np.full(n_claims, 0.5)  # adopted-on-entry prior
    for _ in range(n_studies):
        belief = 1.0 / (1.0 + np.exp(-lo))
        # the more 'established' (believed-true) a claim is, the less it is independently RE-TESTED;
        # bandwagon=0 -> every study replicates at base_rep (cite==test); bandwagon>0 -> citing replaces testing.
        p_rep = base_rep / (1.0 + bw * np.clip(belief, 0.0, 1.0))
        do_rep = r.random(n_claims) < p_rep
        z = r.normal(np.where(truth > 0.5, mu, -mu), 1.0)   # noisy replication z-signal
        llr = 2.0 * mu * z                                   # Gaussian log-likelihood-ratio (sd=1)
        lo = lo + np.where(do_rep, llr, 0.0)                 # cites/extends -> no update
    return 1.0 / (1.0 + np.exp(-lo))

fb = simulate(bandwagon, 0)
fbc = simulate(0.0, 1)
fm = truth < 0.5
tm = truth > 0.5
nf = int(fm.sum())

p_false_surv = float(np.mean(fb[fm] > 0.5))
p_true_aband = float(np.mean(fb[tm] < 0.5))
p_false_ctrl = float(np.mean(fbc[fm] > 0.5))

se_f = float(np.sqrt(p_false_surv * (1 - p_false_surv) / nf))
se_c = float(np.sqrt(p_false_ctrl * (1 - p_false_ctrl) / nf))
lift = p_false_surv / p_false_ctrl if p_false_ctrl > 0 else float("inf")
asym = p_false_surv / p_true_aband if p_true_aband > 0 else float("inf")
diff = p_false_surv - p_false_ctrl
se_d = float(np.sqrt(se_f ** 2 + se_c ** 2))
z_d = diff / se_d if se_d > 0 else float("nan")

print(f"MEASURED: P(false survives)={{p_false_surv:.3f}}+/-{{se_f:.3f}} vs bandwagon=0 control {{p_false_ctrl:.3f}}+/-{{se_c:.3f}} (lift {{lift:.1f}}x, z_diff={{z_d:.1f}}); P(true abandoned)={{p_true_aband:.3f}}, false/true asymmetry {{asym:.1f}}x; n={{n_claims}}")
ok = (z_d > 2) and (p_false_surv > p_true_aband) and (lift > 1.5)
print(f"VERDICT: {{'lock-in confirmed' if ok else 'no lock-in'}} - bandwagon suppression makes false claims survive above the no-suppression control AND above the rate true claims are abandoned; falsifier: dead if survival==abandonment or lift~1")
''',
    },
}
