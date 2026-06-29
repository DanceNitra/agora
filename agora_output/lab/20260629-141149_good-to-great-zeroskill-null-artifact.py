"""Artifact-Debunk (Crucible): "Good to Great" (Jim Collins, 2001) — do the 11 companies' shared
traits + sustained greatness require skill, or does a ZERO-SKILL null reproduce the pattern?

Null model (skill switched OFF): N firms as geometric random walks with IDENTICAL drift+vol (no firm
is better than any other). Apply Collins' selection on the dependent variable: ~mediocre for 15y, then
>=3x the market over the next 15y ('the leap'). Then measure, with pre-registered predictions:
  (1) FORWARD COLLAPSE (RTM): roll the selected cohort forward 15y -> mean EXCESS return vs market.
      If artifact: reverts to ~0 (matches real post-2001 underperformance: Circuit City, Fannie Mae...).
  (2) TRAIT RETROFIT: assign K candidate binary 'traits' at realistic prevalence; how many are shared
      by ALL selected firms purely by chance (Texas-sharpshooter over a trait space)?
FALSIFIER (claim is NOT an artifact): forward mean excess of the selected cohort is significantly
POSITIVE (skill would persist) -> then the null fails to reproduce sustained greatness.
Honest scope: shows the EVIDENCE cannot separate skill from luck+selection, NOT that skill is zero.
Prior art credited: Rosenzweig 'The Halo Effect' (2007), Levitt. Novelty = the runnable two-part null.
Pure numpy, cloud-free.
"""
import numpy as np

def run(seed=0, N=1400, mu=0.006, sigma=0.06,
        mo_prior=180, mo_trans=180, mo_fwd=180,
        leap_mult=3.0, mediocre_band=(0.5, 1.5), K_traits=60, trait_prev=0.6):
    rng = np.random.default_rng(seed)
    total = mo_prior + mo_trans + mo_fwd
    r = rng.normal(mu, sigma, size=(N, total))          # iid log-returns, IDENTICAL params -> no skill
    def cumret(a):                                       # cumulative simple return over a window
        return np.exp(a.sum(axis=1)) - 1.0
    prior = cumret(r[:, :mo_prior])
    trans = cumret(r[:, mo_prior:mo_prior + mo_trans])
    fwd   = cumret(r[:, mo_prior + mo_trans:])
    mkt_prior, mkt_trans, mkt_fwd = prior.mean(), trans.mean(), fwd.mean()
    # Collins selection on the DEPENDENT variable: mediocre prior, then >= leap_mult x market in transition
    mediocre = (prior >= mediocre_band[0] * mkt_prior) & (prior <= mediocre_band[1] * mkt_prior)
    leaped   = trans >= leap_mult * mkt_trans
    sel = np.where(mediocre & leaped)[0]
    n_sel = len(sel)
    out = {"seed": seed, "n_firms": N, "n_selected": int(n_sel)}
    if n_sel == 0:
        out["note"] = "no selection this seed"; return out
    # transition-window 'greatness' (by construction huge) and forward EXCESS (the test)
    out["sel_trans_excess_mult"] = float(np.mean(trans[sel] + 1) / (mkt_trans + 1))
    out["sel_fwd_excess"] = float(np.mean(fwd[sel] - mkt_fwd))     # RTM prediction: ~0
    out["all_fwd_excess"] = float(np.mean(fwd - mkt_fwd))          # ~0 (sanity)
    rand11 = rng.choice(N, size=min(11, N), replace=False)
    out["rand_fwd_excess"] = float(np.mean(fwd[rand11] - mkt_fwd))
    # trait retrofit: K candidate binary traits at prevalence trait_prev; how many shared by ALL selected?
    traits = rng.random((N, K_traits)) < trait_prev
    shared_all = int(np.sum(traits[sel].all(axis=0)))             # traits present in EVERY selected firm
    out["traits_shared_by_all_selected"] = shared_all
    out["traits_K"] = K_traits
    return out


def main():
    import statistics as st
    def ci(a):
        a = sorted(a); n = len(a); return (round(a[int(0.025*n)], 4), round(a[int(0.975*n)], 4))

    print("=== Good-to-Great zero-skill null (Monte Carlo, 200 seeds/setting) ===")
    print("CLAIM under test: the 11 firms' 15y 'leap' to >=3x market reflects discoverable skill/traits.")
    print("NULL: every firm has IDENTICAL drift+vol (zero skill). Select on the dependent variable")
    print("(mediocre 15y, then >=Nx market 15y), then measure the NEXT 15y excess return.\n")
    print(" leap | firms/run | transition greatness | FORWARD excess (mean) | 95% CI            | %% runs fwd>0")
    rows = []
    for leap in (3.0, 4.0, 5.0):
        res = [run(s, leap_mult=leap) for s in range(200)]
        res = [x for x in res if x.get("n_selected", 0) > 0]
        nsel = [x["n_selected"] for x in res]
        trans = [x["sel_trans_excess_mult"] for x in res]
        fwd = [x["sel_fwd_excess"] for x in res]
        pos = 100.0 * sum(1 for x in fwd if x > 0) / len(fwd)
        rows.append((leap, st.median(nsel), st.mean(trans), st.mean(fwd), ci(fwd), pos))
        print("  %.0fx | %9.0f | %17.2fx | %21.4f | %-16s | %5.0f%%" % (
            leap, st.median(nsel), st.mean(trans), st.mean(fwd), str(ci(fwd)), pos))
    # sanity: all-firms forward excess ~0
    base = [run(s)["all_fwd_excess"] for s in range(200)]
    print("\nsanity — all-firms forward excess (no selection): mean %.5f" % st.mean(base))
    # verdict on the headline 3x setting
    leap, nf, tr, fwd_mean, (lo, hi), pos = rows[0]
    artifact = lo <= 0 <= hi
    print("\nMEASURED (3x setting): a ZERO-SKILL null reproduces a ~%.0f-firm good-to-great cohort, each "
          "~%.1fx the market over the selection window, whose NEXT-15y excess return then reverts to "
          "%.3f (95%% CI %s), with only %.0f%% of cohorts beating the market forward (~coin flip)." % (
          nf, tr, fwd_mean, str((lo, hi)), pos))
    print("VERDICT:", "FAILED — 'sustained greatness' is reproduced from selection-on-the-dependent-variable + "
          "regression to the mean with NO skill; matches the real post-2001 collapse of Collins' picks "
          "(Circuit City bankrupt, Fannie Mae bailed out). Scope: the evidence cannot separate skill from "
          "luck+selection (NOT that skill is literally zero). Prior art: Rosenzweig (Halo Effect), Levitt."
          if artifact else "NOT an artifact — forward excess stays significantly positive.")


if __name__ == "__main__":
    main()
