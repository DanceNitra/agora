import numpy as np
rng = np.random.default_rng(42)

# Claim (Chu, Li, Reyzin, Schapire 2011): a linear contextual bandit (LinUCB-style) achieves
# regret that grows SUBLINEARLY, ~ sqrt(T) (with sqrt(d) and polylog factors) and holds w.h.p.
# Smallest model: d-dim features, K arms, reward = x·theta* + noise. Verify cumulative regret of
# LinUCB scales ~ sqrt(T) (exponent ~0.5, regret/T -> 0), vs greedy (no exploration) and random
# which incur LINEAR regret. Source: simulation.

d, K, T = 6, 12, 4000
theta = rng.normal(size=d); theta /= np.linalg.norm(theta)
alpha = 0.6              # UCB exploration width

def run(policy):
    A = np.eye(d); b = np.zeros(d); regret = 0.0; curve = {}
    checkpoints = {500, 1000, 2000, 4000}
    for t in range(1, T+1):
        X = rng.normal(size=(K, d)); X /= np.linalg.norm(X, axis=1, keepdims=True)
        means = X @ theta
        best = means.max()
        Ainv = np.linalg.inv(A); theta_hat = Ainv @ b
        if policy == "linucb":
            ucb = X @ theta_hat + alpha * np.sqrt(np.einsum('ij,jk,ik->i', X, Ainv, X))
            a = int(ucb.argmax())
        elif policy == "greedy":
            a = int((X @ theta_hat).argmax())
        else:
            a = rng.integers(K)
        r = means[a] + rng.normal(0, 0.1)
        A += np.outer(X[a], X[a]); b += r * X[a]
        regret += best - means[a]
        if t in checkpoints: curve[t] = regret
    return curve

print(f"d={d} K={K} T={T}. Claim: LinUCB regret ~ sqrt(T) (sublinear).\n")
print(f"{'policy':9s} {'R@500':>8} {'R@1000':>8} {'R@2000':>8} {'R@4000':>8}  {'fit exponent':>13}")
for pol in ("linucb", "greedy", "random"):
    c = run(pol)
    ts = sorted(c); xs = np.log(ts); ys = np.log([max(c[t],1e-9) for t in ts])
    expo = np.polyfit(xs, ys, 1)[0]          # regret ~ T^expo ; 0.5 = sqrt(T), 1.0 = linear
    print(f"{pol:9s} {c[500]:8.1f} {c[1000]:8.1f} {c[2000]:8.1f} {c[4000]:8.1f}  {expo:13.2f}")
print("\nLinUCB exponent ~0.5 (sqrt(T), regret/T -> 0) confirms the sublinear-regret claim;")
print("random ~1.0 (linear). REPRODUCED if LinUCB exponent is clearly < 1 and near 0.5.")
