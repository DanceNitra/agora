"""
Severe test of two ideas the second-brain briefing generated from the owner's own notes:

IDEA 1 — "Cue-Validity Determines the Custodian": there is a crossover v* in environment signal
quality below which a humble CROWD (variance-reducing ensemble) beats a confident EXPERT
(full-commitment model), and above which the expert wins. Falsifier: NO crossover (one always wins).

IDEA 2 — "A Crowd Is System 2 Implemented Socially / only INDEPENDENCE is load-bearing": averaging
N estimates kills RANDOM error (~1/sqrt(N)) but NOT a shared bias; with correlated errors the gain
floors. Falsifier: error keeps shrinking ~1/sqrt(N) even with a shared anchor.

Mechanism is plain bias-variance + correlated-error algebra (well understood); the contribution is
the MEASURED crossover and floor that ground the framing. Nothing is hand-set to force the result.
"""
import numpy as np

# ---------- IDEA 1: cue-validity crossover ----------
def crossover(d=12, k=4, M=25, n_train=40, n_test=400, n_seeds=60):
    vs = [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]
    out = {}
    for v in vs:
        e_exp, e_crowd = [], []
        for s in range(n_seeds):
            rng = np.random.default_rng(10_000*s + int(v*1000))
            beta = rng.standard_normal(d)
            def gen(n):
                X = rng.standard_normal((n, d))
                signal = X @ beta
                # noise set so R^2 == v:  var(noise) = var(signal)*(1-v)/v
                nstd = np.sqrt(np.var(signal) * (1-v)/v)
                y = signal + rng.normal(0, nstd, size=n)
                return X, y
            Xtr, ytr = gen(n_train); Xte, yte = gen(n_test)
            # EXPERT: full OLS on all d features (low bias, high variance under noise)
            w = np.linalg.lstsq(Xtr, ytr, rcond=None)[0]
            pred_exp = Xte @ w
            # CROWD: M agents, each OLS on a bootstrap sample using a random k-feature subspace; average
            preds = np.zeros(n_test)
            for _ in range(M):
                cols = rng.choice(d, size=k, replace=False)
                rows = rng.integers(0, n_train, size=n_train)
                wm = np.linalg.lstsq(Xtr[np.ix_(rows, cols)], ytr[rows], rcond=None)[0]
                preds += Xte[:, cols] @ wm
            pred_crowd = preds / M
            e_exp.append(np.sqrt(np.mean((pred_exp - yte)**2)))
            e_crowd.append(np.sqrt(np.mean((pred_crowd - yte)**2)))
        out[v] = (float(np.mean(e_exp)), float(np.mean(e_crowd)))
    return out

# ---------- IDEA 2: independence is load-bearing ----------
def corr_floor(sigma=1.0, n_seeds=4000):
    Ns = [1,2,5,10,25,50,100,200]
    out = {}
    for rho in [0.0, 0.3]:
        for N in Ns:
            rng = np.random.default_rng(777 + N + int(rho*1000))
            sq = []
            for _ in range(n_seeds):
                shared = rng.normal(0, sigma)
                errs = np.sqrt(rho)*shared + np.sqrt(1-rho)*rng.normal(0, sigma, size=N)
                sq.append((errs.mean())**2)
            out[(rho, N)] = float(np.sqrt(np.mean(sq)))
    return out

if __name__ == "__main__":
    print("=== IDEA 1: cue-validity crossover (expert OLS vs crowd ensemble) ===")
    co = crossover()
    print(f"{'v':>5} {'expert_RMSE':>12} {'crowd_RMSE':>12}  winner")
    winners = []
    for v,(ee,ce) in co.items():
        w = 'EXPERT' if ee < ce else 'crowd'
        winners.append(w)
        print(f"{v:>5} {ee:>12.3f} {ce:>12.3f}  {w}")
    # crossover exists iff both winners appear and it flips exactly as v rises
    flips = sum(1 for a,b in zip(winners, winners[1:]) if a!=b)
    has_cross = ('crowd' in winners) and ('EXPERT' in winners)
    monotone = (winners[0]=='crowd' and winners[-1]=='EXPERT' and flips==1)
    print(f"\nCROSSOVER PRESENT: {has_cross} | single clean flip crowd->EXPERT as v rises: {monotone} (flips={flips})")
    print("VERDICT idea1:", "SUPPORTED (crossover at low->high cue validity)" if monotone else
          ("PARTIAL (crossover present but not a single clean flip)" if has_cross else "FAILED (no crossover)"))

    print("\n=== IDEA 2: independence load-bearing (RMSE of the averaged estimate) ===")
    cf = corr_floor()
    print(f"{'N':>5} {'rho=0 (indep)':>15} {'rho=0.3 (shared)':>18}")
    for N in [1,2,5,10,25,50,100,200]:
        print(f"{N:>5} {cf[(0.0,N)]:>15.4f} {cf[(0.3,N)]:>18.4f}")
    indep_shrinks = cf[(0.0,200)] < 0.15            # ~1/sqrt(200)=0.071
    shared_floors = cf[(0.3,200)] > 0.45            # floor ~ sqrt(0.3)=0.548
    print(f"\nindep keeps shrinking ~1/sqrt(N): {indep_shrinks} (RMSE@200={cf[(0.0,200)]:.3f})")
    print(f"shared-anchor RMSE FLOORS (stops shrinking): {shared_floors} (RMSE@200={cf[(0.3,200)]:.3f}, theory floor sqrt(0.3)={np.sqrt(0.3):.3f})")
    print("VERDICT idea2:", "SUPPORTED (only independence buys the 1/sqrt(N); shared bias floors it)"
          if (indep_shrinks and shared_floors) else "FAILED")
