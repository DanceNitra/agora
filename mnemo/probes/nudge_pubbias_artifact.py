"""Food-nudge "2.5x more responsive" — a publication-bias artifact, reproduced.

Public probe for the Crucible null-result "Food nudges aren't 2.5x better — it's publication bias"
(dancenitra.github.io/agora/public/posts/food-nudges-publication-bias.html).

CLAIM under test (Mertens, Herberz, Hahnel & Brosch 2021, PNAS, doi:10.1073/pnas.2107346118): pooled
across hundreds of nudge studies, the food/dietary domain is the most responsive to choice architecture —
the headline that travelled as "food nudges are ~2.5x more responsive than other domains".

SEVERE TEST (mechanism replication, NOT a re-analysis of their dataset): give EVERY domain the IDENTICAL
true effect (Cohen's d = 0.20). Make the "food" domain out of SMALL studies (per-group n~30, like cafeteria
field trials) and the "other" domain out of LARGE studies (n~300, like default-enrollment / tax-letter
studies). Keep a study only if it clears the standard file-drawer filter (p < .05, expected direction).
Because a significance filter inflates SMALL studies more (they only clear the bar when their estimate is
large), a domain made of small studies is systematically inflated relative to one made of large studies —
even with ZERO true between-domain difference. Read the observed food/other ratio.

HONEST SCOPE: this shows the between-domain RANKING is *reproducible from no true difference*, i.e. it is not
robust evidence of an intrinsic "food is more nudgeable" property. It does NOT claim nudges have zero effect,
and it is not their exact estimate (we don't have their per-study data). It lines up with the real-data
publication-bias re-analysis of this same meta-analysis by Maier, Bartos, Stanley, Shanks, Harris &
Wagenmakers (2022, PNAS, doi:10.1073/pnas.2200300119). Differential small-study effects / publication bias
are textbook (Egger 1997; Stanley & Doucouliagos PET-PEESE 2014) — the contribution here is only the small
runnable receipt that the *specific 2.5x domain ratio* falls out of a realistic ~10x size asymmetry.

Each printed number seeds its own RNG, so it reproduces independently of call order.
Runnable, deterministic (fixed seeds; needs numpy):  python nudge_pubbias_artifact.py
MIT-licensed. Part of Agora / mnemo (https://github.com/DanceNitra/agora/tree/main/mnemo).
"""
import math
import numpy as np

TRUE_D = 0.20      # identical true effect in EVERY domain (Cohen's d)
OTHER_N = 300      # "other domain" per-group sample size (large studies)
N_STUDIES = 12     # published studies pooled per domain
REPS = 400         # Monte-Carlo repetitions
SEED = 42


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def pooled_d(rng, n_per_group, true_d=TRUE_D, n_studies=N_STUDIES, pub_filter=True):
    """Inverse-variance-weighted pooled effect over `n_studies` studies that SURVIVE the file-drawer
    filter (p < .05 in the expected direction). Each study draws d_hat ~ N(true_d, se), se = sqrt(2/n)."""
    kept_d, kept_se, attempts, cap = [], [], 0, n_studies * 500
    while len(kept_d) < n_studies and attempts < cap:
        attempts += 1
        se = math.sqrt(2.0 / n_per_group)
        d_hat = rng.normal(true_d, se)
        z = d_hat / se
        p = 2.0 * (1.0 - _norm_cdf(abs(z)))
        if (not pub_filter) or (p < 0.05 and d_hat > 0):
            kept_d.append(d_hat)
            kept_se.append(se)
    d = np.array(kept_d); se = np.array(kept_se); w = 1.0 / se ** 2
    return float(np.sum(w * d) / np.sum(w)) if len(d) else float("nan")


def mean_pooled(n, reps=REPS):
    rng = np.random.default_rng(SEED + n)          # own seed -> order-independent
    return float(np.mean([pooled_d(rng, n) for _ in range(reps)]))


def mean_ratio(food_n, reps=REPS):
    rng = np.random.default_rng(SEED + food_n)     # own seed -> order-independent
    return float(np.mean([pooled_d(rng, food_n) / pooled_d(rng, OTHER_N) for _ in range(reps)]))


def main():
    food_pooled = mean_pooled(30)
    other_pooled = mean_pooled(OTHER_N)
    main_ratio = mean_ratio(30)
    control = mean_ratio(OTHER_N)   # equal n both domains -> symmetric bias -> ratio ~1.0

    print(f"True between-domain ratio      = 1.00   (identical true effect d={TRUE_D} in every domain)")
    print(f"Pooled 'food'  effect (n=30)   = {food_pooled:.2f}   (true 0.20, inflated by the filter)")
    print(f"Pooled 'other' effect (n=300)  = {other_pooled:.2f}   (true 0.20, barely inflated)")
    print(f"Observed food/other ratio      = {main_ratio:.2f}x  (food n=30 vs other n=300, ~10x asymmetry)")
    print(f"CONTROL (equal n=300 both)     = {control:.2f}   (expect ~1.0 -> the artifact is the SIZE gap)")

    print("\nDose-response: food per-group n  ->  observed food/other ratio (true = 1.00)")
    for fn in (300, 150, 100, 60, 30, 20):
        print(f"   n={fn:<4d} -> {mean_ratio(fn):.2f}x")

    ok = main_ratio >= 2.0 and abs(control - 1.0) < 0.1
    print(f"\nVERDICT (mechanism): {'FAILED (the 2.5x is reproducible from ZERO true difference)' if ok else 'PARTIAL'}")
    print("The famous ~2.5x appears at a ~10x sample-size asymmetry (~30 vs ~300) -- exactly the gap between")
    print("cafeteria field trials and population-scale default studies. cf. Maier et al. 2022 PNAS (real data).")


if __name__ == "__main__":
    main()
