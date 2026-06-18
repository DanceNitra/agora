"""
Challenge belief (inbox 44c469): "synthetic control (SC) restores honest CI coverage for one treated
unit (0.31 DiD -> 0.89 SC)". The belief's strongest claim is SC's honest INFERENCE. Disconfirming
hypothesis: SC's coverage advantage has an UNSTATED condition — the treated unit must lie inside the
donor convex hull. When the treated unit is an OUTLIER outside the hull, SC must EXTRAPOLATE (it cannot
form a convex match), so interpolation bias inflates the estimated effect while the placebo distribution
(donor-on-donor, all interior) stays tight -> SC falsely flags a zero effect as significant -> its
coverage COLLAPSES too. If so, the belief needs a condition (c): treated within the donor hull.

Factor model: y_it = lambda_i . F_t + eps_it (K=2 factors). True treatment effect = 0, so a correct
95% test should cover 0 ~95% of the time. SC weights = simplex-constrained LS on the pre-period
(numpy-only projected-gradient). Inference = Abadie placebo: the treated effect is 'significant' iff
|effect_treated| exceeds the 95th percentile of |placebo effects| (each donor treated in turn).
Coverage = P(NOT flagged significant) under the true null.
"""
import numpy as np

def simplex_proj(v):
    """Euclidean projection of v onto the probability simplex (Wang & Carreira-Perpinan)."""
    u = np.sort(v)[::-1]
    css = np.cumsum(u) - 1.0
    rho = np.nonzero(u - css / (np.arange(len(v)) + 1) > 0)[0][-1]
    theta = css[rho] / (rho + 1.0)
    return np.maximum(v - theta, 0.0)

def sc_weights(Y_pre_donors, y_pre_treated, iters=400, lr=0.05):
    """Simplex-constrained least squares: min ||y_treated - Y_donors w||, w in simplex."""
    m = Y_pre_donors.shape[1]
    w = np.full(m, 1.0 / m)
    A = Y_pre_donors
    for _ in range(iters):
        grad = A.T @ (A @ w - y_pre_treated)
        w = simplex_proj(w - lr * grad)
    return w

def sc_effect(Y_pre, Y_post, y_pre_t, y_post_t):
    w = sc_weights(Y_pre, y_pre_t)
    synth_post = Y_post @ w
    return float(np.mean(y_post_t - synth_post))

def one_sim(exterior, N=30, Tpre=20, Tpost=10, K=2, sigma=0.4, seed=0):
    rng = np.random.default_rng(abs(seed) % (2**32))
    # STATIONARY AR(1) factors (phi=0.6): a good pre-period convex match predicts the post-period, so
    # the test isolates interpolation/extrapolation (hull) bias rather than random-walk post-divergence.
    T = Tpre + Tpost
    F = np.zeros((T, K)); phi = 0.6
    for t in range(1, T):
        F[t] = phi * F[t - 1] + np.sqrt(1 - phi**2) * rng.standard_normal(K)
    lam_d = rng.standard_normal((N, K))                                  # donor loadings (interior cloud)
    lam_t = (3.0 * np.ones(K) + 0.3 * rng.standard_normal(K)) if exterior else rng.standard_normal(K)
    def series(lam):
        return F @ lam + sigma * rng.standard_normal(Tpre + Tpost)
    Yd = np.array([series(lam_d[i]) for i in range(N)])                  # N x T
    yt = series(lam_t)                                                   # treated, TRUE effect = 0
    Ypre, Ypost = Yd[:, :Tpre].T, Yd[:, Tpre:].T                         # Tpre x N , Tpost x N
    eff_t = sc_effect(Ypre, Ypost, yt[:Tpre], yt[Tpre:])
    # placebo: each donor treated in turn, fit SC on the OTHER donors
    plac = []
    for j in range(N):
        idx = [k for k in range(N) if k != j]
        eff_j = sc_effect(Yd[idx][:, :Tpre].T, Yd[idx][:, Tpre:].T, Yd[j, :Tpre], Yd[j, Tpre:])
        plac.append(abs(eff_j))
    thresh = np.percentile(plac, 95)
    flagged = abs(eff_t) > thresh                                        # false positive (true effect=0)
    return (not flagged), abs(eff_t), thresh

def coverage(exterior, sims=200, seed0=0):
    res = [one_sim(exterior, seed=seed0 + s) for s in range(sims)]
    cov = np.mean([r[0] for r in res])
    mean_eff = np.mean([r[1] for r in res]); mean_thr = np.mean([r[2] for r in res])
    return cov, mean_eff, mean_thr

if __name__ == "__main__":
    print("SC honest-coverage challenge: treated INSIDE vs OUTSIDE the donor convex hull (true effect=0).")
    print("A correct 95% test covers ~0.95. Belief claims SC restores honest coverage; does it hold off-hull?\n")
    ci, ei, ti = coverage(exterior=False)
    ce, ee, te = coverage(exterior=True)
    print(f"  treated INTERIOR to donor hull : SC coverage = {ci:.2f}  (|effect|~{ei:.2f} vs placebo-95 thr {ti:.2f})")
    print(f"  treated EXTERIOR (outlier)     : SC coverage = {ce:.2f}  (|effect|~{ee:.2f} vs placebo-95 thr {te:.2f})")
    print("\n=== VERDICT ===")
    interior_ok = ci >= 0.80                       # belief's honest-coverage claim holds in-hull
    collapses = ce < ci - 0.15                      # coverage materially worse off-hull
    print(f"belief holds when treated is INTERIOR (coverage >= 0.80): {interior_ok}")
    print(f"coverage COLLAPSES when treated is an outlier off the hull: {collapses}")
    if interior_ok and collapses:
        print("\nCHALLENGE PARTIALLY CONFIRMED -> belief REFINED, not retired:")
        print("SC's honest-coverage advantage is REAL but CONDITIONAL on the treated unit lying within the")
        print("donor convex hull. For an outlier treated unit SC must extrapolate; interpolation bias inflates")
        print("the effect beyond the (interior) placebo distribution and SC FALSELY flags a null effect as")
        print("significant -> coverage collapses. Add condition (c) to the rule: 'and the treated unit lies")
        print("within the donor convex hull (diagnosable: can the pre-period be matched with convex weights?)'.")
    elif interior_ok and not collapses:
        print("\nCHALLENGE FAILED -> belief STRENGTHENED: SC coverage holds even for an outlier treated unit.")
    else:
        print("\nUNEXPECTED: belief's interior coverage claim itself did not hold here -- investigate setup.")
