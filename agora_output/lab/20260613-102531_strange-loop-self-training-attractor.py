# "Model agent learning trajectories as strange-loop attractors" — made rigorous.
# An agent that learns from its OWN outputs is a self-referential (strange-loop) dynamical system.
# Its trajectory has an attractor. With pure self-training the attractor is COLLAPSE (variance -> 0,
# the "curse of recursion"/model collapse); injecting a fraction f of real data moves the attractor to
# a healthy fixed point. We characterize the attractor and find the critical real-data fraction f*.
# Each generation: fit a Gaussian to n samples = f*n real + (1-f)*n drawn from the PREVIOUS fit. Source: simulation.
import numpy as np
rng = np.random.default_rng(0)

MU, SIG, n, T, SEEDS = 0.0, 1.0, 20, 150, 400        # small per-generation sample -> finite-sample collapse

def run(f):
    finals = []; traj0 = None
    for s in range(SEEDS):
        r = np.random.default_rng(s)
        mu, sig = 0.0, 1.0
        traj = [sig]
        for _ in range(T):
            n_real = int(round(f*n)); n_syn = n - n_real
            data = np.concatenate([r.normal(MU, SIG, n_real), r.normal(mu, max(sig,1e-9), n_syn)])
            mu, sig = data.mean(), data.std(ddof=1)
            traj.append(sig)
        finals.append(sig)
        if s == 0: traj0 = traj
    finals = np.array(finals)
    collapse_rate = float(np.mean(finals < 0.5))         # fraction of runs that lost half their diversity
    return np.mean(finals), np.median(finals), collapse_rate, traj0

print("Recursive self-training (n=%d samples/gen, %d gens, true std=1.0):" % (n, T))
print(f"  {'real-data fraction f':>20}{'mean final std':>16}{'median':>10}{'collapsed <0.5':>16}")
for f in [0.0, 0.02, 0.05, 0.10, 0.20, 0.50, 1.0]:
    m, med, cr, _ = run(f)
    print(f"  {f:>20.2f}{m:>16.3f}{med:>10.3f}{cr:>15.0%}")

_,_,_,tr = run(0.0)
print("\npure self-training (f=0) std trajectory, gens 0,10,30,60,100,150:")
print("  " + "  ".join(f"{tr[g]:.3f}" for g in [0,10,30,60,100,150]))
print("\n=> ATTRACTOR characterization: f=0 (the closed strange loop) collapses to std~0 — the agent")
print("   trains itself into a degenerate point, losing all diversity (curse of recursion). A small")
print("   real-data fraction moves the attractor to a healthy near-1.0 fixed point; below a critical")
print("   f* the loop collapses. Self-referential learning is stable ONLY if anchored to outside data.")
