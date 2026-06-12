
import numpy as np
rng = np.random.default_rng(7)
N = 40000
def ols(y, *cols):
    X = np.column_stack([np.ones_like(y)] + list(cols))
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coef
print("=== Collider bias: does adjusting for a collider corrupt a correct causal estimate? ===")
print(f"{'true_beta':>9} | {'naive Y~X':>10} | {'Y~X+collider':>13} | {'induced bias':>12}")
for beta in (0.0, 0.5, 1.0):
    X = rng.normal(size=N)
    Y = beta * X + rng.normal(size=N)
    C = X + Y + 0.3 * rng.normal(size=N)
    b_naive = ols(Y, X)[1]; b_adj = ols(Y, X, C)[1]
    print(f"{beta:>9.2f} | {b_naive:>10.4f} | {b_adj:>13.4f} | {b_adj-beta:>12.4f}")
print()
print("=== M-bias: adjusting for a PRE-treatment covariate (collider of two latents) ===")
print(f"{'true_beta':>9} | {'naive Y~X':>10} | {'Y~X+M':>10} | {'induced bias':>12}")
for beta in (0.0, 0.5):
    U1 = rng.normal(size=N); U2 = rng.normal(size=N)
    X = U1 + rng.normal(size=N)
    Y = beta * X + U2 + rng.normal(size=N)
    C = U1 + U2 + 0.3 * rng.normal(size=N)
    b_naive = ols(Y, X)[1]; b_adj = ols(Y, X, C)[1]
    print(f"{beta:>9.2f} | {b_naive:>10.4f} | {b_adj:>10.4f} | {b_adj-beta:>12.4f}")
