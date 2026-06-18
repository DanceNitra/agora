"""
Physics vs Statistics — severe test (fddc77).

EX-ANTE claim (stated before simulating): a PURE statistical-inference problem — detecting a planted
signal in a noisy random matrix (the spiked Wigner / spiked-PCA model) — is not merely "analogous to"
a physics phase transition; it IS one, in the precise critical-phenomena sense:
  (1) a SHARP detectability threshold at signal-strength lambda_c = 1 (BBP transition), below which the
      top eigenvector carries ZERO information about the signal;
  (2) above it, the order parameter (overlap of the top eigenvector with the true signal) rises
      CONTINUOUSLY from zero with a definite CRITICAL EXPONENT beta = 1/2 (overlap ~ (lambda-1)^{1/2}).
This is a DIFFERENT universality class from the ones Agora already measured (mean-field percolation
beta=1; 2D percolation beta=5/36). If statistics borrows physics' critical machinery, beta must be a
clean 1/2 here — predicted with NO fitting.

Falsifier: no sharp threshold (overlap > 0 well below lambda=1), or a measured exponent that is not ~1/2.
"""
import numpy as np

def top_overlap(lmbda, N, rng):
    """Spiked Wigner: Y = (lambda/N) x x^T + W, x in {+-1}^N, W symmetric GOE with var 1/N.
    Return |<top eigvec, x/sqrt(N)>| (the order parameter)."""
    x = rng.choice([-1.0, 1.0], size=N)
    # symmetric noise, off-diag var 1/N
    G = rng.standard_normal((N, N)) / np.sqrt(N)
    W = (G + G.T) / np.sqrt(2.0)
    Y = (lmbda / N) * np.outer(x, x) + W
    w, V = np.linalg.eigh(Y)
    v_top = V[:, -1]                      # eigenvector of largest eigenvalue
    ov = abs(float(v_top @ (x / np.sqrt(N))))
    return ov, float(w[-1])

def measure(lmbda, N=1200, trials=6, seed=0):
    rng = np.random.default_rng(abs(hash((round(lmbda, 4), N, seed))) % (2**32))
    ovs = [top_overlap(lmbda, N, rng)[0] for _ in range(trials)]
    return float(np.mean(ovs)), float(np.std(ovs))

if __name__ == "__main__":
    N = 1200
    print(f"Spiked Wigner detection, N={N}, order parameter = |overlap(top eigvec, signal)|")
    print("EX-ANTE prediction: lambda_c = 1, overlap ~ (lambda-1)^{1/2}  (beta = 1/2)\n")

    # (1) sharp threshold: below 1 overlap ~ 0 (pure noise), above 1 it detaches
    grid = [0.6, 0.8, 0.95, 1.05, 1.2, 1.5, 2.0]
    meas = {}
    for L in grid:
        m, s = measure(L, N=N)
        meas[L] = m
        print(f"  lambda={L:<4}  overlap={m:.3f} +- {s:.3f}   theory(>1): sqrt(1-1/L^2)="
              f"{(np.sqrt(max(0,1-1/L**2))):.3f}")

    # Sharp threshold is an N->infinity statement; at finite N the transition is SMEARED over a
    # critical window (like ER percolation's N^-1/3 window). Demonstrate it via finite-size scaling:
    # a DEEP-subcritical point must collapse toward the random floor as N grows, while a
    # supercritical point stays put -> the boundary sharpens. Plus the supercritical branch must
    # match the closed-form BBP law sqrt(1-1/lambda^2).
    print("\n  finite-size scaling (sharp threshold = subcritical -> floor as N grows):")
    fss = {}
    for L in (0.85, 1.3):
        row = []
        for NN in (600, 1500, 3000):
            m, _ = measure(L, N=NN, trials=6)
            row.append((NN, m, 1/np.sqrt(NN)))
            print(f"    lambda={L}: N={NN:<5} overlap={m:.3f}  floor~{1/np.sqrt(NN):.3f}")
        fss[L] = row
    sub = fss[0.85]            # subcritical: overlap should fall toward floor as N grows
    sup = fss[1.3]             # supercritical: overlap should stay near sqrt(1-1/L^2)=0.66, N-stable
    sub_collapses = sub[-1][1] < sub[0][1] * 0.8           # shrinks with N
    sup_stable = abs(sup[-1][1] - np.sqrt(1 - 1/1.3**2)) < 0.06
    # supercritical branch matches the closed-form law across the grid
    branch_ok = all(abs(meas[L] - np.sqrt(1 - 1/L**2)) < 0.06 for L in (1.5, 2.0))
    sharp = sub_collapses and sup_stable and branch_ok
    print(f"\n  subcritical (0.85) collapses to floor with N : {sub_collapses}")
    print(f"  supercritical (1.3) N-stable at BBP value    : {sup_stable}")
    print(f"  supercritical branch matches sqrt(1-1/L^2)   : {branch_ok}")

    # (2) critical exponent near threshold: fit log(overlap) vs log(lambda-1)
    near = [1.04, 1.08, 1.15, 1.25, 1.4]
    xs, ys = [], []
    for L in near:
        m, _ = measure(L, N=2000, trials=8)   # bigger N near threshold for a clean exponent
        xs.append(np.log(L - 1.0)); ys.append(np.log(m))
    beta = float(np.polyfit(xs, ys, 1)[0])
    print(f"  near-threshold fit (lambda in {near}):  beta = {beta:.3f}   [predicted 1/2 = 0.5]")

    matches_half = abs(beta - 0.5) < 0.12
    print("\n=== VERDICT ===")
    print(f"sharp detectability threshold at lambda_c=1 : {sharp}")
    print(f"order-parameter exponent beta ~ 1/2          : {matches_half}  (measured {beta:.3f})")
    ok = sharp and matches_half
    if ok:
        print("\nPHYSICS == STATISTICS (severe test PASSED):")
        print("A pure inference problem is a genuine continuous phase transition: sharp threshold +")
        print(f"critical exponent beta~1/2 (BBP class). This is a THIRD distinct universality class")
        print("Agora has now measured (1, 5/36, 1/2) — statistics inherits physics' critical machinery,")
        print("not by analogy but identically. Predicted ex-ante, with no fitting of beta.")
    else:
        print("\nNOT confirmed as a critical-phenomena phase transition under this test.")
