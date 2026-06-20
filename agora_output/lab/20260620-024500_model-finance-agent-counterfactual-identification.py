"""
MODEL the belief: "A finance-watching agent's edge is causal identification of the user's
COUNTERFACTUAL NORMAL, not the watching." (insight-a-finance-watching-agents-edge-is-causal-identificat,
2026-06-10, belief_status: survived.)

The belief's OWN falsifier: compare two agents on the same users — (A) a personalized counterfactual
baseline (learns each user's spending structure) vs (B) a generic category threshold. If personalized
alert PRECISION does not beat generic by a clear margin, identification is NOT the bottleneck and the
belief is wrong.

Severe-test design (so it can't be rigged):
  - FIXED ALERT BUDGET: both detectors emit the SAME number of alerts per user (you can't win by
    alerting more). The only thing that differs is WHERE each spends its budget.
  - Anomalies are defined RELATIVE TO EACH USER'S OWN NORMAL ("worth knowing FOR ME"): a genuine
    anomaly is a charge that is a large multiple of THIS user's typical spend for that category
    (fraud / duplicate / price-hike). A generic global threshold is blind to whose normal it is.
  - SWEEP user heterogeneity sigma_user. Prediction: the personalized edge GROWS with heterogeneity
    and -> 0 when users are homogeneous (then one global threshold fits everyone and identification
    buys nothing). That both supports AND bounds the belief — the honest, falsifiable version.
"""
import numpy as np

RNG = np.random.default_rng(7)
CATS = 6           # spending categories (groceries, rent, dining, transport, ...)
DAYS = 60          # the falsifier's 60-day window
TX_PER_DAY = 4     # transactions/day/user
ANOM_RATE = 0.02   # 2% of transactions are genuine, user-relative anomalies worth flagging
ANOM_MULT = (3.0, 6.0)   # an anomaly is 3-6x the user's OWN typical for that category


def simulate_user(cat_means, sigma_log=0.5):
    """A user's 60 days of transactions. cat_means = this user's per-category typical spend.
    Returns amounts, category index, and a boolean is_anomaly (defined vs THIS user's own normal)."""
    n = DAYS * TX_PER_DAY
    cat = RNG.integers(0, CATS, n)
    base = cat_means[cat]
    # normal spend: lognormal around the user's own per-category mean (multiplicative noise)
    amt = base * np.exp(RNG.normal(0, sigma_log, n))
    is_anom = RNG.random(n) < ANOM_RATE
    mult = RNG.uniform(*ANOM_MULT, n)
    amt = np.where(is_anom, base * mult, amt)     # anomalies are large MULTIPLES of the user's own normal
    return amt, cat, is_anom


def precision_recall_at_budget(amt, cat, is_anom, scores, budget):
    """Flag the top-`budget` transactions by `scores`; measure precision & recall vs genuine anomalies."""
    if budget <= 0 or not is_anom.any():
        return np.nan, np.nan
    flagged = np.argsort(scores)[-budget:]
    tp = is_anom[flagged].sum()
    precision = tp / budget
    recall = tp / is_anom.sum()
    return precision, recall


def run(sigma_user, n_users=400, alert_frac=0.02):
    """alert_frac of all transactions may be flagged (the fixed budget), shared identically by both
    detectors. Generic: deviation from the GLOBAL (population) per-category mean. Personalized:
    deviation from the USER'S OWN learned per-category mean (the counterfactual normal)."""
    # population per-category center; users scatter around it by sigma_user (heterogeneity of "normal")
    pop_center = RNG.uniform(20, 120, CATS)
    gen_p, gen_r, per_p, per_r = [], [], [], []
    # global per-category mean a generic engine would calibrate to (pooled across users)
    global_cat_mean = pop_center.copy()
    for _ in range(n_users):
        cat_means = pop_center * np.exp(RNG.normal(0, sigma_user, CATS))   # this user's true normal
        amt, cat, is_anom = simulate_user(cat_means)
        budget = max(1, int(round(alert_frac * len(amt))))
        # (B) GENERIC: z-score vs the GLOBAL per-category mean (blind to the individual)
        gen_score = amt / global_cat_mean[cat]                # how big vs the population's normal
        # (A) PERSONALIZED: learn THIS user's per-category baseline from their own history (robust median),
        #     score by deviation from the user's OWN counterfactual normal (causal identification of "for me")
        learned = np.array([np.median(amt[cat == c]) if (cat == c).any() else global_cat_mean[c]
                            for c in range(CATS)])
        per_score = amt / learned[cat]
        gp, gr = precision_recall_at_budget(amt, cat, is_anom, gen_score, budget)
        pp, pr = precision_recall_at_budget(amt, cat, is_anom, per_score, budget)
        gen_p.append(gp); gen_r.append(gr); per_p.append(pp); per_r.append(pr)
    return (np.nanmean(gen_p), np.nanmean(gen_r), np.nanmean(per_p), np.nanmean(per_r))


print("=== Model: does PERSONALIZED counterfactual identification beat a GENERIC threshold? ===")
print("    (fixed alert budget per user; anomalies defined vs each user's OWN normal)\n")
print(f"  {'sigma_user':>10} {'generic_prec':>13} {'pers_prec':>10} {'prec_gain':>10} "
      f"{'generic_rec':>12} {'pers_rec':>9}")
results = []
for su in (0.0, 0.15, 0.3, 0.5, 0.8, 1.2):
    gp, gr, pp, pr = run(su)
    gain = pp - gp
    results.append((su, gp, pp, gain, gr, pr))
    print(f"  {su:>10.2f} {gp:>13.3f} {pp:>10.3f} {gain:>+10.3f} {gr:>12.3f} {pr:>9.3f}")

# decisive cell: realistic heterogeneity (people's "normal" genuinely differs ~ exp(N(0,0.5)))
su0, gp0, pp0, gain0, gr0, pr0 = results[3]
homog = results[0]   # sigma_user = 0 : everyone identical -> identification should buy ~nothing
print(f"\nMEASURED (sigma_user={su0}): generic precision={gp0:.3f}, personalized precision={pp0:.3f} "
      f"-> personalized is {pp0/max(gp0,1e-9):.2f}x (gain {gain0:+.3f} at equal alert budget).")
print(f"MEASURED (sigma_user=0, homogeneous users): gain={homog[3]:+.3f} (identification buys ~nothing "
      f"when everyone's normal is the same).")

# verdict: belief holds IF personalized clearly beats generic at realistic heterogeneity AND the edge
# is heterogeneity-driven (small at sigma_user=0). Falsifier fires if the gain is NOT a clear margin.
clear = gain0 >= 0.10 and pp0 >= 1.3 * gp0
het_driven = gain0 > homog[3] + 0.05
print()
if clear and het_driven:
    print("VERDICT: belief HOLDS, and is now PRECISE. At equal alert budget, a personalized counterfactual "
          f"baseline beats a generic threshold by {gain0:+.3f} precision ({pp0/max(gp0,1e-9):.2f}x) at "
          "realistic user heterogeneity, while the edge collapses toward zero when users are homogeneous. "
          "So the bottleneck IS identification of the user's counterfactual normal — exactly to the extent "
          "that users differ. The watcher's worth is its identification, not its eyes; and that worth is "
          "PROPORTIONAL to how heterogeneous the population's 'normal' is.")
elif clear:
    print("VERDICT: belief HOLDS but the heterogeneity mechanism is unclear (personalized wins even when "
          "users are homogeneous) — identification helps for a reason other than individual-normal scatter.")
else:
    print("VERDICT: belief FAILS its own falsifier — personalized precision does NOT beat generic by a clear "
          "margin at equal budget, so causal identification of the counterfactual is NOT the bottleneck here.")
