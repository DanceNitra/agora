import numpy as np

# ============================================================
# Alvarez & Ferman (2020) replication:
# DiD with FEW treated units + spatially/serially-correlated
# errors vs Synthetic Control. True effect = 0.
# Question: does standard DiD inference UNDER-cover (CI cov < 0.95)?
# Does SC do materially better (coverage closer to nominal /
# lower estimation error)?
# ============================================================

rng = np.random.default_rng(12345)

# ---- Design ----
N = 30          # total units
T = 12          # total periods
T0 = 8          # pre-treatment periods (post = T - T0 = 4)
N_TREAT = 1     # FEW treated units (the regime A&F study)
REPS = 200
TRUE_EFFECT = 0.0

# Error structure: each unit gets
#   y_it = alpha_i + lambda_t + u_it
# where u_it is AR(1) in time (serial corr) and ALSO loaded on a
# common factor (cross-sectional / "spatial" correlation across units).
rho   = 0.7     # serial (AR1) correlation
fac_load_sd = 1.0   # spread of factor loadings -> cross-sectional corr
sig_idio = 1.0  # idiosyncratic shock sd
sig_factor = 1.0  # common factor sd per period

def gen_panel():
    # unit and time fixed effects (nuisance; DiD removes them)
    alpha = rng.normal(0, 1, size=N)
    lam   = rng.normal(0, 1, size=T)

    # common factor with its own AR(1) over time -> spatially correlated,
    # serially correlated errors that fixed effects do NOT absorb
    loadings = rng.normal(0, fac_load_sd, size=N)        # per-unit loading
    f = np.zeros(T)
    e = rng.normal(0, sig_factor, size=T)
    f[0] = e[0]
    for t in range(1, T):
        f[t] = rho * f[t-1] + np.sqrt(1 - rho**2) * e[t]
    factor_term = np.outer(loadings, f)                  # N x T

    # idiosyncratic AR(1) per unit
    u = np.zeros((N, T))
    eps = rng.normal(0, sig_idio, size=(N, T))
    u[:, 0] = eps[:, 0]
    for t in range(1, T):
        u[:, t] = rho * u[:, t-1] + np.sqrt(1 - rho**2) * eps[:, t]

    y = alpha[:, None] + lam[None, :] + factor_term + u
    # true effect is 0, so no treatment added
    return y

def did_estimate(y, treated_idx):
    # 2x2 generalized DiD: treated vs control, pre vs post.
    treated = np.zeros(N, dtype=bool)
    treated[treated_idx] = True
    pre = slice(0, T0)
    post = slice(T0, T)
    # group-period means
    yt_pre  = y[treated][:, pre].mean()
    yt_post = y[treated][:, post].mean()
    yc_pre  = y[~treated][:, pre].mean()
    yc_post = y[~treated][:, post].mean()
    att = (yt_post - yt_pre) - (yc_post - yc_pre)

    # Standard cluster-robust (by unit) DiD inference via the regression
    # y_it = b0 + b1*Treat_i + b2*Post_t + b3*(Treat_i*Post_t) + e_it,
    # SE clustered by unit -- the textbook "standard" approach.
    units = np.repeat(np.arange(N), T)
    Treat = np.repeat(treated.astype(float), T)
    Post  = np.tile((np.arange(T) >= T0).astype(float), N)
    Y = y.reshape(-1)
    X = np.column_stack([np.ones_like(Y), Treat, Post, Treat * Post])
    XtX = X.T @ X
    XtX_inv = np.linalg.pinv(XtX)
    beta = XtX_inv @ (X.T @ Y)
    resid = Y - X @ beta
    # cluster-robust (CR0) covariance, clusters = units
    meat = np.zeros((4, 4))
    for g in range(N):
        m = units == g
        Xg = X[m]
        ug = resid[m]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    G = N
    # small-cluster correction commonly applied
    cc = G / (G - 1.0)
    V = XtX_inv @ meat @ XtX_inv * cc
    se_att = np.sqrt(V[3, 3])
    from scipy import stats
    tcrit = stats.t.ppf(0.975, df=G - 1)   # t with G-1 dof (standard)
    lo, hi = beta[3] - tcrit * se_att, beta[3] + tcrit * se_att
    return beta[3], lo, hi

def synthetic_control(y, treated_idx):
    # Single treated unit. Fit convex weights on controls to match the
    # treated unit's PRE outcomes (simplex-constrained least squares),
    # then post-period gap is the SC estimate of the effect.
    tr = treated_idx[0]
    ctrl = [i for i in range(N) if i != tr]
    Z = y[ctrl][:, :T0].T        # T0 x (N-1)
    target = y[tr, :T0]          # T0
    w = _simplex_lstsq(Z, target)
    synth = y[ctrl].T @ w        # T
    gap = y[tr] - synth
    att_sc = gap[T0:].mean()     # post-period mean gap (effect estimate)

    # Placebo / permutation inference: run SC treating each control as
    # if treated, build the null distribution of post-period mean gap,
    # form a 95% interval from placebo quantiles centered at estimate.
    placebo = []
    for p in ctrl:
        others = [i for i in range(N) if i != p]
        Zp = y[others][:, :T0].T
        tp = y[p, :T0]
        wp = _simplex_lstsq(Zp, tp)
        sp = y[others].T @ wp
        gp = (y[p] - sp)[T0:].mean()
        placebo.append(gp)
    placebo = np.array(placebo)
    qlo, qhi = np.quantile(placebo, [0.025, 0.975])
    # 95% CI for true effect: estimate +/- placebo spread (centered)
    lo = att_sc - qhi
    hi = att_sc - qlo
    return att_sc, lo, hi, gap[T0:]

def _simplex_lstsq(Z, target, iters=200):
    # projected gradient on the probability simplex with a step size
    # scaled by the spectral norm of Z (stable, fast convergence).
    k = Z.shape[1]
    w = np.full(k, 1.0 / k)
    # Lipschitz-based step: 1/||Z||^2 (largest singular value squared)
    L = np.linalg.norm(Z, 2) ** 2 + 1e-9
    lr = 1.0 / L
    for _ in range(iters):
        r = Z @ w - target
        grad = Z.T @ r
        w = _proj_simplex(w - lr * grad)
    return w

def _proj_simplex(v):
    u = np.sort(v)[::-1]
    css = np.cumsum(u)
    rho_idx = np.nonzero(u * np.arange(1, len(u) + 1) > (css - 1))[0]
    if len(rho_idx) == 0:
        return np.full_like(v, 1.0 / len(v))
    r = rho_idx[-1]
    theta = (css[r] - 1) / (r + 1.0)
    return np.maximum(v - theta, 0)

# ---- Run replications ----
treated_idx = np.array([0])   # one fixed treated unit

did_cover = 0
did_widths = []
did_ests = []
sc_cover = 0
sc_widths = []
sc_ests = []
did_abs = []
sc_abs = []

for r in range(REPS):
    y = gen_panel()
    att_did, lo, hi = did_estimate(y, treated_idx)
    if lo <= TRUE_EFFECT <= hi:
        did_cover += 1
    did_widths.append(hi - lo)
    did_ests.append(att_did)
    did_abs.append(abs(att_did - TRUE_EFFECT))

    att_sc, slo, shi, _ = synthetic_control(y, treated_idx)
    if slo <= TRUE_EFFECT <= shi:
        sc_cover += 1
    sc_widths.append(shi - slo)
    sc_ests.append(att_sc)
    sc_abs.append(abs(att_sc - TRUE_EFFECT))

did_ests = np.array(did_ests)
sc_ests = np.array(sc_ests)

print("=== Alvarez & Ferman (2020) replication ===")
print(f"N={N} units, T={T} (T0={T0} pre), treated={N_TREAT}, rho={rho}, reps={REPS}, true effect={TRUE_EFFECT}")
print()
print(f"DiD  95% CI coverage : {did_cover/REPS:.3f}   (nominal 0.95)")
print(f"SC   95% CI coverage : {sc_cover/REPS:.3f}   (nominal 0.95)")
print()
print(f"DiD  estimate RMSE   : {np.sqrt(np.mean((did_ests-TRUE_EFFECT)**2)):.3f}")
print(f"SC   estimate RMSE   : {np.sqrt(np.mean((sc_ests-TRUE_EFFECT)**2)):.3f}")
print(f"DiD  mean |bias|     : {np.mean(did_abs):.3f}")
print(f"SC   mean |bias|     : {np.mean(sc_abs):.3f}")
print()
print(f"DiD  mean CI width   : {np.mean(did_widths):.3f}")
print(f"SC   mean CI width   : {np.mean(sc_widths):.3f}")
print()
did_under = (did_cover/REPS) < 0.90
sc_better = (sc_cover/REPS) > (did_cover/REPS) + 0.03
print(f"DiD under-covers (<0.90)? {did_under}")
print(f"SC coverage materially better than DiD? {sc_better}")
print(f"SC RMSE <= DiD RMSE? {np.sqrt(np.mean((sc_ests)**2)) <= np.sqrt(np.mean((did_ests)**2))}")
