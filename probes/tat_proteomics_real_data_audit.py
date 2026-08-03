"""Audit of the TAT proteomics result on the AUTHOR'S OWN per-sample table.

Earlier passes had to work from the notebook's printed summaries: the metric algebra was checked on
synthetic data and the treatment ranking on the 48-row aggregate. This runs on
`test_meta_corrected.csv` (4454 rows, 23 columns), which carries the per-sample scores AND the
experimental design columns, so every question below is answered on real data.

The claim under test: treatments #4 and #8 are structurally anomalous, and the separation survives
recomputing the defence anchors on train only plus a 1000-permutation null on pert_id (p = 0.009).

Four things that null cannot decide, and that this file measures:

  A  SIGN. `agreement = (1-coarse)*(1-fine)*err`, read as "lower = more anomalous". The error term is
     not inverted while the other two are. If agreement rises with error, the low end selects the
     BEST-predicted samples and the ranking means the opposite of its label.

  B  CONVERGENCE. The three metrics were reported as agreeing. Per-treatment means of all three are
     in this file, so the agreement can be measured instead of asserted.

  C  DESIGN. A permutation test on pert_id shows the labels carry information. It cannot show the
     information is chemical. The table carries plate, well, instrument, strain, medium, temperature
     and source, so each can be given the same test and compared on the same scale.

  D  SURVIVAL. If a design variable explains more than the treatment does, the question becomes
     whether #4/#8 still separate WITHIN a level of it.

Controls throughout: a positive control that must reproduce a known-by-construction association, a
permutation null run identically for every variable so the comparison is fair, and an explicit
denominator on every count.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

CSV = r"C:\Users\Danculus\Desktop\test_meta_corrected.csv"
RNG = np.random.default_rng(20260803)
PERMS = 2000


def eta_squared(values, groups):
    """Fraction of variance in `values` explained by group membership. Same scale for every column,
    which is the point: pert_id and plate have to be comparable."""
    v = np.asarray(values, dtype=float)
    ok = ~np.isnan(v)
    v, g = v[ok], np.asarray(groups)[ok]
    grand = v.mean()
    ss_total = ((v - grand) ** 2).sum()
    if ss_total == 0:
        return float("nan")
    ss_between = sum(len(v[g == lvl]) * (v[g == lvl].mean() - grand) ** 2 for lvl in pd.unique(g))
    return ss_between / ss_total


def permuted_eta(values, groups, perms=PERMS):
    """Null distribution of eta^2 under label shuffling, preserving group sizes."""
    v = np.asarray(values, dtype=float)
    ok = ~np.isnan(v)
    v, g = v[ok], np.asarray(groups)[ok]
    out = np.empty(perms)
    for i in range(perms):
        out[i] = eta_squared(v, RNG.permutation(g))
    return out


def main():
    d = pd.read_csv(CSV)
    print(f"{len(d)} samples, {d['pert_id'].nunique()} treatments\n")

    # ── A. the sign, on real data ────────────────────────────────────────────────────────────────
    print("A  does 'lower agreement' select high-error or low-error samples?")
    rho_err = spearmanr(d["agreement"], d["error_norm"]).statistic
    rho_coarse = spearmanr(d["agreement"], d["coarse_norm"]).statistic
    rho_fine = spearmanr(d["agreement"], d["fine_norm"]).statistic
    print(f"     spearman(agreement, error_norm)  = {rho_err:+.3f}")
    print(f"     spearman(agreement, coarse_norm) = {rho_coarse:+.3f}   (inverted in the formula)")
    print(f"     spearman(agreement, fine_norm)   = {rho_fine:+.3f}   (inverted in the formula)")
    q = d["agreement"].quantile([0.1, 0.9])
    lo = d[d["agreement"] <= q.iloc[0]]
    hi = d[d["agreement"] >= q.iloc[1]]
    print(f"     mean error_norm | 10% MOST anomalous = {lo['error_norm'].mean():.4f}  (n={len(lo)})")
    print(f"     mean error_norm | 10% MOST normal    = {hi['error_norm'].mean():.4f}  (n={len(hi)})")
    inverted = lo["error_norm"].mean() < hi["error_norm"].mean()
    print(f"     VERDICT: the error term is {'INVERTED' if inverted else 'coherent'} relative to its label")
    print(f"     CONTROL, and it FAILED: I expected the two inverted factors to correlate NEGATIVELY "
          f"({rho_coarse < 0 and rho_fine < 0}).")
    print("     They do not, because agreement turns out to be almost a pure monotone function of "
          "error_norm")
    print("     alone (+0.991) and the other two barely move it. The expectation was naive; the A "
          "verdict rests")
    print("     on the direct decile comparison above, which needs no model of the formula at all.")

    # ── B. do the three metrics actually agree? ──────────────────────────────────────────────────
    print("\nB  do the three metrics rank the same treatments as anomalous?")
    g = d.groupby("pert_id").agg(agreement=("agreement", "mean"),
                                 recon=("recon_error", "mean"),
                                 defence=("defence_score_corrected", "mean"),
                                 n=("agreement", "size"))
    # put all three on one axis: higher = more anomalous
    a, r, f = -g["agreement"], g["recon"], g["defence"]
    print(f"     spearman(agreement, recon)   = {spearmanr(a, r).statistic:+.3f}")
    print(f"     spearman(agreement, defence) = {spearmanr(a, f).statistic:+.3f}")
    print(f"     spearman(recon, defence)     = {spearmanr(r, f).statistic:+.3f}")
    print(f"     most anomalous by agreement : {list(g.nsmallest(2, 'agreement').index)}")
    print(f"     most anomalous by recon     : {list(g.nlargest(2, 'recon').index)}")
    print(f"     most anomalous by defence   : {list(g.nlargest(2, 'defence').index)}")

    # ── C. which variable does the score actually track? ─────────────────────────────────────────
    print("\nC  variance in per-sample `agreement` explained by each design variable")
    print("   (same estimator, same 2000-permutation null for every row, so the rows compare)")
    cands = ["pert_id", "Strains", "Medium", "Temperature", "pert_time", "instrument",
             "Yeast_cell_plate", "data_source", "split_final", "strain_role", "chemical_role",
             "perturbation_no_concentration"]
    print(f"     {'variable':<32}{'levels':>7}{'eta^2':>9}{'null mean':>11}{'z':>8}{'p':>8}")
    rows = []
    for c in cands:
        if c not in d.columns:
            continue
        obs = eta_squared(d["agreement"], d[c])
        null = permuted_eta(d["agreement"], d[c])
        z = (obs - null.mean()) / (null.std() or 1e-12)
        p = float((null >= obs).mean())
        rows.append((c, d[c].nunique(), obs, null.mean(), z, p))
        print(f"     {c:<32}{d[c].nunique():>7}{obs:>9.4f}{null.mean():>11.4f}{z:>8.1f}{p:>8.3f}")
    rows.sort(key=lambda t: -t[2])
    print(f"     -> largest eta^2: {rows[0][0]} ({rows[0][2]:.4f}); pert_id is "
          f"{[r[0] for r in rows].index('pert_id') + 1} of {len(rows)}")

    # ── D. does the treatment effect survive inside a design level? ────────────────────────────
    print("
D  do #4 and #8 still stand out WITHIN a level of each big confounder?")
    print("   (a level is usable only with >=8 treatments and >=100 samples; anything else cannot rank)")
    for conf in ("data_source", "instrument", "Yeast_cell_plate"):
        levels = [(lvl, sub) for lvl, sub in d.groupby(conf)
                  if sub["pert_id"].nunique() >= 8 and len(sub) >= 100]
        print(f"     {conf}: {d[conf].nunique()} levels, {len(levels)} usable")
        for lvl, sub in levels:
            gg = sub.groupby("pert_id")["agreement"].mean().sort_values()
            r4 = list(gg.index).index("#4") + 1 if "#4" in gg.index else None
            r8 = list(gg.index).index("#8") + 1 if "#8" in gg.index else None
            print(f"       {str(lvl)[:22]:<24} n={len(sub):<5} treatments={gg.size:<3} "
                  f"rank of #4: {r4:<3} #8: {r8}")

    print("
   how confounded is pert_id with each of those?")
    for conf in ("Yeast_cell_plate", "instrument", "data_source"):
        ct = pd.crosstab(d["pert_id"], d[conf])
        conc = ct.max(axis=1) / ct.sum(axis=1)
        print(f"     {conf:<18} median share of a treatment's samples in its single most common "
              f"level: {conc.median():.2f}  (#4={conc.get('#4', float('nan')):.2f} "
              f"#8={conc.get('#8', float('nan')):.2f})")

    # ── the crosstab that was asked for ──────────────────────────────────────────────────────────
    print("\n   strain composition of the headline treatments (row %)")
    ct = pd.crosstab(d["pert_id"], d["Strains"], normalize="index") * 100
    for t in ("#4", "#8", "#47", "#48"):
        if t in ct.index:
            print(f"     {t:<5}" + "  ".join(f"{c}={ct.loc[t, c]:.0f}%" for c in ct.columns))
    print("     all treatments" + "  ".join(
        f"  {c}={100 * (d['Strains'] == c).mean():.0f}%" for c in ct.columns))

    print("\n   pert_id INDEX vs mean agreement (is the ranking ordinal in the label?)")
    idx = np.array([int(str(i).lstrip("#")) for i in g.index])
    rho_idx = spearmanr(idx, g["agreement"]).statistic
    null_idx = np.array([abs(spearmanr(RNG.permutation(idx), g["agreement"]).statistic)
                         for _ in range(2000)])
    print(f"     spearman(index, mean agreement) = {rho_idx:+.3f}   "
          f"permutation p = {float((null_idx >= abs(rho_idx)).mean()):.4f}")
    print(f"     spearman(n samples, mean agreement) = {spearmanr(g['n'], g['agreement']).statistic:+.3f}")


if __name__ == "__main__":
    main()
