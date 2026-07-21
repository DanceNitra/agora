"""'Good to Great' — a zero-skill null reproduces the leap AND its forward collapse.

Public probe for the Crucible null-result "'Good to Great': a zero-skill null reproduces the leap"
(dancenitra.github.io/agora/public/posts/good-to-great-zero-skill-null.html).

CLAIM under test (Jim Collins, *Good to Great*, 2001): 11 companies leapt from mediocre to a 15-year run
beating the market ~3x, and shared management traits (Level 5 leadership, Hedgehog, Flywheel) are the
discoverable causes of that *sustained greatness*.

NULL (skill switched OFF): simulate N=1400 firms (~Collins' 1435 starting universe) as random walks with
IDENTICAL drift + volatility -- no firm is better than any other. Apply Collins' own selection on the
DEPENDENT variable (mediocre for 15y, then >= Nx the market over the next 15y = 'the leap'), then measure
the NEXT 15y excess return. Pre-registered predictions if it is an artifact: (1) FORWARD COLLAPSE -- the
selected cohort's forward excess reverts to ~0 (regression to the mean); (2) TRAIT RETROFIT -- with a space
of candidate binary 'traits', several are shared by ALL selected firms purely by chance (Texas-sharpshooter).
FALSIFIER: if the selected cohort's forward excess stayed significantly POSITIVE, skill would persist and the
null would fail to reproduce sustained greatness.

HONEST SCOPE: this shows the EVIDENCE (winners-only, traits retrofitted, no forward test) cannot separate
skill from luck + selection -- NOT that management skill is literally zero. The mechanism is textbook:
selection on the dependent variable + regression to the mean (Rosenzweig, *The Halo Effect* 2007; Denrell
2003 on selection bias in management research; Kahneman, *Thinking, Fast and Slow* 2011, discusses G2G and
the illusion of validity). The contribution here is only the runnable two-part null that reproduces the
cohort AND its forward collapse end to end, with no data and no tuning.

Deterministic (fixed seeds; needs numpy):  python good_to_great_null.py
MIT-licensed. Part of Agora / inspeximus (https://github.com/DanceNitra/agora/tree/main/inspeximus).
"""
import statistics as st
import numpy as np

N = 1400            # ~Collins' 1435-firm starting universe
MU, SIGMA = 0.006, 0.06
MONTHS = 180        # 15 years per window (prior / transition / forward)
SEEDS = 200


def run(seed, leap_mult=3.0, mediocre_band=(0.5, 1.5), K_traits=60, trait_prev=0.6):
    rng = np.random.default_rng(seed)
    r = rng.normal(MU, SIGMA, size=(N, 3 * MONTHS))          # iid returns, IDENTICAL params -> no skill
    def cumret(a):
        return np.exp(a.sum(axis=1)) - 1.0
    prior = cumret(r[:, :MONTHS])
    trans = cumret(r[:, MONTHS:2 * MONTHS])
    fwd = cumret(r[:, 2 * MONTHS:])
    mkt_prior, mkt_trans, mkt_fwd = prior.mean(), trans.mean(), fwd.mean()
    mediocre = (prior >= mediocre_band[0] * mkt_prior) & (prior <= mediocre_band[1] * mkt_prior)
    leaped = trans >= leap_mult * mkt_trans                   # Collins: >= leap_mult x market in transition
    sel = np.where(mediocre & leaped)[0]
    if len(sel) == 0:
        return None
    traits = rng.random((N, K_traits)) < trait_prev
    return {
        "n_selected": int(len(sel)),
        "sel_trans_mult": float(np.mean(trans[sel] + 1) / (mkt_trans + 1)),
        "sel_fwd_excess": float(np.mean(fwd[sel] - mkt_fwd)),   # RTM prediction: ~0
        "all_fwd_excess": float(np.mean(fwd - mkt_fwd)),        # sanity: ~0
        "frac_fwd_pos": float(np.mean(fwd[sel] > mkt_fwd)),     # share of selected firms that beat mkt fwd
        "traits_shared_by_all": int(np.sum(traits[sel].all(axis=0))),  # traits in EVERY selected firm by chance
        "K_traits": K_traits,
    }


def _ci(a):
    a = sorted(a); n = len(a)
    return (round(a[int(0.025 * n)], 4), round(a[int(0.975 * n)], 4))


def main():
    print("=== 'Good to Great' zero-skill null (Monte Carlo, %d seeds/setting) ===" % SEEDS)
    print("NULL: every firm has IDENTICAL drift+vol (zero skill). Select on the dependent variable")
    print("(mediocre 15y, then >=Nx market 15y), then measure the NEXT 15y excess return.\n")
    print(" leap | firms/run | selection-window greatness | FORWARD excess (mean) | 95% CI          | %cohorts fwd>0 | traits shared/60")
    rows = {}
    for leap in (3.0, 4.0, 5.0):
        res = [x for x in (run(s, leap_mult=leap) for s in range(SEEDS)) if x]
        nsel = st.median(x["n_selected"] for x in res)
        tr = st.mean(x["sel_trans_mult"] for x in res)
        fwd = [x["sel_fwd_excess"] for x in res]
        pos = 100.0 * sum(1 for x in fwd if x > 0) / len(fwd)
        traits = st.mean(x["traits_shared_by_all"] for x in res)
        rows[leap] = (nsel, tr, st.mean(fwd), _ci(fwd), pos, traits)
        print("  %.0fx | %9.0f | %24.2fx | %21.4f | %-15s | %11.0f%% | %8.1f" % (
            leap, nsel, tr, st.mean(fwd), str(_ci(fwd)), pos, traits))

    base = st.mean(run(s)["all_fwd_excess"] for s in range(SEEDS))
    print("\nsanity -- all-firms forward excess (no selection): mean %.5f" % base)

    nsel, tr, fwd_mean, (lo, hi), pos, traits = rows[3.0]
    artifact = lo <= 0 <= hi
    print("\nMEASURED (3x): a ZERO-SKILL null makes a ~%.0f-firm good-to-great cohort, each ~%.1fx the market" % (nsel, tr))
    print("in the selection window; its NEXT-15y excess reverts to %.3f (95%% CI %s), only %.0f%% beat the market" % (fwd_mean, (lo, hi), pos))
    print("forward (~coin flip); and ~%.0f of 60 candidate traits are shared by ALL selected firms by chance." % traits)
    print("VERDICT (mechanism):", "FAILED -- 'sustained greatness' is reproduced from selection-on-the-dependent-"
          "variable + regression to the mean with NO skill (matches the real post-2001 collapse: Circuit City "
          "bankrupt, Fannie Mae bailed out). Scope: the EVIDENCE can't separate skill from luck+selection."
          if artifact else "NOT an artifact -- forward excess stays significantly positive.")


if __name__ == "__main__":
    main()
