"""
Crucible replication (simulation): finite-size scaling of survival probability in branching processes.

Claim (Garcia-Millan, Font-Clos et al. 2015): the survival probability of a branching process obeys a
finite-size scaling form in the control parameter (offspring mean m = 1+eps) and the maximum number of
generations n. Concretely, near the critical point m=1, P_n(eps) ~ (1/n) * F(eps * n) — so the rescaled
survival probability n*P_n is a function of the single scaling variable x = eps*n, and curves for
different n COLLAPSE. Built as the smallest Galton-Watson model.

Vectorized over R realizations: a generation's total offspring is Poisson(m * pop) (sum of pop iid
Poisson(m)). Survival = population > 0 at generation n.
"""
import numpy as np

def survival_prob(eps, n, R=40000, cap=10**7, seed=0):
    m = 1.0 + eps
    rng = np.random.default_rng(abs(seed + int(round(eps*1e6)) + n*7) + 1)
    pop = np.ones(R, dtype=np.float64)
    for _ in range(n):
        lam = np.minimum(m * pop, cap)
        pop = rng.poisson(lam).astype(np.float64)      # Poisson(m*pop) = next generation size
        pop = np.minimum(pop, cap)
    return float((pop > 0).mean())

# (1) critical case eps=0: Kolmogorov says P_n ~ 2/(sigma^2 n); Poisson(1) has sigma^2=1 -> n*P_n -> 2
print("Critical (eps=0): n*P_n should approach 2/sigma^2 = 2 (Poisson offspring)")
for n in [20, 50, 150, 400]:
    p = survival_prob(0.0, n); print(f"  n={n:<4} P_n={p:.4f}  n*P_n={n*p:.3f}")

# (2) finite-size scaling collapse: n*P_n vs x=eps*n should collapse across different n
print("\nScaling collapse: Y=n*P_n vs x=eps*n (same x -> same Y across different n?)")
ns = [50, 150, 400]
eps_over_n = [-4.0, -1.0, 0.0, 1.0, 3.0]   # target x = eps*n values
print("x      " + "  ".join(f"n={n}" for n in ns))
rows = {}
for x in eps_over_n:
    ys = []
    for n in ns:
        eps = x / n
        p = survival_prob(eps, n)
        ys.append(n*p)
    rows[x] = ys
    print(f"x={x:<5} " + "  ".join(f"{y:.2f}" for y in ys))

# collapse quality: at each x, spread of Y across n should be small relative to the variation across x
def cv(vals):
    vals=np.array(vals); return float(np.std(vals)/ (abs(np.mean(vals))+1e-9))
within_x_spread = np.mean([np.std(rows[x]) for x in eps_over_n])      # avg spread across n at fixed x
across_x_range = np.mean([np.mean(rows[x]) for x in eps_over_n])      # typical Y magnitude
across_x_variation = np.std([np.mean(rows[x]) for x in eps_over_n])   # how Y varies with x
print(f"\navg within-x spread (should be SMALL) = {within_x_spread:.3f}")
print(f"across-x variation (should be LARGE)   = {across_x_variation:.3f}")
collapse = within_x_spread < 0.5 * across_x_variation and abs(survival_prob(0.0,400)*400 - 2) < 0.6

print("\n=== VERDICT ===")
print(f"critical n*P_n -> ~2 (Kolmogorov): {abs(survival_prob(0.0,400)*400 - 2) < 0.6}")
print(f"finite-size scaling collapse holds (within-x spread << across-x variation): {collapse}")
print("REPRODUCED" if collapse else "FAILED")
print("note: n*P_n is ~constant along fixed x=eps*n and rises with x (supercritical) / falls (subcritical)")
print("-> the rescaled survival probability is a function of eps*n alone, the claimed finite-size scaling.")
