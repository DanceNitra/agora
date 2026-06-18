"""
Severe test of the insight "an A/B test beats a quasi-experiment by a BIAS threshold, not effect size."

The folk intuition: bigger treatment effects justify the expensive RCT. The claim under test: the
A/B-vs-quasi choice is decided by the quasi-method's BIAS vs the RCT's variance penalty, and is
INVARIANT to the true effect size. Mechanism: for an unbiased RCT estimate the error ~ N(0, var_rct)
and for the biased quasi estimate the error ~ N(bias, var_quasi); the true effect tau cancels out of
the error in BOTH, so the RMSE comparison cannot depend on tau. Falsifier: if the crossover moved
with tau, the claim is wrong.

A/B (RCT): treatment randomized (independent of the confounder), unbiased, but expensive -> small n.
Quasi: cheap observational data -> large n (lower variance), but treatment is confounded -> biased.
"""
import numpy as np

def run(n_rct=100, n_quasi=2000, sigma=1.0, gamma=1.0, seeds=500):
    taus = [0.1, 0.5, 1.0, 2.0, 5.0]
    confs = [0.0, 0.2, 0.4, 0.6, 0.8]          # confounding strength -> quasi bias
    out = {}
    for tau in taus:
        for conf in confs:
            re_rct, re_quasi = [], []
            for s in range(seeds):
                rng = np.random.default_rng(7919 * s + int(tau * 1000) + int(conf * 97))
                # A/B: randomized treatment, confounder independent of T -> unbiased
                Cr = rng.standard_normal(n_rct)
                Tr = rng.integers(0, 2, n_rct)
                Yr = tau * Tr + gamma * Cr + rng.normal(0, sigma, n_rct)
                est_rct = Yr[Tr == 1].mean() - Yr[Tr == 0].mean()
                # Quasi: P(treated) rises with the confounder (selection) -> naive diff biased
                Cq = rng.standard_normal(n_quasi)
                p = 1.0 / (1.0 + np.exp(-3.0 * conf * Cq))
                Tq = (rng.random(n_quasi) < p).astype(int)
                if Tq.sum() == 0 or Tq.sum() == n_quasi:
                    continue
                Yq = tau * Tq + gamma * Cq + rng.normal(0, sigma, n_quasi)
                est_quasi = Yq[Tq == 1].mean() - Yq[Tq == 0].mean()
                re_rct.append(est_rct - tau)
                re_quasi.append(est_quasi - tau)
            out[(tau, conf)] = (float(np.sqrt(np.mean(np.square(re_rct)))),
                                float(np.sqrt(np.mean(np.square(re_quasi)))))
    return out


if __name__ == "__main__":
    o = run()
    confs = [0.0, 0.2, 0.4, 0.6, 0.8]
    taus = [0.1, 0.5, 1.0, 2.0, 5.0]
    print("RMSE of the treatment-effect estimate.  A/B = randomized (n=100), Quasi = observational (n=2000, confounded).")
    print("\nDoes the A/B-vs-Quasi WINNER depend on the true effect size tau?  (rows = tau, cols = confounding)")
    print("tau \\ conf | " + " ".join(f"{c:>10.1f}" for c in confs))
    for tau in taus:
        cells = []
        for conf in confs:
            rr, rq = o[(tau, conf)]
            cells.append(("A/B " if rr < rq else "quasi") )
        print(f"{tau:>9} | " + " ".join(f"{c:>10}" for c in cells))
    print("\nRMSE values at tau=1.0 (to see the crossover in bias):")
    print("  conf  RMSE_A/B  RMSE_quasi  winner")
    for conf in confs:
        rr, rq = o[(1.0, conf)]
        print(f"  {conf:>4}  {rr:>8.3f}  {rq:>10.3f}  {'A/B' if rr<rq else 'quasi'}")
    # verify: winner pattern identical across all tau rows (=> tau-invariant)?
    pat = {}
    for tau in taus:
        pat[tau] = tuple('A' if o[(tau,c)][0] < o[(tau,c)][1] else 'q' for c in confs)
    invariant = len(set(pat.values())) == 1
    # and there IS a crossover in conf (not all same)?
    has_cross = len(set(pat[1.0])) > 1
    print(f"\nWinner pattern identical across ALL effect sizes tau? {invariant}  (pattern {pat[1.0]})")
    print(f"Crossover present along the BIAS/confounding axis? {has_cross}")
    print("VERDICT:", "SUPPORTED — the A/B-vs-quasi choice is set by bias, INVARIANT to effect size"
          if (invariant and has_cross) else "NOT supported")
