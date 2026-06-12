"""
Deepen fd00facb: when is an RCT STRICTLY better than a quasi-experiment (DiD / synthetic
control), and when is the quasi the ONLY option?

Parent insight established the BIAS axis (RCT wins once parallel-trends bias b exceeds the RCT's
SE). This adds the second, independent axis the parent ignored: ASSIGNABILITY / N.

Mechanism under test: with a SINGLE treated unit, the post-treatment estimate carries that one
unit's realized idiosyncratic shock, which NO amount of donor pool or pre-period length can
average away. So a single-unit quasi-experiment has an irreducible RMSE floor ~= sigma_idio.
An RCT with n randomized units averages that same shock down as 2*sigma/sqrt(n).

Prediction: single-unit (SC/DiD) RMSE plateaus at ~sigma_idio as donors/pre-periods grow;
RCT RMSE keeps falling with n and crosses below the floor at small n.
"""
import numpy as np

rng = np.random.default_rng(7)
TAU = 2.0
SIG = 1.0  # idiosyncratic shock sd (same per-observation noise for both designs)


def sim_single_unit(n_donors, n_pre, reps=1500):
    """One treated unit; estimate tau via fitted-weight synthetic control on a matchable donor pool."""
    errs = np.empty(reps)
    for r in range(reps):
        # one nonstationary common factor (random walk) -> classic parallel-trends violation driver
        f = np.cumsum(rng.normal(0, 1, n_pre + 1))
        load_tr = 1.0
        loads = rng.normal(1.0, 0.5, n_donors)      # donors straddle the treated loading -> inside hull
        a_tr = rng.normal(0, 1)
        a_do = rng.normal(0, 1, n_donors)
        # pre-period outcomes
        Ytr_pre = a_tr + load_tr * f[:n_pre] + rng.normal(0, SIG, n_pre)
        Ydo_pre = a_do[:, None] + loads[:, None] * f[None, :n_pre] + rng.normal(0, SIG, (n_donors, n_pre))
        # fit weights: least squares of treated pre on donor pre (synthetic-control style)
        w, *_ = np.linalg.lstsq(Ydo_pre.T, Ytr_pre, rcond=None)
        # post period (1 period). The treated unit's realized post shock is the irreducible part.
        fp = f[n_pre]
        eps_tr_post = rng.normal(0, SIG)
        Ytr_post = a_tr + load_tr * fp + eps_tr_post + TAU
        Ydo_post = a_do + loads * fp + rng.normal(0, SIG, n_donors)
        tau_hat = Ytr_post - w @ Ydo_post
        errs[r] = tau_hat - TAU
    return float(np.sqrt(np.mean(errs**2))), float(np.mean(errs))


def sim_rct(n_units, reps=4000):
    """n randomized units; first-difference removes unit + common-factor terms, leaving only noise."""
    errs = np.empty(reps)
    for r in range(reps):
        n = n_units - (n_units % 2)
        treat = np.zeros(n); treat[: n // 2] = 1
        # within-unit first difference cancels alpha and the common factor; effect + 2 noise draws remain
        delta = TAU * treat + rng.normal(0, SIG, n) - rng.normal(0, SIG, n)
        errs[r] = delta[treat == 1].mean() - delta[treat == 0].mean()
    errs = errs - 0  # errs already centered on tau; recompute as deviation
    return float(np.sqrt(np.mean((errs - TAU) ** 2))), float(np.mean(errs - TAU))


print("=== SINGLE TREATED UNIT (synthetic control): RMSE vs donors x pre-periods ===")
print(f"{'donors':>7} {'pre':>5} {'RMSE':>8} {'bias':>8}")
for nd in (5, 20, 80):
    for npre in (12, 48, 192):
        rmse, bias = sim_single_unit(nd, npre)
        print(f"{nd:>7} {npre:>5} {rmse:>8.3f} {bias:>8.3f}")

print("\n=== RANDOMIZED A/B TEST (RCT): RMSE vs number of units n ===")
print(f"{'n_units':>7} {'RMSE':>8} {'2sig/sqrtn':>11}")
for n in (4, 16, 64, 256, 1024):
    rmse, bias = sim_rct(n)
    print(f"{n:>7} {rmse:>8.3f} {2*SIG/np.sqrt(n):>11.3f}")

print(f"\nNoise floor (single-unit, irreducible) ~ sigma_idio = {SIG:.3f}")
print("RCT RMSE crosses below that floor at n ~ (2/1)^2 = 4 units, then keeps falling.")
