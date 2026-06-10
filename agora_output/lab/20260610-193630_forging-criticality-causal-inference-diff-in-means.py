import numpy as np

rng = np.random.default_rng(7)

# FORGING: Criticality -> causal inference.
# Units on a 2D lattice influence neighbors (linear-in-means: y = tau*D + rho*W*y + e).
# As rho -> rho_crit = 1/lambda_max(W), correlation length diverges - treatment leaks
# into "controls" system-wide, violating SUTVA. Measure naive diff-in-means bias vs
# distance to criticality.
L = 20                          # 20x20 lattice, N=400
N = L * L
TAU = 2.0
N_SIM = 60

# row-normalized adjacency (von Neumann neighbors, torus)
idx = lambda r, c: (r % L) * L + (c % L)
W = np.zeros((N, N))
for r in range(L):
    for c in range(L):
        i = idx(r, c)
        for dr, dc in ((1,0), (-1,0), (0,1), (0,-1)):
            W[i, idx(r+dr, c+dc)] = 0.25
lam_max = np.max(np.abs(np.linalg.eigvals(W)).real)   # = 1 for row-normalized
rho_crit = 1.0 / lam_max

print("Criticality -> causal inference: diff-in-means bias vs distance to critical coupling")
print(f"(lattice {L}x{L}, true effect tau={TAU}, rho_crit={rho_crit:.3f}, {N_SIM} sims/point)\n")
print(f"{'rho/rho_c':>9} {'corr_len_proxy':>14} {'est_effect':>11} {'bias':>8} {'bias%':>7}")

I = np.eye(N)
for frac in (0.0, 0.5, 0.8, 0.9, 0.95, 0.98, 0.99):
    rho = frac * rho_crit
    M = np.linalg.inv(I - rho * W)          # equilibrium propagator
    # correlation-length proxy: average total indirect influence per unit
    corr_proxy = (M.sum() / N) - 1.0
    biases = []
    for _ in range(N_SIM):
        D = (rng.random(N) < 0.5).astype(float)   # randomized treatment, half the lattice
        e = rng.normal(0, 1, N)
        y = M @ (TAU * D + e)
        est = y[D == 1].mean() - y[D == 0].mean()
        biases.append(est - TAU)
    b = float(np.mean(biases))
    print(f"{frac:9.2f} {corr_proxy:14.2f} {TAU + b:11.3f} {b:8.3f} {100*abs(b)/TAU:6.1f}%")

print("\nReading: even with RANDOMIZED treatment, interference (rho>0) contaminates controls;")
print("bias should grow non-linearly as rho -> rho_crit (diverging correlation length = global")
print("SUTVA violation). If bias stays flat near criticality, the forged hypothesis is dead.")
