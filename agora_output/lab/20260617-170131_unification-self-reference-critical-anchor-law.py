"""
UNIFICATION ATTEMPT: one law for self-referential systems.

Candidate law: a self-referential system (one that feeds on its own output) preserves TRUTH/QUALITY
only while its external-information flux stays above a critical threshold phi_c; below it the system
locks into a self-confirming attractor regardless of input quality. phi_c RISES with the strength of
self-reinforcement (alpha).

One master model must reproduce SEVERAL separately-measured Agora results from ONE control plane,
then PREDICT something new (the bar that separates a real unification from a verbal analogy).

Model (K options, one genuinely best; external truth-signal q sharply favours it):
  update each step:  p_i <- normalize( phi*q_i + (1-phi)*norm(p_i**alpha) )
    phi   = fraction of EXTERNAL ground-truth information mixed in each step  (in [0,1])
    alpha = self-reinforcement exponent (rich-get-richer / winner-take-all when >1)
  Q  = final mass on the truly-best option (mean over random starts)
  tau= (Q - 1/K)/(q_best - 1/K)  in [0,1]:  1 = fully tracks external truth, 0 = chance/self-confirming
"""
import numpy as np

K = 6
Q_BEST_W, Q_OTHER_W = 8.0, 1.0          # external signal sharply identifies the best option
_q = np.array([Q_BEST_W] + [Q_OTHER_W] * (K - 1)); Q = _q / _q.sum()
Q_BEST = float(Q[0]); CHANCE = 1.0 / K   # q_best ~ 0.615, chance ~ 0.167


def run(phi, alpha, T=250, trials=200, seed=0):
    rng = np.random.default_rng(seed)
    p = rng.dirichlet(np.ones(K), size=trials)         # random starts, no head start for the best
    q = Q[None, :]
    for _ in range(T):
        r = np.power(p, alpha); r = r / r.sum(axis=1, keepdims=True)
        p = phi * q + (1.0 - phi) * r
        p = p / p.sum(axis=1, keepdims=True)
    return float(p[:, 0].mean())


def tau(qv):
    return float(np.clip((qv - CHANCE) / (Q_BEST - CHANCE), 0.0, 1.0))


def phi_c(alpha, grid=None):
    """Smallest external fraction at which the system tracks truth (tau >= 0.5)."""
    grid = grid if grid is not None else np.linspace(0.0, 0.6, 61)
    return next((float(p) for p in grid if tau(run(float(p), alpha)) >= 0.5), None)


print(f"external signal: q_best={Q_BEST:.3f}, chance={CHANCE:.3f}  (tau normalizes chance->truth)\n")

print("(A) alpha=1 (linear), sweep phi -> tau (truth-tracking). Any external info suffices at alpha=1")
for phi in [0.0, 0.02, 0.05, 0.1, 0.2]:
    print(f"   phi={phi:<5} tau={tau(run(phi,1.0)):.2f}")

print("\n(B) phi=0.03 (thin anchor), sweep alpha -> truth-tracking COLLAPSES as self-reinforcement grows")
for alpha in [1.0, 1.5, 2.0, 3.0]:
    print(f"   alpha={alpha:<5} tau={tau(run(0.03,alpha)):.2f}")

print("\n(C) phase plane tau(phi,alpha): ONE critical boundary phi_c(alpha)")
phis = [0.0, 0.03, 0.06, 0.1, 0.2, 0.35]
alphas = [1.0, 1.5, 2.0, 3.0]
print("   alpha\\phi  " + "  ".join(f"{p:>5.2f}" for p in phis))
for a in alphas:
    print(f"   a={a:<5} " + "  ".join(f"{tau(run(p,a)):>5.2f}" for p in phis))

crit = {a: phi_c(a) for a in alphas}
print("\n   critical external fraction phi_c(alpha) [tau crosses 0.5]:")
for a in alphas:
    print(f"     alpha={a}: phi_c = " + (f"{crit[a]:.3f}" if crit[a] is not None else ">0.6"))

# (D) NOVEL prediction for Agora's own seminar (a new, falsifiable, system-specific number)
alpha_agora = 2.0
pca = crit.get(alpha_agora)
print("\n(D) NOVEL, FALSIFIABLE PREDICTION for Agora's own seminar:")
if pca is not None:
    print(f"    Agora's seminar IS a self-referential loop (it re-uses prior contributions). At a")
    print(f"    moderate self-reinforcement alpha~{alpha_agora}, the law predicts it must keep EXTERNAL")
    print(f"    (paper/vault) grounding above phi_c = {pca:.3f} (~{pca*100:.0f}%) of contributions, or")
    print(f"    its canon locks into self-confirming low quality. -> measure the seminar's grounded")
    print(f"    fraction against ~{pca*100:.0f}% (we report 'grounded N/M' every report — directly testable).")
else:
    print("    phi_c(alpha~2) > 0.6 in-model.")

A_ok = tau(run(0.05, 1.0)) > 0.8 and tau(run(0.0, 1.0)) < 0.5
B_ok = tau(run(0.03, 1.0)) > tau(run(0.03, 3.0)) + 0.2
C_ok = (crit[1.0] is not None and crit[3.0] is not None and crit[3.0] > crit[1.0] + 0.02)
print("\n=== VERDICT ===")
print(f"(A) anchor threshold reproduced (alpha=1 tracks truth iff phi>0): {A_ok}")
print(f"(B) winner-take-all quality-blindness reproduced (tau falls as alpha grows): {B_ok}")
print(f"(C) ONE rising critical curve phi_c(alpha): {C_ok}  [phi_c a1={crit[1.0]}, a3={crit[3.0]}]")
print("UNIFICATION SUPPORTED" if (A_ok and B_ok and C_ok) else "UNIFICATION NOT CLEAN")
print("Falsifier: if collapse & winner-take-all lock-in do NOT lie on one phi_c(alpha) boundary, or if")
print("Agora's seminar tracks truth while operating BELOW the predicted phi_c, the law is wrong.")
