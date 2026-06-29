
import numpy as np, math
def norm_cdf(x): return 0.5*(1.0+math.erf(x/math.sqrt(2.0)))
def pooled_d(rng, n_per_group, n_studies, true_d, pub_filter=True):
    kd, ks, att, cap = [], [], 0, n_studies*500
    while len(kd) < n_studies and att < cap:
        att += 1
        se = math.sqrt(2.0/n_per_group)
        d_hat = rng.normal(true_d, se); z = d_hat/se
        p = 2.0*(1.0-norm_cdf(abs(z)))
        if (not pub_filter) or (p < 0.05 and d_hat > 0):
            kd.append(d_hat); ks.append(se)
    d = np.array(kd); se = np.array(ks); w = 1.0/se**2
    return float(np.sum(w*d)/np.sum(w)) if len(d) else float('nan')

# CLAIM under test (Mertens et al. 2021 PNAS): food-choice nudges ~2.5x more responsive than other domains.
# SEVERE TEST: can differential publication bias (food studies small-n vs other-domain large-n) manufacture
# the 2.5x RATIO from an IDENTICAL true effect across domains? Pre-registered falsifier: if ratio>=2.0 from
# zero true difference, the 2.5x is reproducible as an artifact => the domain claim is not robust (FAILED).
rng = np.random.default_rng(42)
TRUE_D, OTHER_N, N_STUDIES, REPS = 0.20, 300, 12, 400
def ratio(food_n, reps=REPS):
    rs=[pooled_d(rng,food_n,N_STUDIES,TRUE_D)/pooled_d(rng,OTHER_N,N_STUDIES,TRUE_D) for _ in range(reps)]
    return float(np.mean(rs))
main = ratio(30)
ctrl = ratio(300)  # equal n -> symmetric bias -> ratio ~1.0 (sim validity check)
sweep = {fn: round(ratio(fn),2) for fn in [300,100,60,30,20]}
print("TRUE between-domain ratio = 1.00 (identical true effect d=%.2f in every domain)" % TRUE_D)
print("OBSERVED food/other ratio @ food_n=30 vs other_n=300:", round(main,2))
print("CONTROL (equal n=300 both): %.2f  (expect ~1.0)" % ctrl)
print("SENSITIVITY food_n->ratio:", sweep)
verdict = "FAILED" if main>=2.0 and abs(ctrl-1.0)<0.1 else "PARTIAL"
print("MEASURED: %.2fx domain ratio reproduced from ZERO true difference via pub-bias x small-study; "
      "claimed 'up to 2.5x'. VERDICT(mechanism): %s. (cf. Maier et al. 2022 PNAS, real-data critique)" % (main, verdict))
